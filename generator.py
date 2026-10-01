# Augmentation + generación: añade los fragmentos recuperados a la consulta
# y pide la respuesta a un modelo de OpenAI.
#
# La API key y el modelo se leen del archivo .env de la raíz del proyecto
# (ver config.py) o de las variables de entorno OPENAI_API_KEY / OPENAI_MODEL.

from config import OPENAI_MODEL, require_openai_key

SYSTEM = (
    "Eres un asistente experto en literatura latinoamericana. Respondes en "
    "español usando únicamente los fragmentos de obras que se te proporcionan. "
    "Si la respuesta no está en los fragmentos, responde exactamente: \"No lo sé.\" "
    "Cuando respondas, menciona la obra y el autor de donde proviene la información."
)

MODEL = OPENAI_MODEL


def build_prompt(query: str, hits) -> str:
    """Plantilla del bloque AUGMENTATION del diagrama:
    Answer <user query>, based on the <doc>. If answer not in the document,
    say "I don't know"."""
    docs = '\n\n'.join(
        f'<documento indice="{i}" obra="{h.title}" autor="{h.author}">\n{h.text}\n</documento>'
        for i, h in enumerate(hits, 1))
    if not docs:
        docs = '<documento>(la memoria asociativa no reconoció la consulta; no hay documentos)</documento>'
    return (f'<documentos>\n{docs}\n</documentos>\n\n'
            f'Responde la siguiente pregunta basándote en los documentos anteriores. '
            f'Si la respuesta no está en los documentos, di "No lo sé."\n\n'
            f'<pregunta>{query}</pregunta>')


def answer(query: str, hits, model: str = MODEL, stream_to=None) -> str:
    from openai import OpenAI

    if not hits:
        return 'No lo sé.'
    client = OpenAI(api_key=require_openai_key())
    stream = client.chat.completions.create(
        model=model,
        messages=[{'role': 'system', 'content': SYSTEM},
                  {'role': 'user', 'content': build_prompt(query, hits)}],
        stream=True,
    )
    parts = []
    for chunk in stream:
        if not chunk.choices:
            continue
        text = chunk.choices[0].delta.content or ''
        parts.append(text)
        if stream_to is not None and text:
            stream_to.write(text)
            stream_to.flush()
    return ''.join(parts).strip() or 'No lo sé.'
