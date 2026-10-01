"""Verifica que eam_rag.associative.MemoryBank reproduce dimex/associative.py.

Requiere numpy < 1.24 (dimex usa np.int/np.bool), p. ej. el entorno `eam`:
  D:/anaconda3/envs/eam/python.exe eam_rag/tests/test_fidelity.py
"""
import importlib.util
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'dimex'))
import associative as orig  # noqa: E402

spec = importlib.util.spec_from_file_location('new_associative', os.path.join(ROOT, 'eam_rag', 'associative.py'))
new = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new)


def test_bank_matches_dimex():
    rng = np.random.default_rng(1)
    n, m, K = 40, 8, 3
    for iota, tol, kappa in [(0, 0, 0), (0.5, 5, 0), (1.0, 12, 0.5), (0, 20, 1.0)]:
        bank = new.MemoryBank(K, n, m, tol, 0.25, iota, kappa)
        ams = [orig.AssociativeMemory(n, m, tol, 0.25, iota, kappa) for _ in range(K)]
        for k in range(K):
            X = rng.integers(0, m, (30, n)).astype(float)
            X[rng.random(X.shape) < 0.05] = np.nan
            bank.register(k, X)
            for x in X:
                ams[k].register(x)
        for _ in range(20):
            cue = rng.integers(0, m, n).astype(float)
            cue[rng.random(n) < 0.1] = np.nan
            acc, w, mis = bank.recognize(cue)
            for k in range(K):
                r, wo = ams[k].recognize(cue)
                assert np.array_equal(bank.relation[k], ams[k].relation)
                assert mis[k] == ams[k].mismatches(cue)
                assert np.isclose(w[k], wo) and acc[k] == r
                assert np.isclose(bank.entropy[k], ams[k].entropy)
                assert np.isclose(bank.mean[k], ams[k].mean)


if __name__ == '__main__':
    test_bank_matches_dimex()
    print('OK: MemoryBank == dimex AssociativeMemory')
