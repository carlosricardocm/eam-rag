"""RAG con Memorias Asociativas Entrópicas.

  User query --SONAR--> cue --EAM (una memoria por obra)--> obras
             --> texto que recibe el LLM --augmentation--> OpenAI (GPT) --> respuesta

Modos (--modo), según lo que recibe el LLM de las obras que elige la EAM:
  obras  (por defecto)  el texto completo de las 3 mejores obras
  bm25                  los 16 fragmentos con mejor puntaje BM25 dentro de las 3 mejores obras
  eam                   los 8 fragmentos con mejor puntaje de la memoria dentro de las 5 mejores obras
--top-works y --top-chunks cambian esos números.

Uso:
  python rag.py "¿Qué enfermedad sufre Dahlmann tras golpearse la frente?"
  python rag.py --modo bm25 "..."     # 3 obras, 16 fragmentos BM25
  python rag.py --no-llm "..."        # sólo recuperación + prompt aumentado
  python rag.py                       # modo interactivo
"""
import argparse
import os
import sys

from eam_store import TOP_CHUNKS, TOP_WORKS, EAMStore
from generator import MODEL, answer, build_prompt
from sonar_encoder import SonarEncoder

HERE = os.path.dirname(os.path.abspath(__file__))
# modo: (obras, fragmentos) por defecto
MODES = {'obras': (3, None), 'bm25': (3, 16), 'eam': (TOP_WORKS, TOP_CHUNKS)}


def show_hits(hits):
    if not hits:
        print('  (ninguna memoria reconoció la consulta)')
    for i, h in enumerate(hits, 1):
        print(f'  [{i}] {h.author} - «{h.title}»  frag={h.chunk_score:.3f} '
              f'obra={h.work_score:.3f} mismatches={h.work_mismatches}')
        print('      ' + h.text[:200].replace('\n', ' ') + ('…' if len(h.text) > 200 else ''))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('query', nargs='*')
    ap.add_argument('--store', default=os.path.join(HERE, 'store'))
    ap.add_argument('--modo', choices=list(MODES), default='obras',
                    help='obras: texto completo de las mejores obras (por defecto); bm25: fragmentos BM25 '
                         'dentro de ellas; eam: fragmentos con la puntuación de la memoria')
    ap.add_argument('--top-works', type=int, help='obras que elige la EAM (por defecto según el modo)')
    ap.add_argument('--top-chunks', type=int, help='fragmentos para el LLM (modos bm25 y eam)')
    ap.add_argument('--criterion', choices=['loglik', 'dimex'])
    ap.add_argument('--min-z', type=float, help='umbral de reconocimiento relativo (criterio loglik); p. ej. 1.1')
    ap.add_argument('--tolerance', type=float, help='mismatches permitidos, fracción de n')
    ap.add_argument('--iota', type=float)
    ap.add_argument('--kappa', type=float)
    ap.add_argument('--sigma', type=float)
    ap.add_argument('--data', default=os.path.join(HERE, '..', 'datasets_csv'),
                    help='corpus original (texto completo de las obras)')
    ap.add_argument('--model', default=MODEL)
    ap.add_argument('--no-llm', action='store_true', help='no llamar al LLM; imprimir el prompt aumentado')
    args = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    store = EAMStore.load(args.store)
    overrides = {k: getattr(args, k) for k in ('criterion', 'min_z', 'tolerance', 'iota', 'kappa', 'sigma')
                 if getattr(args, k) is not None}
    if overrides:
        store.set_params(**overrides)
    encoder = SonarEncoder()
    works_k = args.top_works or MODES[args.modo][0]
    chunks_c = args.top_chunks or MODES[args.modo][1]
    # Los modos obras y bm25 necesitan el texto de las obras (y detectan las obras repetidas).
    texts = store.load_texts(args.data) if args.modo in ('obras', 'bm25') else None

    def run(query):
        cue = encoder.encode(query)
        if args.modo == 'obras':
            hits = store.retrieve_works(cue, works_k, texts)
        elif args.modo == 'bm25':
            hits = store.retrieve_bm25(cue, query, works_k, chunks_c)
        else:
            hits = store.retrieve(cue, works_k, chunks_c)
        print('\nRecuperación (EAM):')
        show_hits(hits)
        if args.no_llm:
            print('\nPrompt aumentado:\n' + build_prompt(query, hits))
            return
        print('\nRespuesta:')
        if not hits:
            print('No lo sé.')
        else:
            answer(query, hits, args.model, stream_to=sys.stdout)
        print()

    if args.query:
        run(' '.join(args.query))
        return
    while True:
        try:
            q = input('\nPregunta> ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q:
            run(q)


if __name__ == '__main__':
    main()
