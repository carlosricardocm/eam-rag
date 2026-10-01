# Carga del Knowledge Base (datasets_csv) y partición en fragmentos (chunks).

import ast
import glob
import os
import re
from collections import Counter
from dataclasses import dataclass

import pandas as pd


@dataclass
class Work:
    work_id: int
    author: str
    title: str
    genre: str
    link: str
    text: str


@dataclass
class Chunk:
    chunk_id: int
    work_id: int
    text: str


def _parse_meta(raw):
    try:
        meta = ast.literal_eval(raw)
        return meta if isinstance(meta, dict) else {}
    except (ValueError, SyntaxError):
        return {}


def load_works(data_dir: str) -> list:
    """Lee todos los CSV (link, text_metadata, text), elimina duplicados por
    link y corrige filas cuyo autor quedó desplazado en el metadato."""
    works, seen = [], set()
    for path in sorted(glob.glob(os.path.join(data_dir, '*.csv'))):
        df = pd.read_csv(path, encoding='utf-8')
        metas = [_parse_meta(m) for m in df['text_metadata']]
        # Autor más frecuente del archivo, para las filas mal etiquetadas.
        authors = Counter(m.get('author', '') for m in metas
                          if m.get('author') and not m['author'].startswith('['))
        file_author = authors.most_common(1)[0][0] if authors else \
            os.path.basename(path).replace('_full_texts.csv', '')
        for meta, (_, row) in zip(metas, df.iterrows()):
            text = row['text'] if isinstance(row['text'], str) else ''
            if row['link'] in seen or len(text.strip()) == 0:
                continue
            seen.add(row['link'])
            author = meta.get('author', '')
            genre = meta.get('metadata', '')
            if not author or author.startswith('['):
                genre, author = author, file_author
            works.append(Work(len(works), author, meta.get('title', '').strip(),
                              genre.strip('[] .'), row['link'], text.strip()))
    return works


_SENT_RE = re.compile(r'(?<=[.!?…»”])\s+(?=[—¿¡«“A-ZÁÉÍÓÚÑ0-9])')


def split_sentences(text: str) -> list:
    sents = []
    for para in re.split(r'\n\s*\n|\r\n|\n', text):
        para = para.strip()
        if para:
            sents.extend(s.strip() for s in _SENT_RE.split(para) if s.strip())
    return sents


def chunk_work(work: Work, max_words: int = 120, overlap: int = 1) -> list:
    """Agrupa oraciones consecutivas hasta ~max_words palabras, repitiendo las
    últimas `overlap` oraciones al inicio del siguiente fragmento.
    SONAR es un codificador de oraciones, así que fragmentos cortos funcionan
    mejor que párrafos largos."""
    sents = split_sentences(work.text)
    chunks, cur, words = [], [], 0
    for s in sents:
        w = len(s.split())
        if cur and words + w > max_words:
            chunks.append(' '.join(cur))
            cur = cur[-overlap:] if overlap else []
            words = sum(len(x.split()) for x in cur)
        cur.append(s)
        words += w
    if cur and (not chunks or ' '.join(cur) not in chunks[-1]):
        chunks.append(' '.join(cur))
    return chunks


def build_chunks(works: list, max_words: int = 120, overlap: int = 1) -> list:
    chunks = []
    for w in works:
        for text in chunk_work(w, max_words, overlap):
            chunks.append(Chunk(len(chunks), w.work_id, text))
    return chunks
