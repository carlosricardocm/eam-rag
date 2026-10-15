# Obra completa (K = 3) frente a 8 fragmentos

89 preguntas sobre el corpus; `gpt-6-luna` como generador y juez. evid = la cita de referencia está en el prompt. Exactitud = correcto + 0.5·parcial.

| Qué recibe el LLM | Recuperador | obra@K | evid | Exactitud | Correcto | Incorrecto | No lo sé | Conocidas | Poco conocidas |
|---|---|---|---|---|---|---|---|---|---|
| 8 fragmentos (de 5 obras) | EAM m=16 | 0.73 (K=5) | 0.33 | **0.38** | 35% | 2% | 57% | 0.43 | 0.29 |
| 8 fragmentos (de 5 obras) | Coseno | 0.83 (K=5) | 0.43 | **0.48** | 45% | 3% | 46% | 0.48 | 0.47 |
| 3 obra(s) completa(s) | EAM m=16 | 0.70 (K=3) | 0.71 | **0.66** | 63% | 1% | 29% | 0.66 | 0.67 |
| 3 obra(s) completa(s) | Coseno | 0.78 (K=3) | 0.78 | **0.71** | 69% | 4% | 21% | 0.65 | 0.82 |
| Nada (LLM directo) | — | — | — | **0.40** | 36% | 4% | 51% | 0.62 | 0.03 |
