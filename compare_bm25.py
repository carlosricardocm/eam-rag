"""Experimento: la EAM (o el coseno) elige las K obras y BM25 elige, dentro de
ellas, los C fragmentos que se pasan al LLM (arquitectura híbrida).

Configuraciones: recuperador de obras {EAM m=16, coseno} x K {1, 3} x C {8, 16}.
Mismas 89 preguntas, modelo, juez y caché que compare_retrievers.py y
compare_whole_works.py; las obras repetidas (texto contenido en otra) se saltan.

Uso:
  python compare_bm25.py [--no-llm]
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from compare_llm import Cache, cached_chat, judge
from compare_retrievers import gold_chunks, summarize
from config import OPENAI_MODEL, require_openai_key
from eam_store import EAMStore
from generator import SYSTEM as RAG_SYSTEM
from generator import build_prompt

HERE = os.path.dirname(os.path.abspath(__file__))
KS = [1, 3]
CS = [8, 16]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--store', default=os.path.join(HERE, 'store'))
    ap.add_argument('--data', default=os.path.join(HERE, '..', 'datasets_csv'))
    ap.add_argument('--questions', default=os.path.join(HERE, 'questions.json'))
    ap.add_argument('--out', default=os.path.join(HERE, 'results'))
    ap.add_argument('--model', default=OPENAI_MODEL)
    ap.add_argument('--judge-model', default=OPENAI_MODEL)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--no-llm', action='store_true')
    args = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    questions = [q for q in json.load(open(args.questions, encoding='utf-8')) if q.get('title')]
    store = EAMStore.load(args.store)
    store.load_texts(args.data)             # marca obras repetidas
    emb = np.load(os.path.join(args.store, 'embeddings.npy'))
    emb_norm = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    work_of = np.array([c.work_id for c in store.chunks])
    key = {(w.title.lower(), w.author.lower()): w.work_id for w in store.works}
    targets = [key[(q['title'].lower(), q['author'].lower())] for q in questions]
    gold = [gold_chunks(store, w, q['evidence']) for w, q in zip(targets, questions)]

    from sonar_encoder import SonarEncoder
    qemb = SonarEncoder().encode([q['q'] for q in questions])
    cos_rank = []
    for e in qemb:
        sims = emb_norm @ (e / np.linalg.norm(e))
        cos_rank.append(list(dict.fromkeys(int(w) for w in work_of[np.argsort(-sims)[:2000]])))

    configs = []
    for name in ('EAM m=16', 'Coseno'):
        for K in KS:
            for C in CS:
                c = dict(name=name, top_works=K, top_chunks=C, rows=[])
                for i, (q, e) in enumerate(zip(questions, qemb)):
                    ranked = None if name.startswith('EAM') else cos_rank[i]
                    hits = store.retrieve_bm25(e[None, :], q['q'], K, C, ranked_works=ranked)
                    prompt = build_prompt(q['q'], hits)
                    c['rows'].append(dict(q=q['q'], fame=q.get('fame', 'conocida'),
                                          work_hit=targets[i] in {h.work_id for h in hits} or
                                          targets[i] in store.distinct_works(
                                              store.rank_works(e[None, :])[1] if ranked is None else ranked, K),
                                          evid_hit=bool({h.chunk_id for h in hits} & gold[i]),
                                          prompt_words=sum(len(h.text.split()) for h in hits), prompt=prompt))
                c['obra'] = float(np.mean([r['work_hit'] for r in c['rows']]))
                c['evid'] = float(np.mean([r['evid_hit'] for r in c['rows']]))
                c['palabras_mediana'] = float(np.median([r['prompt_words'] for r in c['rows']]))
                configs.append(c)
                print(f"{name:9} K={K} C={C:2}: obra@{K} {c['obra']:.2f}  evid {c['evid']:.2f}  "
                      f"palabras {c['palabras_mediana']:.0f}")

    if not args.no_llm:
        from openai import OpenAI
        client = OpenAI(api_key=require_openai_key())
        cache = Cache(os.path.join(args.out, 'compare_cache.jsonl'))
        before = len(cache.data)
        prompts = sorted({r['prompt'] for c in configs for r in c['rows']})
        print(f'Generación: {sum(len(c["rows"]) for c in configs)} respuestas, {len(prompts)} prompts distintos')
        with ThreadPoolExecutor(args.workers) as ex:
            answers = dict(zip(prompts, ex.map(
                lambda p: cached_chat(cache, client, args.model, RAG_SYSTEM, p)['text'], prompts)))
        pairs = sorted({(i, answers[r['prompt']]) for c in configs for i, r in enumerate(c['rows'])})
        with ThreadPoolExecutor(args.workers) as ex:
            verdicts = dict(zip(pairs, ex.map(
                lambda p: judge(cache, client, args.judge_model, questions[p[0]], p[1])[0], pairs)))
        print(f'Llamadas nuevas a la API: {len(cache.data) - before}')
        for c in configs:
            for i, r in enumerate(c['rows']):
                r['answer'] = answers[r['prompt']]
                r['verdict'] = verdicts[(i, r['answer'])]
            c.update(summarize(c['rows'], 'verdict'))
            for fame in ('conocida', 'poco_conocida'):
                c[f'exactitud_{fame}'] = summarize([r for r in c['rows'] if r['fame'] == fame], 'verdict')['exactitud']

    for c in configs:
        for r in c['rows']:
            del r['prompt']
    out = dict(model=args.model, judge_model=args.judge_model, n=len(questions), configs=configs)
    with open(os.path.join(args.out, 'bm25.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = report(out)
    with open(os.path.join(args.out, 'bm25.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print('\n' + md)


def report(out):
    md = ['# Obras por EAM o coseno + fragmentos por BM25\n',
          f"{out['n']} preguntas sobre el corpus; `{out['model']}` como generador y juez. evid = el fragmento con "
          'la cita de referencia está en el prompt. Exactitud = correcto + 0.5·parcial.\n',
          '| Obras | K | Fragmentos (BM25) | obra@K | evid | Palabras | Exactitud | Correcto | Incorrecto | '
          'No lo sé | Conocidas | Poco conocidas |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    llm = 'exactitud' in out['configs'][0]
    for c in out['configs']:
        s = (f"| {c['name']} | {c['top_works']} | {c['top_chunks']} | {c['obra']:.2f} | {c['evid']:.2f} | "
             f"{c['palabras_mediana']:.0f} |")
        if llm:
            s += (f" **{c['exactitud']:.2f}** | {c['correcto']:.0%} | {c['incorrecto']:.0%} | {c['no_sabe']:.0%} | "
                  f"{c['exactitud_conocida']:.2f} | {c['exactitud_poco_conocida']:.2f} |")
        md.append(s)
    return '\n'.join(md) + '\n'


if __name__ == '__main__':
    main()
