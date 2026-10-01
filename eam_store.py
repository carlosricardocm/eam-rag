# "Base de datos" del RAG basada en Memorias Asociativas Entrópicas.
#
# Sustituye a la vector database del diagrama:
#   - Cada obra (cuento, minicuento, ensayo...) tiene su propia memoria asociativa.
#   - Los embeddings SONAR de sus fragmentos se cuantizan a m niveles y se
#     registran (abstraen) en la memoria de la obra.
#   - La consulta, codificada también con SONAR y cuantizada, se usa como cue:
#       1) cada memoria puntúa el cue y se eligen las obras mejor puntuadas.
#          criterion='loglik' (por defecto): log-verosimilitud suave del cue
#          en la memoria (ver MemoryBank.log_likelihood); con min_z, una
#          memoria reconoce el cue sólo si su score está al menos min_z
#          desviaciones estándar por encima de la media de todas las memorias
#          (análogo relativo a kappa en dimex).
#          criterion='dimex': reconocimiento con tolerance/iota/kappa y orden
#          por entropy/weight, exactamente como AssociativeMemorySystem.recall.
#       2) dentro de las obras recuperadas, cada fragmento se puntúa con el
#          peso suavizado de una memoria que contiene sólo ese fragmento.
#   - Si ninguna memoria reconoce el cue, no se recupera nada y el generador
#     responde "No lo sé".

import json
import os
from dataclasses import asdict, dataclass

import numpy as np

from associative import MemoryBank, gaussian_kernel
from corpus import Chunk, Work

# Recuperación por defecto: mejores obras (memorias) y, dentro de ellas, mejores fragmentos.
TOP_WORKS = 5
TOP_CHUNKS = 8


class Quantizer:
    """Cuantiza embeddings reales a enteros en [0, m).

    'quantile': cortes por rasgo en cuantiles del corpus (niveles
        equiprobables, máxima entropía por rasgo).
    'minmax'  : escala global min-max, como msize_features en dimex/eam.py.
    """

    def __init__(self, m: int, method: str = 'quantile'):
        self.m, self.method = m, method
        self.edges = None
        self.lo = self.hi = None

    def fit(self, X: np.ndarray):
        if self.method == 'quantile':
            qs = np.linspace(0, 1, self.m + 1)[1:-1]
            self.edges = np.quantile(X, qs, axis=0).T.astype(np.float32)  # (n, m-1)
        else:
            self.lo, self.hi = float(X.min()), float(X.max())
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        if self.method == 'quantile':
            codes = np.empty(X.shape, dtype=np.uint8)
            for j in range(X.shape[1]):
                codes[:, j] = np.searchsorted(self.edges[j], X[:, j], side='right')
            return codes
        v = np.round((self.m - 1) * (X - self.lo) / (self.hi - self.lo))
        return np.clip(v, 0, self.m - 1).astype(np.uint8)

    def state(self):
        return dict(q_m=np.array(self.m), q_method=np.array(self.method),
                    q_edges=self.edges if self.edges is not None else np.zeros(0),
                    q_range=np.array([self.lo or 0.0, self.hi or 0.0]))

    @classmethod
    def from_state(cls, d):
        q = cls(int(d['q_m']), str(d['q_method']))
        if q.method == 'quantile':
            q.edges = d['q_edges']
        else:
            q.lo, q.hi = map(float, d['q_range'])
        return q


@dataclass
class Hit:
    chunk_id: int
    work_id: int
    author: str
    title: str
    text: str
    chunk_score: float
    work_score: float
    work_mismatches: int


class EAMStore:
    def __init__(self, works, chunks, quantizer, bank, codes, config):
        self.works, self.chunks = works, chunks
        self.quantizer, self.bank, self.codes = quantizer, bank, codes
        self.config = config
        self.chunks_of = {}
        for c in chunks:
            self.chunks_of.setdefault(c.work_id, []).append(c.chunk_id)
        self._chunk_kernel = gaussian_kernel(quantizer.m, config['chunk_sigma'] * quantizer.m)

    # --------------------------------------------------------------- build
    @classmethod
    def build(cls, works, chunks, embeddings, m=16, quant='quantile',
              criterion='loglik', sigma=0.3, eps=0.01, min_z=None,
              tolerance=1.0, iota=0.0, kappa=0.0, soft=False, chunk_sigma=0.2):
        """sigma, chunk_sigma: fracción de m. tolerance: fracción de n
        (1.0 = cualquier número de mismatches). min_z=None: sin umbral."""
        n = embeddings.shape[1]
        quantizer = Quantizer(m, quant).fit(embeddings)
        codes = quantizer.transform(embeddings)
        bank = MemoryBank(len(works), n, m, int(round(tolerance * n)),
                          sigma, iota, kappa)
        work_of = np.array([c.work_id for c in chunks])
        for w in works:
            idx = np.nonzero(work_of == w.work_id)[0]
            if len(idx):
                bank.register(w.work_id, codes[idx])
        config = dict(m=m, quant=quant, criterion=criterion, sigma=sigma, eps=eps,
                      min_z=min_z, tolerance=tolerance, iota=iota,
                      kappa=kappa, soft=soft, chunk_sigma=chunk_sigma)
        return cls(works, chunks, quantizer, bank, codes, config)

    def set_params(self, **kw):
        """Ajusta parámetros de recuperación sin reconstruir las memorias."""
        self.config.update(kw)
        b = self.bank
        if 'tolerance' in kw:
            b.tolerance = int(round(kw['tolerance'] * b.n))
        if 'sigma' in kw:
            b.sigma = kw['sigma']
        if 'iota' in kw:
            b.iota = kw['iota']
        if 'kappa' in kw:
            b.kappa = kw['kappa']
        if 'chunk_sigma' in kw:
            self._chunk_kernel = gaussian_kernel(self.quantizer.m, kw['chunk_sigma'] * self.quantizer.m)

    # ------------------------------------------------------------ retrieval
    def rank_works(self, query_emb):
        """Devuelve (cue, obras reconocidas ordenadas, score por obra,
        mismatches por obra). Score: mayor es mejor."""
        cfg = self.config
        cue = self.quantizer.transform(query_emb)[0]
        mis = self.bank.mismatches(cue)
        if cfg['criterion'] == 'dimex':
            pen, _, _, _ = self.bank.penalties(cue, soft=cfg['soft'])
            score = -pen
        else:
            score = self.bank.log_likelihood(cue, cfg['eps'])
            score = np.where(mis <= self.bank.tolerance, score, -np.inf)
            if cfg.get('min_z') is not None:
                fin = score[np.isfinite(score)]
                z = (score - fin.mean()) / (fin.std() or 1.0)
                score = np.where(z >= cfg['min_z'], score, -np.inf)
        order = np.argsort(-score, kind='stable')
        order = order[np.isfinite(score[order])]
        return cue, order, score, mis

    def chunk_scores(self, cue, chunk_ids):
        """Peso suavizado de una memoria de un solo fragmento:
        mean_j G(code_cj, cue_j)."""
        codes = self.codes[chunk_ids].astype(np.int64)  # (C, n)
        return self._chunk_kernel[codes, cue[None, :].astype(np.int64)].mean(axis=1)

    def retrieve(self, query_emb, top_works: int = TOP_WORKS, top_chunks: int = TOP_CHUNKS):
        cue, order, wscore, mis = self.rank_works(query_emb)
        sel = order[:top_works]
        cand = [cid for wid in sel for cid in self.chunks_of.get(int(wid), [])]
        if not cand:
            return []
        scores = self.chunk_scores(cue, np.array(cand))
        best = np.argsort(-scores)[:top_chunks]
        hits = []
        for b in best:
            c = self.chunks[cand[b]]
            w = self.works[c.work_id]
            hits.append(Hit(c.chunk_id, w.work_id, w.author, w.title, c.text,
                            float(scores[b]), float(wscore[w.work_id]),
                            int(mis[w.work_id])))
        return hits

    # ---------------------------------------------------------- persistence
    def save(self, path: str):
        os.makedirs(path, exist_ok=True)
        np.savez_compressed(os.path.join(path, 'memories.npz'),
                            codes=self.codes, **self.bank.state(),
                            **self.quantizer.state())
        with open(os.path.join(path, 'store.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(config=self.config,
                           works=[{k: v for k, v in asdict(w).items() if k != 'text'}
                                  for w in self.works],
                           chunks=[asdict(c) for c in self.chunks]),
                      f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str):
        d = np.load(os.path.join(path, 'memories.npz'), allow_pickle=False)
        with open(os.path.join(path, 'store.json'), encoding='utf-8') as f:
            meta = json.load(f)
        works = [Work(text='', **w) for w in meta['works']]
        chunks = [Chunk(**c) for c in meta['chunks']]
        bank = MemoryBank.from_state(d['relation'], d['counts'], d['params'])
        return cls(works, chunks, Quantizer.from_state(d), bank, d['codes'], meta['config'])
