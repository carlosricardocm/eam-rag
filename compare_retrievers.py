"""Experimento: recuperación con EAM (m = 16, 8, 4) frente a similitud coseno,
con las preguntas de questions.json y dos tamaños de recuperación
(5 obras / 8 fragmentos y 3 obras / 8 fragmentos).

Dos niveles de evaluación:
  1. Recuperación (sin LLM, sin costo): obra@K (la obra correcta está entre
     las K recuperadas) y evid@C (el fragmento con la evidencia literal llega
     al prompt).
  2. Respuesta (con LLM): cada configuración genera su respuesta RAG y un juez
     la compara con la de referencia, igual que compare_llm.py.

Para ahorrar llamadas a la API:
  - los prompts idénticos entre configuraciones se generan una sola vez
    (coseno no depende de m ni del número de obras; la EAM con 3 y 5 obras
    suele recuperar los mismos 8 fragmentos);
  - una respuesta "No lo sé." no pasa por el juez;
  - todo se guarda en results/compare_cache.jsonl (compartido con
    compare_llm.py), así que lo ya calculado no se repite.
  La generación sólo usa las preguntas sobre el corpus: sin umbral, ningún
  recuperador rechaza las preguntas ajenas, así que no distinguen configuraciones.

Uso:
  python compare_retrievers.py             # recuperación + LLM
  python compare_retrievers.py --no-llm    # sólo recuperación (sin costo)
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from compare_llm import (DIRECT_SYSTEM, SCORE, VERDICTS, Cache, cached_chat, judge, norm)
from config import OPENAI_MODEL, require_openai_key
from eam_store import EAMStore, Hit
from generator import SYSTEM as RAG_SYSTEM
from generator import build_prompt

HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = [(5, 8), (3, 8)]          # (top_works, top_chunks)
MS = [16, 8, 4]


def gold_chunks(store, wid, evidence):
    """Fragmentos de la obra que contienen el inicio o el final de la evidencia."""
    ev = norm(evidence)
    return {c for c in store.chunks_of[wid]
            if ev[:60] in norm(store.chunks[c].text) or ev[-60:] in norm(store.chunks[c].text)}


def cosine_retrieve(store, emb_norm, work_of, q, top_works, top_chunks):
    """Vector DB: los top_chunks fragmentos más similares de todo el corpus.
    Las obras (para obra@K) se ordenan por su fragmento más similar."""
    sims = emb_norm @ (q / np.linalg.norm(q))
    top = np.argsort(-sims)
    works = list(dict.fromkeys(int(w) for w in work_of[top[:500]]))[:top_works]
    hits = []
    for c in top[:top_chunks]:
        ch = store.chunks[c]
        w = store.works[ch.work_id]
        hits.append(Hit(int(c), w.work_id, w.author, w.title, ch.text, float(sims[c]), 0.0, 0))
    return works, hits


def summarize(rows, key):
    n = len(rows)
    d = {v: sum(r[key] == v for r in rows) / n for v in VERDICTS}
    d['exactitud'] = float(np.mean([SCORE[r[key]] for r in rows]))
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--store', default=os.path.join(HERE, 'store'))
    ap.add_argument('--questions', default=os.path.join(HERE, 'questions.json'))
    ap.add_argument('--out', default=os.path.join(HERE, 'results'))
    ap.add_argument('--model', default=OPENAI_MODEL)
    ap.add_argument('--judge-model', default=OPENAI_MODEL)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--no-llm', action='store_true', help='sólo métricas de recuperación (sin API)')
    args = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(args.out, exist_ok=True)

    questions = [q for q in json.load(open(args.questions, encoding='utf-8')) if q.get('title')]
    store16 = EAMStore.load(args.store)
    emb = np.load(os.path.join(args.store, 'embeddings.npy'))
    emb_norm = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    work_of = np.array([c.work_id for c in store16.chunks])
    key = {(w.title.lower(), w.author.lower()): w.work_id for w in store16.works}
    targets = [key[(q['title'].lower(), q['author'].lower())] for q in questions]
    gold = [gold_chunks(store16, w, q['evidence']) for w, q in zip(targets, questions)]

    from sonar_encoder import SonarEncoder
    qemb = SonarEncoder().encode([q['q'] for q in questions])

    # Mismos embeddings y fragmentos; con otro m sólo cambian cuantización y memorias.
    cfg = {k: store16.config[k] for k in ('quant', 'criterion', 'sigma', 'eps', 'min_z', 'tolerance',
                                          'iota', 'kappa', 'soft', 'chunk_sigma')}
    stores = {16: store16}
    for m in MS:
        if m not in stores:
            stores[m] = EAMStore.build(store16.works, store16.chunks, emb, m=m, **cfg)

    # ---------------------------------------------------------- recuperación
    configs = []
    for W, C in SIZES:
        for m in MS:
            configs.append(dict(name=f'EAM m={m}', retriever='eam', m=m, top_works=W, top_chunks=C))
        configs.append(dict(name='Coseno', retriever='cos', m=None, top_works=W, top_chunks=C))
    for c in configs:
        c['rows'] = []
        for i, (q, e) in enumerate(zip(questions, qemb)):
            if c['retriever'] == 'eam':
                st = stores[c['m']]
                _, order, _, _ = st.rank_works(e[None, :])
                works = [int(w) for w in order[:c['top_works']]]
                hits = st.retrieve(e[None, :], c['top_works'], c['top_chunks'])
            else:
                works, hits = cosine_retrieve(store16, emb_norm, work_of, e, c['top_works'], c['top_chunks'])
            c['rows'].append(dict(q=q['q'], fame=q.get('fame', 'conocida'), work_hit=targets[i] in works,
                                  evid_hit=bool({h.chunk_id for h in hits} & gold[i]),
                                  prompt=build_prompt(q['q'], hits)))
        c['obra'] = float(np.mean([r['work_hit'] for r in c['rows']]))
        c['evid'] = float(np.mean([r['evid_hit'] for r in c['rows']]))
        print(f"{c['name']:10} W={c['top_works']} C={c['top_chunks']}  obra@{c['top_works']} {c['obra']:.2f}  "
              f"evid@{c['top_chunks']} {c['evid']:.2f}")

    direct = None
    if not args.no_llm:
        from openai import OpenAI
        client = OpenAI(api_key=require_openai_key())
        cache = Cache(os.path.join(args.out, 'compare_cache.jsonl'))
        before = len(cache.data)

        # Generación: un solo llamado por prompt distinto.
        prompts = sorted({r['prompt'] for c in configs for r in c['rows']})
        total = sum(len(c['rows']) for c in configs)
        print(f'\nGeneración: {total} respuestas RAG, {len(prompts)} prompts distintos '
              f'(+{len(questions)} respuestas directas)')
        with ThreadPoolExecutor(args.workers) as ex:
            answers = dict(zip(prompts, ex.map(
                lambda p: cached_chat(cache, client, args.model, RAG_SYSTEM, p)['text'], prompts)))
            direct_ans = list(ex.map(
                lambda q: cached_chat(cache, client, args.model, DIRECT_SYSTEM, q['q'])['text'], questions))

        # Juez: un solo llamado por (pregunta, respuesta) distinta; "No lo sé." no se juzga.
        pairs = sorted({(i, answers[r['prompt']]) for c in configs for i, r in enumerate(c['rows'])}
                       | set(enumerate(direct_ans)))
        print(f'Juez: {len(pairs)} pares (pregunta, respuesta) distintos')
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
                sub = [r for r in c['rows'] if r['fame'] == fame]
                c[f'exactitud_{fame}'] = summarize(sub, 'verdict')['exactitud']
        drows = [dict(fame=q.get('fame', 'conocida'), verdict=verdicts[(i, a)])
                 for i, (q, a) in enumerate(zip(questions, direct_ans))]
        direct = summarize(drows, 'verdict')
        for fame in ('conocida', 'poco_conocida'):
            direct[f'exactitud_{fame}'] = summarize([r for r in drows if r['fame'] == fame], 'verdict')['exactitud']

    for c in configs:
        for r in c['rows']:
            del r['prompt']
    out = dict(model=args.model, judge_model=args.judge_model, n=len(questions),
               configs=configs, direct=direct)
    with open(os.path.join(args.out, 'retrievers.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = report(out)
    with open(os.path.join(args.out, 'retrievers.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print('\n' + md)


def report(out):
    md = ['# Recuperación con EAM (m = 16, 8, 4) frente a similitud coseno\n',
          f"{out['n']} preguntas sobre el corpus. obra@K: la obra correcta está entre las K recuperadas; "
          'evid@C: el fragmento con la evidencia literal está entre los C que llegan al prompt. '
          'Exactitud = correcto + 0.5·parcial.\n']
    llm = out['direct'] is not None
    for W, C in SIZES:
        md += [f'\n## {W} obras / {C} fragmentos\n']
        head = f'| Recuperador | obra@{W} | evid@{C} |'
        sep = '|---|---|---|'
        if llm:
            head += ' Exactitud | Correcto | Parcial | Incorrecto | No lo sé | Conocidas | Poco conocidas |'
            sep += '---|---|---|---|---|---|---|'
        md += [head, sep]
        for c in out['configs']:
            if (c['top_works'], c['top_chunks']) != (W, C):
                continue
            line = f"| {c['name']} | {c['obra']:.2f} | {c['evid']:.2f} |"
            if llm:
                line += (f" **{c['exactitud']:.2f}** | {c['correcto']:.0%} | {c['parcial']:.0%} | "
                         f"{c['incorrecto']:.0%} | {c['no_sabe']:.0%} | {c['exactitud_conocida']:.2f} | "
                         f"{c['exactitud_poco_conocida']:.2f} |")
            md.append(line)
        if llm:
            d = out['direct']
            md.append(f"| LLM directo (sin recuperación) | — | — | **{d['exactitud']:.2f}** | {d['correcto']:.0%} | "
                      f"{d['parcial']:.0%} | {d['incorrecto']:.0%} | {d['no_sabe']:.0%} | "
                      f"{d['exactitud_conocida']:.2f} | {d['exactitud_poco_conocida']:.2f} |")
    return '\n'.join(md) + '\n'


if __name__ == '__main__':
    main()
