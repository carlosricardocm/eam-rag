# BM25: búsqueda por palabras clave sobre los fragmentos.
#
# Se usa para ordenar los fragmentos dentro de las obras que elige la EAM
# (o el coseno). Puntúa cada fragmento según cuántas palabras de la pregunta
# contiene, qué tan raras son en el corpus (idf) y su longitud.
#
# Tokenización: minúsculas, sin acentos, sin palabras vacías y sin reducir a la
# raíz. Parámetros estándar (k1 = 1.2, b = 0.75), sin ajustar con las preguntas
# de evaluación.

import math
import re
import unicodedata
from collections import Counter, defaultdict

import numpy as np

STOPWORDS = set('''
a al algo algunas algunos ante antes aquel aquella aquello aquellos así aun aunque cada como con contra cual
cuales cualquier cuando cuanto cuantos cuantas de del desde donde dos el él ella ellas ellos en entre era eran
es esa esas ese eso esos esta estaba estas este esto estos fue fueron ha había habían han hasta hay hace hacen
la las le les lo los más me mi mientras muy nada ni no nos o otra otras otro otros para pero poco por porque que
qué quien quién quienes quiénes se sea según ser si sí sin sobre son su sus también tan te tiene tienen todo
todos tras tu un una unas uno unos y ya yo cómo dónde cuándo cuánto cuántos cuántas cuál cuáles
'''.split())


def _strip_accents(s: str) -> str:
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')


STOP = {_strip_accents(w) for w in STOPWORDS}


def tokenize(text: str):
    text = _strip_accents(text.lower())
    return [t for t in re.findall(r'\w+', text) if len(t) > 1 and t not in STOP]


class BM25:
    def __init__(self, texts, k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        docs = [tokenize(t) for t in texts]
        self.n = len(docs)
        self.length = np.array([len(d) for d in docs], dtype=np.float64)
        self.avg = float(self.length.mean())
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.postings = defaultdict(list)          # término -> [(documento, frecuencia)]
        for i, d in enumerate(docs):
            for t, f in Counter(d).items():
                self.postings[t].append((i, f))

    def scores(self, query: str) -> np.ndarray:
        """Puntaje BM25 de cada documento (fragmento) para la consulta."""
        s = np.zeros(self.n)
        norm = self.k1 * (1 - self.b + self.b * self.length / self.avg)
        for t in set(tokenize(query)):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i, f in self.postings[t]:
                s[i] += idf * f * (self.k1 + 1) / (f + norm[i])
        return s
