"""Experimento: pasar al LLM la obra completa en lugar de fragmentos.

La obra se elige como siempre (EAM: rank_works; coseno: la obra de los
fragmentos más similares) y se toma la mejor (K = 1 por defecto) con su texto
íntegro. Así la evidencia llega al prompt siempre que se acierte la obra.

Se compara EAM (m = 16) y coseno con obra completa, y como referencia se leen
de results/retrievers.json los resultados con 8 fragmentos y del LLM sin
recuperación (python compare_retrievers.py). Mismo modelo, juez y caché.

Uso:
  python compare_whole_works.py [--obras 1] [--no-llm]
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from compare_llm import Cache, cached_chat, judge, norm
from compare_retrievers import summarize
from config import OPENAI_MODEL, require_openai_key
from eam_store import EAMStore, Hit
from generator import SYSTEM as RAG_SYSTEM
from generator import build_prompt

HERE = os.path.dirname(os.path.abspath(__file__))


def cosine_works(store, emb_norm, work_of, q, k, texts):
    sims = emb_norm @ (q / np.linalg.norm(q))
    ranked = list(dict.fromkeys(int(w) for w in work_of[np.argsort(-sims)[:2000]]))
    works = store.distinct_works(ranked, k)   # sin textos repetidos, igual que la EAM
    return [Hit(-1, w, store.works[w].author, store.works[w].title, texts[w], 0.0, 0.0, 0) for w in works]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--store', default=os.path.join(HERE, 'store'))
    ap.add_argument('--data', default=os.path.join(HERE, '..', 'datasets_csv'))
    ap.add_argument('--questions', default=os.path.join(HERE, 'questions.json'))
    ap.add_argument('--out', default=os.path.join(HERE, 'results'))
    ap.add_argument('--obras', type=int, default=1, help='obras completas por pregunta (K)')
    ap.add_argument('--model', default=OPENAI_MODEL)
    ap.add_argument('--judge-model', default=OPENAI_MODEL)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--no-llm', action='store_true')
    args = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    questions = [q for q in json.load(open(args.questions, encoding='utf-8')) if q.get('title')]
    store = EAMStore.load(args.store)
    texts = store.load_texts(args.data)
    emb = np.load(os.path.join(args.store, 'embeddings.npy'))
    emb_norm = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    work_of = np.array([c.work_id for c in store.chunks])
    key = {(w.title.lower(), w.author.lower()): w.work_id for w in store.works}
    targets = [key[(q['title'].lower(), q['author'].lower())] for q in questions]

    from sonar_encoder import SonarEncoder
    qemb = SonarEncoder().encode([q['q'] for q in questions])

    K = args.obras
    configs = [dict(name='EAM m=16', retriever='eam'), dict(name='Coseno', retriever='cos')]
    for c in configs:
        c.update(top_works=K, mode='obra completa', rows=[])
        for q, e, t in zip(questions, qemb, targets):
            hits = (store.retrieve_works(e[None, :], K, texts) if c['retriever'] == 'eam'
                    else cosine_works(store, emb_norm, work_of, e, K, texts))
            prompt = build_prompt(q['q'], hits)
            c['rows'].append(dict(q=q['q'], fame=q.get('fame', 'conocida'),
                                  work_hit=t in [h.work_id for h in hits],
                                  evid_hit=norm(q['evidence'])[:60] in norm(prompt),
                                  prompt_words=len(prompt.split()), prompt=prompt))
        c['obra'] = float(np.mean([r['work_hit'] for r in c['rows']]))
        c['evid'] = float(np.mean([r['evid_hit'] for r in c['rows']]))
        c['palabras_mediana'] = float(np.median([r['prompt_words'] for r in c['rows']]))
        print(f"{c['name']:9} obra completa K={K}: obra@{K} {c['obra']:.2f}  evid {c['evid']:.2f}  "
              f"prompt mediano {c['palabras_mediana']:.0f} palabras")

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
    ref = json.load(open(os.path.join(args.out, 'retrievers.json'), encoding='utf-8'))
    out = dict(model=args.model, judge_model=args.judge_model, n=len(questions), obras=K, configs=configs,
               fragmentos=[{k: v for k, v in c.items() if k != 'rows'} for c in ref['configs']
                           if c['top_works'] == 5 and c['name'] in ('EAM m=16', 'Coseno')],
               direct=ref['direct'])
    name = f'whole_works_k{K}'
    with open(os.path.join(args.out, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = report(out)
    with open(os.path.join(args.out, name + '.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print('\n' + md)


def report(out):
    K = out['obras']
    md = [f'# Obra completa (K = {K}) frente a 8 fragmentos\n',
          f"{out['n']} preguntas sobre el corpus; `{out['model']}` como generador y juez. evid = la cita de "
          'referencia está en el prompt. Exactitud = correcto + 0.5·parcial.\n',
          '| Qué recibe el LLM | Recuperador | obra@K | evid | Exactitud | Correcto | Incorrecto | No lo sé | '
          'Conocidas | Poco conocidas |', '|---|---|---|---|---|---|---|---|---|---|']
    llm = 'exactitud' in out['configs'][0]

    def line(what, c, k):
        s = f"| {what} | {c['name']} | {c['obra']:.2f} (K={k}) | {c['evid']:.2f} |"
        if llm:
            s += (f" **{c['exactitud']:.2f}** | {c['correcto']:.0%} | {c['incorrecto']:.0%} | {c['no_sabe']:.0%} | "
                  f"{c['exactitud_conocida']:.2f} | {c['exactitud_poco_conocida']:.2f} |")
        return s
    for c in out['fragmentos']:
        md.append(line('8 fragmentos (de 5 obras)', c, 5))
    for c in out['configs']:
        md.append(line(f'{K} obra(s) completa(s)', c, K))
    d = out['direct']
    md.append(f"| Nada (LLM directo) | — | — | — | **{d['exactitud']:.2f}** | {d['correcto']:.0%} | "
              f"{d['incorrecto']:.0%} | {d['no_sabe']:.0%} | {d['exactitud_conocida']:.2f} | "
              f"{d['exactitud_poco_conocida']:.2f} |")
    return '\n'.join(md) + '\n'


if __name__ == '__main__':
    main()
