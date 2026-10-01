"""Evalúa la recuperación con memorias asociativas entrópicas frente a una
vector database (similitud coseno sobre los mismos embeddings SONAR).

Dos conjuntos de consultas:
  - sintético: una oración interior de N fragmentos al azar (objetivo = su obra
    y su fragmento);
  - preguntas: questions.json, preguntas escritas a mano sobre cuentos
    conocidos, más preguntas fuera del corpus (objetivo = rechazar).

Uso:
  python evaluate.py [--store store] [--n 300] [--grid] [--m 4 8 16]
"""
import argparse
import hashlib
import itertools
import json
import os
import sys

import numpy as np

from corpus import split_sentences
from eam_store import TOP_CHUNKS, TOP_WORKS, EAMStore

HERE = os.path.dirname(os.path.abspath(__file__))


def synthetic_queries(store, n, seed=0):
    rng = np.random.default_rng(seed)
    qs = []
    for cid in rng.permutation(len(store.chunks)):
        sents = [s for s in split_sentences(store.chunks[cid].text) if len(s.split()) >= 10]
        if len(sents) >= 2:
            qs.append((sents[len(sents) // 2], int(cid), store.chunks[cid].work_id))
        if len(qs) == n:
            break
    return qs


def text_sig(texts):
    return hashlib.sha1('\x00'.join(texts).encode('utf-8')).hexdigest()


def cosine_baseline(emb_norm, work_of, q, k_chunks=TOP_CHUNKS):
    sims = emb_norm @ (q / np.linalg.norm(q))
    top = np.argsort(-sims)
    works = list(dict.fromkeys(work_of[top[:200]]))
    return works, top[:k_chunks], sims


def eval_synthetic(store, qemb, queries, emb_norm, work_of, top_works=TOP_WORKS, top_chunks=TOP_CHUNKS):
    r = dict(eam_w1=0, eam_wk=0, eam_c=0, cos_w1=0, cos_wk=0, cos_c=0, rejected=0)
    for (text, cid, wid), q in zip(queries, qemb):
        _, order, _, _ = store.rank_works(q[None, :])
        r['rejected'] += len(order) == 0
        r['eam_w1'] += wid in order[:1]
        r['eam_wk'] += wid in order[:top_works]
        hits = store.retrieve(q[None, :], top_works, top_chunks)
        r['eam_c'] += cid in [h.chunk_id for h in hits]
        works, chunks, _ = cosine_baseline(emb_norm, work_of, q, top_chunks)
        r['cos_w1'] += wid in works[:1]
        r['cos_wk'] += wid in works[:top_works]
        r['cos_c'] += cid in chunks
    return {k: v / len(queries) for k, v in r.items()}


def eval_questions(store, qemb, questions, emb_norm, work_of, top_works=TOP_WORKS, verbose=False):
    # (título, autor): hay títulos repetidos entre autores distintos.
    title_of = {w.work_id: (w.title.lower(), w.author.lower()) for w in store.works}
    rows = []
    for item, q in zip(questions, qemb):
        _, order, pen, mis = store.rank_works(q[None, :])
        works, _, sims = cosine_baseline(emb_norm, work_of, q)
        target = (item['title'].lower(), item['author'].lower()) if item['title'] else None
        eam_titles = [title_of[w] for w in order[:top_works]]
        cos_titles = [title_of[w] for w in works[:top_works]]
        rows.append(dict(q=item['q'], target=target, accepted=len(order),
                         eam=target in eam_titles if target else len(order) == 0,
                         cos=target in cos_titles if target else None,
                         eam_top=eam_titles, cos_top=cos_titles))
    if verbose:
        for r in rows:
            print(f"  EAM {'✓' if r['eam'] else '✗'} COS {'✓' if r['cos'] else ('-' if r['cos'] is None else '✗')} "
                  f"acc={r['accepted']:3d} | {r['q'][:60]}\n      eam={r['eam_top']}\n      cos={r['cos_top']}")
    inq = [r for r in rows if r['target']]
    outq = [r for r in rows if not r['target']]
    return dict(eam_hitk=np.mean([r['eam'] for r in inq]),
                cos_hitk=np.mean([r['cos'] for r in inq]),
                eam_reject_ood=np.mean([r['eam'] for r in outq]) if outq else float('nan'),
                eam_accept_rate=np.mean([r['accepted'] > 0 for r in inq]))


def evaluate_config(store, cfg, qs_emb, queries, qq_emb, questions, emb_norm, work_of, verbose=False,
                    top_works=TOP_WORKS, top_chunks=TOP_CHUNKS):
    store.set_params(**{k: cfg[k] for k in ('criterion', 'soft', 'sigma', 'tolerance', 'min_z') if k in cfg})
    syn = eval_synthetic(store, qs_emb, queries, emb_norm, work_of, top_works, top_chunks)
    qs = eval_questions(store, qq_emb, questions, emb_norm, work_of, top_works, verbose=verbose)
    W, C = top_works, top_chunks
    c = store.config
    soft = f"soft={c['soft']!s:5} " if c['criterion'] == 'dimex' else ''
    print(f"m={c['m']:<2} {c['criterion']:6} {soft}sigma={c['sigma']:.2f} tol={c['tolerance']:.2f} min_z={c['min_z']} | "
          f"SINT obra@1 EAM {syn['eam_w1']:.3f} / COS {syn['cos_w1']:.3f}  obra@{W} EAM {syn['eam_wk']:.3f} / COS {syn['cos_wk']:.3f}  "
          f"frag@{C} EAM {syn['eam_c']:.3f} / COS {syn['cos_c']:.3f}  rech {syn['rejected']:.2f} | "
          f"PREG obra@{W} EAM {qs['eam_hitk']:.2f} / COS {qs['cos_hitk']:.2f}  acepta {qs['eam_accept_rate']:.2f}  rechazo-OOD {qs['eam_reject_ood']:.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--store', default=os.path.join(HERE, 'store'))
    ap.add_argument('--n', type=int, default=300, help='número de consultas sintéticas')
    ap.add_argument('--grid', action='store_true', help='barrido de sigma/tolerance/soft')
    ap.add_argument('--m', type=int, nargs='+',
                    help='tamaños del rango (filas/niveles) a comparar, p. ej. --m 4 8 16; '
                         'reconstruye las memorias en memoria sin tocar el store')
    ap.add_argument('--top-works', type=int, default=TOP_WORKS, help='obras recuperadas (obra@K)')
    ap.add_argument('--top-chunks', type=int, default=TOP_CHUNKS, help='fragmentos recuperados (frag@K)')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')

    store = EAMStore.load(args.store)
    emb = np.load(os.path.join(args.store, 'embeddings.npy'))
    emb_norm = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    work_of = np.array([c.work_id for c in store.chunks])

    queries = synthetic_queries(store, args.n)
    questions = json.load(open(os.path.join(HERE, 'questions.json'), encoding='utf-8'))
    # El caché guarda una huella SHA-1 de los textos: si cambian las consultas
    # sintéticas o alguna pregunta, se vuelven a codificar sólo las que cambiaron.
    syn_sig = text_sig(q[0] for q in queries)
    qq_sig = text_sig(q['q'] for q in questions)
    cache = os.path.join(args.store, f'eval_queries_{args.n}.npz')
    d = dict(np.load(cache)) if os.path.exists(cache) else {}
    qs_emb, qq_emb = d.get('syn'), d.get('questions')
    enc = None
    if qs_emb is None or str(d.get('syn_sig', '')) != syn_sig:
        from sonar_encoder import SonarEncoder
        enc = SonarEncoder()
        qs_emb = enc.encode([q[0] for q in queries])
    if qq_emb is None or str(d.get('questions_sig', '')) != qq_sig:
        from sonar_encoder import SonarEncoder
        enc = enc or SonarEncoder()
        qq_emb = enc.encode([q['q'] for q in questions])
    if enc is not None:
        np.savez(cache, syn=qs_emb, questions=qq_emb, syn_sig=syn_sig, questions_sig=qq_sig)

    configs = [dict(store.config)]
    if args.grid:
        configs = [dict(criterion='dimex', soft=sf, sigma=0.1, tolerance=t, min_z=None)
                   for sf, t in itertools.product([False, True], [1.0, 0.5])]
        configs += [dict(criterion='loglik', sigma=g, tolerance=1.0, min_z=None)
                    for g in [0.1, 0.2, 0.3, 0.4]]
        configs += [dict(criterion='loglik', sigma=0.3, tolerance=1.0, min_z=th)
                    for th in [1.05, 1.1, 1.15]]
    elif args.m:
        configs = [dict(criterion='loglik', sigma=g, tolerance=1.0, min_z=None)
                   for g in [0.1, 0.2, 0.3, 0.4, 0.5]]
        configs += [dict(criterion='loglik', sigma=0.3, tolerance=1.0, min_z=th)
                    for th in [1.05, 1.1, 1.15]]
    print(f'{len(queries)} consultas sintéticas, {len(questions)} preguntas; config={store.config}')
    stores = [store]
    if args.m:
        # Mismos embeddings y fragmentos; sólo cambian la cuantización y las memorias.
        stores = (EAMStore.build(store.works, store.chunks, emb, m=m, quant=store.config['quant'])
                  for m in args.m)
    for st in stores:
        b = st.bank
        print(f'\n== memorias {b.K} x ({b.m} x {b.n}), entropía media {b.entropy.mean():.3f} bits '
              f'(máx {np.log2(b.m):.0f}), R ocupa {b._relation.nbytes / 2**20:.1f} MB')
        for cfg in configs:
            evaluate_config(st, cfg, qs_emb, queries, qq_emb, questions, emb_norm, work_of, args.verbose,
                            args.top_works, args.top_chunks)


if __name__ == '__main__':
    main()
