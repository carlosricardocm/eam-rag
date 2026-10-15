# Obra completa (K = 1) frente a 8 fragmentos

89 preguntas sobre el corpus; `gpt-6-luna` como generador y juez. evid = la cita de referencia está en el prompt. Exactitud = correcto + 0.5·parcial.

| Qué recibe el LLM | Recuperador | obra@K | evid | Exactitud | Correcto | Incorrecto | No lo sé | Conocidas | Poco conocidas |
|---|---|---|---|---|---|---|---|---|---|
| 8 fragmentos (de 5 obras) | EAM m=16 | 0.73 (K=5) | 0.33 | **0.38** | 35% | 2% | 57% | 0.43 | 0.29 |
| 8 fragmentos (de 5 obras) | Coseno | 0.83 (K=5) | 0.43 | **0.48** | 45% | 3% | 46% | 0.48 | 0.47 |
| 1 obra(s) completa(s) | EAM m=16 | 0.60 (K=1) | 0.61 | **0.56** | 54% | 2% | 39% | 0.56 | 0.56 |
| 1 obra(s) completa(s) | Coseno | 0.70 (K=1) | 0.70 | **0.65** | 62% | 2% | 30% | 0.56 | 0.79 |
| Nada (LLM directo) | — | — | — | **0.40** | 36% | 4% | 51% | 0.62 | 0.03 |
