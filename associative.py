# Memorias Asociativas Entrópicas (EAM) vectorizadas.
#
# Port de dimex/associative.py (Pineda, Fuentes y Morales; archivo original de
# Raul Peralta-Lozada, Apache 2.0) con dos cambios:
#
#   1. En vez de una clase por memoria, `MemoryBank` guarda K memorias apiladas
#      en un tensor R[K, m+1, n] para poder evaluar un cue contra todas a la vez
#      (en el RAG hay una memoria por obra, ~700 memorias).
#   2. Compatible con numpy >= 1.24 (dimex usa np.int / np.bool, ya removidos).
#
# La semántica se conserva:
#   - register  : abstracción  R <- R + r_io   (saturando en absolute_max)
#   - entropy   : entropía media de las columnas de R
#   - iota      : relación moderada por iota (celdas por debajo de iota*media -> 0)
#   - mismatches: número de rasgos del cue que caen en celdas vacías (containment)
#   - weight    : media de R[v_j, j] normalizada por max(R)
#   - recognize : mismatches <= tolerance  y  weight >= kappa * mean
#   - recall    : lambda-reducción (muestreo por columna con gaussiana sigma)
#   - penalty   : entropy / weight, criterio de AssociativeMemorySystem.recall
#
# Extensión (opcional): `soft_weight` suaviza la lectura de cada columna con la
# misma gaussiana sigma que dimex usa en recall, para tolerar cues cuyos valores
# caen cerca (no exactamente) de los registrados.

import numpy as np


def gaussian_kernel(m: int, sigma_levels: float) -> np.ndarray:
    """G[i, v] = exp(-(i-v)^2 / 2 s^2), s en niveles de cuantización."""
    idx = np.arange(m)
    s = max(float(sigma_levels), 1e-6)
    return np.exp(-((idx[:, None] - idx[None, :]) ** 2) / (2.0 * s * s))


class MemoryBank:
    def __init__(self, num_memories: int, n: int, m: int, tolerance: int = 0,
                 sigma: float = 0.25, iota: float = 0.0, kappa: float = 0.0,
                 absolute_max: int = 1023):
        """
        num_memories: K, número de memorias (una por obra en el RAG).
        n: tamaño del dominio (rasgos; 1024 para SONAR).
        m: tamaño del rango (niveles de cuantización).
        tolerance: mismatches permitidos entre el cue y la memoria.
        sigma: desviación estándar de la gaussiana usada al recordar,
            como fracción de m (igual que en dimex).
        """
        self.K, self.n, self.m = num_memories, n, m
        self.tolerance = tolerance
        self.sigma = sigma
        self.iota = iota
        self.kappa = kappa
        self.absolute_max = absolute_max
        # Fila m (la m+1-ésima) para funciones parciales: valor indefinido.
        self._relation = np.zeros((self.K, m + 1, n), dtype=np.uint16)
        self.counts = np.zeros(self.K, dtype=np.int64)
        self._cache = {}

    # ------------------------------------------------------------------ props
    @property
    def undefined(self):
        return self.m

    @property
    def relation(self):
        return self._relation[:, :self.m, :]

    @property
    def sigma(self):
        return self._sigma

    @sigma.setter
    def sigma(self, s):
        self._sigma = abs(s)
        self._kernel = gaussian_kernel(self.m, self._sigma * self.m)

    @property
    def iota(self):
        return self._iota

    @iota.setter
    def iota(self, i):
        if i < 0:
            raise ValueError('Iota must be a non negative number.')
        self._iota = i
        self._cache = {}

    def _cached(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    @property
    def max_values(self):
        """max(R_k) por memoria (nunca cero porque se usa como divisor)."""
        def f():
            mx = self.relation.reshape(self.K, -1).max(axis=1).astype(float)
            return np.where(mx == 0, 1.0, mx)
        return self._cached('max', f)

    @property
    def entropies(self):
        """Entropía (bits) de cada columna de cada memoria: (K, n)."""
        def f():
            r = self.relation.astype(np.float32)
            totals = r.sum(axis=1, keepdims=True)
            p = r / np.where(totals == 0, 1, totals)
            with np.errstate(divide='ignore', invalid='ignore'):
                h = -p * np.log2(np.where(p == 0, 1.0, p))
            return h.sum(axis=1)
        return self._cached('ent', f)

    @property
    def entropy(self):
        """Entropía de cada memoria: (K,)."""
        return self.entropies.mean(axis=1)

    @property
    def means(self):
        def f():
            r = self.relation
            sums = r.sum(axis=1, dtype=float)
            cnt = np.count_nonzero(r, axis=1)
            cnt = np.where(cnt == 0, 1, cnt)
            return (sums / cnt) / self.max_values[:, None]
        return self._cached('means', f)

    @property
    def mean(self):
        return self.means.mean(axis=1)

    @property
    def iota_relation(self):
        def f():
            r = self.relation
            if self.iota == 0:
                return r
            # Como en dimex, la media incluye la fila de valores indefinidos.
            sums = self._relation.sum(axis=1, dtype=float)
            cnt = np.count_nonzero(self._relation, axis=1)
            thr = self.iota * sums / np.where(cnt == 0, 1, cnt)
            return np.where(r < thr[:, None, :], 0, r)
        return self._cached('iota', f)

    # --------------------------------------------------------------- escritura
    def validate(self, vectors):
        """Valores fuera de [0, m) o NaN se consideran indefinidos."""
        v = np.nan_to_num(np.asarray(vectors, dtype=float), nan=self.undefined)
        v = np.where((v >= self.m) | (v < 0), self.undefined, v)
        return v.astype(np.int64)

    def register(self, k: int, vectors):
        """Registra (abstrae) uno o varios vectores en la memoria k."""
        v = self.validate(np.atleast_2d(vectors))
        cols = np.broadcast_to(np.arange(self.n), v.shape)
        add = np.zeros((self.m + 1, self.n), dtype=np.int64)
        np.add.at(add, (v, cols), 1)
        r = self._relation[k].astype(np.int64) + add
        self._relation[k] = np.minimum(r, self.absolute_max).astype(np.uint16)
        self.counts[k] += v.shape[0]
        self._cache = {}

    # ----------------------------------------------------------------- lectura
    def _cells(self, cue, rel=None):
        """R[k, v_j, j] para todo k: (K, n); rasgos indefinidos -> 0."""
        rel = self.relation if rel is None else rel
        v = self.validate(cue)
        defined = v != self.undefined
        vals = np.zeros((self.K, self.n), dtype=float)
        j = np.nonzero(defined)[0]
        vals[:, j] = rel[:, v[j], j]
        return vals, defined

    def mismatches(self, cue):
        vals, defined = self._cells(cue, self.iota_relation)
        return np.count_nonzero((vals == 0) & defined[None, :], axis=1)

    def weight(self, cue):
        """Peso dimex: media de R[v_j, j] / max(R)."""
        vals, _ = self._cells(cue)
        return vals.mean(axis=1) / self.max_values

    def soft_weight(self, cue):
        """Peso suavizado: sum_i R[i,j] G(i, v_j), normalizado por max(R)."""
        v = self.validate(cue)
        defined = v != self.undefined
        g = self._kernel[:, np.where(defined, v, 0)] * defined  # (m, n)
        vals = np.einsum('kij,ij->kj', self.relation, g, dtype=np.float64)
        return vals.mean(axis=1) / self.max_values

    def log_likelihood(self, cue, eps=0.01):
        """mean_j log( sum_i R[i,j] G(i, v_j) / N_k + eps ).

        Generalización graduada de mismatches + weight: con sigma -> 0 cada
        rasgo del cue que cae en una celda vacía (un mismatch) aporta log(eps),
        y los demás aportan el log de la frecuencia con que la memoria lo vio.
        A diferencia de entropy/weight, no favorece memorias con pocos
        registros (una obra de un solo fragmento tiene entropía 0)."""
        v = self.validate(cue)
        defined = v != self.undefined
        g = self._kernel[:, np.where(defined, v, 0)]  # (m, n)
        vals = np.einsum('kij,ij->kj', self.relation, g, dtype=np.float64)
        counts = np.where(self.counts == 0, 1, self.counts)[:, None]
        ll = np.log(vals / counts + eps)
        return (ll * defined).sum(axis=1) / max(defined.sum(), 1)

    def recognize(self, cue, soft=False):
        """(aceptada[K], weight[K], mismatches[K]) como en AssociativeMemory."""
        mis = self.mismatches(cue)
        w = self.soft_weight(cue) if soft else self.weight(cue)
        accept = (mis <= self.tolerance) & (w >= self.mean * self.kappa)
        return accept, w, mis

    def penalties(self, cue, soft=False):
        """Criterio de AssociativeMemorySystem.recall: entropy/weight
        (inf para memorias que no reconocen el cue)."""
        accept, w, mis = self.recognize(cue, soft)
        with np.errstate(divide='ignore'):
            pen = np.where(w > 0, self.entropy / w, np.inf)
        return np.where(accept, pen, np.inf), accept, w, mis

    def recall(self, k: int, cue, rng=None):
        """Lambda-reducción de la memoria k guiada por el cue: devuelve un
        vector (con NaN en rasgos indefinidos) o todo NaN si no se acepta."""
        rng = np.random.default_rng() if rng is None else rng
        accept, _, _ = self.recognize(cue)
        if not accept[k]:
            return np.full(self.n, np.nan), False
        v = self.validate(cue)
        rel = self.relation[k].astype(float)  # (m, n)
        defined = v != self.undefined
        col = np.where(defined[None, :], rel * self._kernel[:, np.where(defined, v, 0)], rel)
        tot = col.sum(axis=0)
        cdf = np.cumsum(col, axis=0) / np.where(tot == 0, 1, tot)
        u = rng.random(self.n)
        out = (cdf < u[None, :]).sum(axis=0).clip(0, self.m - 1).astype(float)
        out[tot == 0] = np.nan
        return out, True

    # ----------------------------------------------------------- persistencia
    def state(self):
        return dict(relation=self._relation, counts=self.counts,
                    params=np.array([self.tolerance, self.sigma, self.iota,
                                     self.kappa, self.absolute_max], dtype=float))

    @classmethod
    def from_state(cls, relation, counts, params):
        K, m1, n = relation.shape
        t, s, i, k, amax = params
        bank = cls(K, n, m1 - 1, int(t), float(s), float(i), float(k), int(amax))
        bank._relation = relation.astype(np.uint16)
        bank.counts = counts
        return bank
