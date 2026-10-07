"""Experimento: RAG con memorias asociativas frente a preguntar directamente al LLM.

Para cada pregunta de questions.json:
  - RAG:     SONAR -> EAM -> fragmentos -> prompt aumentado -> LLM (igual que rag.py)
  - Directo: la misma pregunta al mismo LLM, sin documentos.
Un LLM juez (que no sabe qué sistema produjo cada respuesta) compara cada
respuesta con la respuesta de referencia y la evidencia literal del cuento:
  correcto | parcial | incorrecto | no_sabe

Las preguntas sin obra (fuera del corpus) se reportan aparte: ahí "No lo sé."
es lo que se espera del RAG, mientras que el LLM directo puede contestarlas.

Las llamadas al LLM se guardan en results/compare_cache.jsonl, así que el
experimento se puede interrumpir y reanudar sin repetir llamadas.

Uso:
  python compare_llm.py [--model gpt-5.5] [--judge-model gpt-5.5] [--workers 8]
"""
import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from config import OPENAI_MODEL, require_openai_key
from eam_store import TOP_CHUNKS, TOP_WORKS, EAMStore
from generator import SYSTEM as RAG_SYSTEM
from generator import build_prompt

HERE = os.path.dirname(os.path.abspath(__file__))

DIRECT_SYSTEM = (
    "Eres un asistente experto en literatura latinoamericana. Respondes en "
    "español. Si no conoces la respuesta con seguridad, responde exactamente: "
    "\"No lo sé.\" Cuando respondas, menciona la obra y el autor de donde "
    "proviene la información, si aplica."
)

JUDGE_SYSTEM = (
    "Eres un evaluador estricto de respuestas a preguntas. Comparas una "
    "respuesta candidata con una respuesta de referencia. Devuelves sólo JSON."
)

JUDGE_TEMPLATE = """<pregunta>{q}</pregunta>
<respuesta_referencia>{ref}</respuesta_referencia>
{evidence}<respuesta_candidata>{cand}</respuesta_candidata>

Clasifica la respuesta candidata:
- "correcto": contiene lo esencial de la referencia y no afirma nada que la contradiga.
- "parcial": acierta una parte de lo esencial pero omite algo importante, o mezcla aciertos con algún error menor.
- "incorrecto": no contiene lo esencial, lo contradice o inventa hechos.
- "no_sabe": se abstiene ("No lo sé" o equivalente) sin dar una respuesta de fondo.
No penalices el estilo, la extensión ni que mencione o no la obra y el autor.

Devuelve JSON: {{"veredicto": "correcto|parcial|incorrecto|no_sabe", "razon": "<una oración>"}}"""

VERDICTS = ('correcto', 'parcial', 'incorrecto', 'no_sabe')
SCORE = {'correcto': 1.0, 'parcial': 0.5, 'incorrecto': 0.0, 'no_sabe': 0.0}


# ----------------------------------------------------------------- caché
class Cache:
    def __init__(self, path):
        self.path, self.lock, self.data = path, threading.Lock(), {}
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        d = json.loads(line)
                        self.data[d['key']] = d['value']

    @staticmethod
    def key(*parts):
        return hashlib.sha1('\x00'.join(parts).encode('utf-8')).hexdigest()

    def get(self, key):
        return self.data.get(key)

    def put(self, key, value):
        with self.lock:
            self.data[key] = value
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(dict(key=key, value=value), ensure_ascii=False) + '\n')


def chat(client, model, system, user, json_mode=False, retries=5):
    kw = dict(response_format={'type': 'json_object'}) if json_mode else {}
    for attempt in range(retries):
        try:
            r = client.chat.completions.create(
                model=model, messages=[{'role': 'system', 'content': system},
                                       {'role': 'user', 'content': user}], **kw)
            return dict(text=(r.choices[0].message.content or '').strip(),
                        prompt_tokens=r.usage.prompt_tokens,
                        completion_tokens=r.usage.completion_tokens)
        except Exception as e:  # límites de tasa, errores transitorios
            if attempt == retries - 1 or getattr(e, 'code', None) == 'insufficient_quota':
                raise
            wait = 2 ** attempt * 2
            print(f'  [reintento {attempt + 1} en {wait}s] {type(e).__name__}: {e}', file=sys.stderr)
            time.sleep(wait)


def cached_chat(cache, client, model, system, user, json_mode=False):
    k = Cache.key(model, system, user, str(json_mode))
    v = cache.get(k)
    if v is None:
        v = chat(client, model, system, user, json_mode)
        cache.put(k, v)
    return v


def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip().lower()


# ------------------------------------------------------------ experimento
def judge(cache, client, model, item, cand):
    ev = f"<evidencia_del_texto>{item['evidence']}</evidencia_del_texto>\n" if item.get('evidence') else ''
    out = cached_chat(cache, client, model, JUDGE_SYSTEM,
                      JUDGE_TEMPLATE.format(q=item['q'], ref=item['answer'], evidence=ev, cand=cand),
                      json_mode=True)
    try:
        d = json.loads(out['text'])
        v = d.get('veredicto', '').strip().lower()
        return (v if v in VERDICTS else 'incorrecto'), d.get('razon', '')
    except json.JSONDecodeError:
        return 'incorrecto', 'respuesta del juez no es JSON: ' + out['text'][:200]


def run_one(item, hits, cache, client, args):
    target = (item['title'].lower(), item['author'].lower()) if item.get('title') else None
    works = list(dict.fromkeys((h.title.lower(), h.author.lower()) for h in hits))
    ev = norm(item.get('evidence'))
    row = dict(q=item['q'], title=item.get('title'), author=item.get('author'),
               answer=item.get('answer'), fame=item.get('fame', 'conocida' if target else 'fuera'),
               in_corpus=target is not None,
               retrieved_works=[f'{t} ({a})' for t, a in works],
               work_hit=(target in works) if target else None,
               # ¿Algún fragmento recuperado contiene (un trozo de) la evidencia literal?
               evidence_hit=(any(ev[:80] in norm(h.text) for h in hits) if ev and target else None))

    if hits:
        rag = cached_chat(cache, client, args.model, RAG_SYSTEM, build_prompt(item['q'], hits))
    else:
        rag = dict(text='No lo sé.', prompt_tokens=0, completion_tokens=0)
    direct = cached_chat(cache, client, args.model, DIRECT_SYSTEM, item['q'])
    for name, out in (('rag', rag), ('direct', direct)):
        v, why = judge(cache, client, args.judge_model, item, out['text'])
        row[name] = dict(text=out['text'], verdict=v, reason=why,
                         prompt_tokens=out['prompt_tokens'], completion_tokens=out['completion_tokens'])
    return row


# ---------------------------------------------------------------- reporte
def pct(x):
    return f'{100 * x:.0f}%'


def table(rows, systems=('rag', 'direct')):
    lines = ['| Sistema | n | Exactitud | Correcto | Parcial | Incorrecto | No lo sé |',
             '|---|---|---|---|---|---|---|']
    names = dict(rag='RAG-EAM', direct='LLM directo')
    for s in systems:
        n = len(rows)
        c = {v: sum(r[s]['verdict'] == v for r in rows) / n for v in VERDICTS}
        acc = np.mean([SCORE[r[s]['verdict']] for r in rows])
        lines.append(f"| {names[s]} | {n} | **{acc:.2f}** | {pct(c['correcto'])} | {pct(c['parcial'])} | "
                     f"{pct(c['incorrecto'])} | {pct(c['no_sabe'])} |")
    return '\n'.join(lines)


def report(rows, args):
    inq = [r for r in rows if r['in_corpus']]
    outq = [r for r in rows if not r['in_corpus']]
    md = [f'# RAG-EAM frente a LLM directo\n',
          f'Modelo generador: `{args.model}` · juez: `{args.judge_model}` · '
          f'recuperación: {args.top_works} obras / {args.top_chunks} fragmentos · '
          f'{len(rows)} preguntas ({len(inq)} sobre el corpus, {len(outq)} fuera del corpus).\n',
          'Exactitud = correcto + 0.5·parcial.\n',
          f'## Preguntas sobre el corpus ({len(inq)})\n', table(inq)]
    for fame, label in (('conocida', 'Obras conocidas'), ('poco_conocida', 'Obras poco conocidas')):
        sub = [r for r in inq if r['fame'] == fame]
        if sub:
            md += [f'\n### {label} ({len(sub)})\n', table(sub)]
    hit = [r for r in inq if r['work_hit']]
    miss = [r for r in inq if not r['work_hit']]
    md += [f'\n### Según la recuperación de la EAM\n',
           f"La obra correcta está entre las recuperadas en {len(hit)}/{len(inq)} preguntas "
           f"({pct(len(hit) / len(inq))}); la evidencia literal llega al prompt en "
           f"{sum(bool(r['evidence_hit']) for r in inq)}/{len(inq)}.\n"]
    if hit:
        md += [f'\nCon la obra recuperada ({len(hit)}):\n', table(hit)]
    if miss:
        md += [f'\nSin la obra recuperada ({len(miss)}):\n', table(miss)]

    def ok(r, s):
        return r[s]['verdict'] == 'correcto'
    both = sum(ok(r, 'rag') and ok(r, 'direct') for r in inq)
    only_rag = [r for r in inq if ok(r, 'rag') and not ok(r, 'direct')]
    only_dir = [r for r in inq if ok(r, 'direct') and not ok(r, 'rag')]
    md += [f'\n### Pregunta por pregunta (sólo "correcto")\n',
           f'- Ambos correctos: {both}',
           f'- Sólo RAG correcto: {len(only_rag)}',
           f'- Sólo LLM directo correcto: {len(only_dir)}',
           f'- Ninguno: {len(inq) - both - len(only_rag) - len(only_dir)}']
    b, c = len(only_rag), len(only_dir)
    if b + c:
        # Prueba exacta de McNemar (binomial bilateral sobre los pares discordantes).
        from math import comb
        k = min(b, c)
        p = min(1.0, 2 * sum(comb(b + c, i) for i in range(k + 1)) / 2 ** (b + c))
        md.append(f'- McNemar exacta (pares discordantes {b} vs {c}): p = {p:.3g}')

    if outq:
        md += [f'\n## Preguntas fuera del corpus ({len(outq)})\n',
               'Aquí lo esperado del RAG es "No lo sé." (sólo debe responder con el corpus); '
               'el LLM directo responde con su conocimiento general.\n', table(outq)]

    tok = {s: (sum(r[s]['prompt_tokens'] for r in rows), sum(r[s]['completion_tokens'] for r in rows))
           for s in ('rag', 'direct')}
    md += ['\n## Costo en tokens (generación, sin el juez)\n',
           '| Sistema | Tokens de entrada | Tokens de salida |', '|---|---|---|',
           f"| RAG-EAM | {tok['rag'][0]:,} | {tok['rag'][1]:,} |",
           f"| LLM directo | {tok['direct'][0]:,} | {tok['direct'][1]:,} |"]

    md += ['\n## Detalle\n', '| # | Pregunta | Obra | Fama | EAM obra | RAG | Directo |',
           '|---|---|---|---|---|---|---|']
    for i, r in enumerate(rows, 1):
        hitmark = '—' if r['work_hit'] is None else ('✓' if r['work_hit'] else '✗')
        md.append(f"| {i} | {r['q']} | {r['title'] or '—'} | {r['fame']} | {hitmark} | "
                  f"{r['rag']['verdict']} | {r['direct']['verdict']} |")
    return '\n'.join(md) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--store', default=os.path.join(HERE, 'store'))
    ap.add_argument('--questions', default=os.path.join(HERE, 'questions.json'))
    ap.add_argument('--out', default=os.path.join(HERE, 'results'))
    ap.add_argument('--model', default=OPENAI_MODEL)
    ap.add_argument('--judge-model', default=OPENAI_MODEL)
    ap.add_argument('--top-works', type=int, default=TOP_WORKS)
    ap.add_argument('--top-chunks', type=int, default=TOP_CHUNKS)
    ap.add_argument('--workers', type=int, default=8)
    args = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(args.out, exist_ok=True)

    questions = json.load(open(args.questions, encoding='utf-8'))
    missing = [q['q'] for q in questions if not q.get('answer')]
    if missing:
        sys.exit(f'Faltan respuestas de referencia ("answer") en {len(missing)} preguntas, p. ej.: {missing[0]}')

    from openai import OpenAI
    from sonar_encoder import SonarEncoder
    client = OpenAI(api_key=require_openai_key())
    store = EAMStore.load(args.store)
    qemb = SonarEncoder().encode([q['q'] for q in questions])
    hits = [store.retrieve(e[None, :], args.top_works, args.top_chunks) for e in qemb]
    print(f'{len(questions)} preguntas; recuperación EAM lista. Llamando a {args.model}...')

    cache = Cache(os.path.join(args.out, 'compare_cache.jsonl'))
    done = [0]

    def task(i):
        try:
            row = run_one(questions[i], hits[i], cache, client, args)
        except Exception as e:
            print(f"  [falló] {type(e).__name__}: {str(e)[:120]} | {questions[i]['q'][:60]}")
            return None
        done[0] += 1
        print(f"  [{done[0]:3d}/{len(questions)}] RAG={row['rag']['verdict']:10} "
              f"DIR={row['direct']['verdict']:10} {row['q'][:70]}")
        return row

    with ThreadPoolExecutor(args.workers) as ex:
        rows = list(ex.map(task, range(len(questions))))
    failed = sum(r is None for r in rows)
    rows = [r for r in rows if r is not None]
    if failed:
        print(f'\n*** {failed} preguntas fallaron (se reintentan al volver a correr el script; '
              f'lo ya obtenido está en el caché). El reporte es PARCIAL. ***')

    with open(os.path.join(args.out, 'comparison.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    md = report(rows, args)
    if failed:
        md = md.replace('\n', f'\n\n> **Reporte parcial:** faltan {failed} de {len(questions)} preguntas.\n', 1)
    with open(os.path.join(args.out, 'comparison.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print('\n' + md.split('\n## Detalle')[0])
    print(f"Resultados: {os.path.join(args.out, 'comparison.md')} y comparison.json")


if __name__ == '__main__':
    main()
