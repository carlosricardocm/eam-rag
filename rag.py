"""RAG con Memorias Asociativas Entrópicas.

  User query --SONAR--> cue --EAM (una memoria por obra)--> fragmentos
             --augmentation--> OpenAI (GPT) --> respuesta

Uso:
  python rag.py "¿Qué enfermedad sufre Dahlmann tras golpearse la frente?"
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
    ap.add_argument('--top-works', type=int, default=TOP_WORKS)
    ap.add_argument('--top-chunks', type=int, default=TOP_CHUNKS)
    ap.add_argument('--criterion', choices=['loglik', 'dimex'])
    ap.add_argument('--min-z', type=float, help='umbral de reconocimiento relativo (criterio loglik); p. ej. 1.1')
    ap.add_argument('--tolerance', type=float, help='mismatches permitidos, fracción de n')
    ap.add_argument('--iota', type=float)
    ap.add_argument('--kappa', type=float)
    ap.add_argument('--sigma', type=float)
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

    def run(query):
        hits = store.retrieve(encoder.encode(query), args.top_works, args.top_chunks)
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
