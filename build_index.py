"""Construye la base de memorias asociativas entrópicas a partir del corpus.

Uso:
  python build_index.py [--data ../datasets_csv] [--out store] [--m 16]
                        [--max-words 120] [--quant quantile]

Los embeddings SONAR se guardan en <out>/embeddings.npy; si ya existen y los
fragmentos no cambiaron, se reutilizan y sólo se reconstruyen las memorias.
"""
import argparse
import hashlib
import os
import time

import numpy as np

from corpus import build_chunks, load_works
from eam_store import EAMStore

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', default=os.path.join(HERE, '..', 'datasets_csv'))
    ap.add_argument('--out', default=os.path.join(HERE, 'store'))
    ap.add_argument('--m', type=int, default=16, help='niveles de cuantización (rango de la memoria)')
    ap.add_argument('--quant', choices=['quantile', 'minmax'], default='quantile')
    ap.add_argument('--max-words', type=int, default=120)
    ap.add_argument('--overlap', type=int, default=1)
    ap.add_argument('--batch-size', type=int, default=32)
    args = ap.parse_args()

    works = load_works(args.data)
    chunks = build_chunks(works, args.max_words, args.overlap)
    print(f'{len(works)} obras, {len(chunks)} fragmentos')

    os.makedirs(args.out, exist_ok=True)
    emb_path = os.path.join(args.out, 'embeddings.npy')
    sig_path = os.path.join(args.out, 'embeddings.sha1')
    sig = hashlib.sha1('\x00'.join(c.text for c in chunks).encode('utf-8')).hexdigest()
    if os.path.exists(emb_path) and os.path.exists(sig_path) and open(sig_path).read() == sig:
        emb = np.load(emb_path)
        print('Embeddings reutilizados:', emb.shape)
    else:
        from sonar_encoder import SonarEncoder
        enc = SonarEncoder()
        t = time.time()
        emb = enc.encode([c.text for c in chunks], args.batch_size, show_progress=True)
        print(f'Embeddings SONAR {emb.shape} en {time.time() - t:.0f}s ({enc.device})')
        np.save(emb_path, emb)
        with open(sig_path, 'w') as f:
            f.write(sig)

    store = EAMStore.build(works, chunks, emb, m=args.m, quant=args.quant)
    store.save(args.out)
    b = store.bank
    print(f'Memorias: {b.K} x ({b.m} x {b.n}); entropía media {b.entropy.mean():.3f} bits')
    print('Guardado en', args.out)


if __name__ == '__main__':
    main()
