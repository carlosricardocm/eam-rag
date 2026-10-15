# Recuperación con EAM (m = 16, 8, 4) frente a similitud coseno

89 preguntas sobre el corpus. obra@K: la obra correcta está entre las K recuperadas; evid@C: el fragmento con la evidencia literal está entre los C que llegan al prompt. Exactitud = correcto + 0.5·parcial.


## 5 obras / 8 fragmentos

| Recuperador | obra@5 | evid@8 | Exactitud | Correcto | Parcial | Incorrecto | No lo sé | Conocidas | Poco conocidas |
|---|---|---|---|---|---|---|---|---|---|
| EAM m=16 | 0.73 | 0.33 | **0.38** | 35% | 6% | 2% | 57% | 0.43 | 0.29 |
| EAM m=8 | 0.72 | 0.31 | **0.36** | 34% | 4% | 3% | 58% | 0.40 | 0.29 |
| EAM m=4 | 0.75 | 0.31 | **0.37** | 35% | 4% | 6% | 55% | 0.39 | 0.33 |
| Coseno | 0.83 | 0.43 | **0.48** | 45% | 6% | 3% | 46% | 0.48 | 0.47 |
| LLM directo (sin recuperación) | — | — | **0.40** | 36% | 9% | 4% | 51% | 0.62 | 0.03 |

## 3 obras / 8 fragmentos

| Recuperador | obra@3 | evid@8 | Exactitud | Correcto | Parcial | Incorrecto | No lo sé | Conocidas | Poco conocidas |
|---|---|---|---|---|---|---|---|---|---|
| EAM m=16 | 0.71 | 0.35 | **0.39** | 37% | 3% | 3% | 56% | 0.42 | 0.33 |
| EAM m=8 | 0.71 | 0.34 | **0.35** | 33% | 6% | 4% | 57% | 0.38 | 0.32 |
| EAM m=4 | 0.70 | 0.31 | **0.34** | 30% | 8% | 3% | 58% | 0.35 | 0.33 |
| Coseno | 0.78 | 0.43 | **0.48** | 45% | 6% | 3% | 46% | 0.48 | 0.47 |
| LLM directo (sin recuperación) | — | — | **0.40** | 36% | 9% | 4% | 51% | 0.62 | 0.03 |
