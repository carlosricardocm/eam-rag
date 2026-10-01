# RAG con Memorias Asociativas Entrópicas (EAM)

Implementación del diagrama `../rag_modificado.png`: un RAG donde la *vector database*
se sustituye por memorias asociativas entrópicas (código base: `../dimex/associative.py`).

```
User query ──SONAR──► cue (1024 rasgos cuantizados a m niveles)
                          │
Knowledge Base ──SONAR──► EAM: una memoria por obra (693 memorias de 16×1024)
(datasets_csv)            │  1) cada memoria puntúa el cue → mejores obras
                          │  2) dentro de esas obras → mejores fragmentos
                          ▼
            AUGMENTATION: "Responde <pregunta> basándote en <documentos>;
                           si no está, di 'No lo sé'"  ──► OpenAI (GPT) ──► respuesta
```

## Instalación

Entorno conda `eamrag` (Python 3.11, PyTorch con CUDA):

```bash
conda create -n eamrag python=3.11
conda activate eamrag
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```

SONAR: el paquete oficial `sonar-space` depende de fairseq2, que no corre en Windows, así que
se usa el port a HuggingFace con los mismos pesos (`cointegrated/SONAR_200_text_encoder`,
idioma `spa_Latn`, mean-pooling).

Para generar respuestas hace falta una API key de OpenAI. Se configura en el archivo `eam_rag/.env`
(plantilla en `eam_rag/.env.example`), que `config.py` carga automáticamente:

```
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-5.5        # opcional
```

Una variable de entorno del sistema con el mismo nombre tiene prioridad sobre el `.env`.
El `.env` está en `.gitignore`: no lo subas a ningún repositorio.

## Uso

Primero, en cada terminal nueva, activa el entorno y entra a la carpeta del proyecto
(desde Anaconda Prompt; en PowerShell hace falta haber corrido una vez `conda init powershell`):

```bash
conda activate eamrag
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"   # True = usa la GPU
```

Después:

```bash
cd eam_rag
python build_index.py                  # corpus → fragmentos → SONAR → memorias (≈1-2 min con GPU)
python rag.py "¿Qué enfermedad sufre Dahlmann tras golpearse la frente?"
python rag.py --no-llm "..."           # sólo recuperación + prompt aumentado, sin llamar al LLM
python rag.py                          # modo interactivo
python rag.py --min-z 1.1 "..."        # la EAM rechaza consultas que no reconoce → "No lo sé."
python rag.py --criterion dimex "..."  # criterio original de dimex (entropy/weight)
python evaluate.py --grid              # evaluación EAM frente a similitud coseno
python evaluate.py --m 4 8 16          # compara tamaños de memoria (filas = niveles de cuantización)
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `associative.py` | `MemoryBank`: K memorias EAM apiladas en un tensor `R[K, m+1, n]`. Es un port vectorizado de `dimex/associative.py` (register, entropy, iota, kappa, mismatches, weight, recognize, recall) y agrega `log_likelihood`. |
| `corpus.py` | Lee los CSV, elimina los 26 links duplicados, corrige autores mal etiquetados y parte cada obra en fragmentos de unas 120 palabras (por oraciones, con traslape de 1). |
| `sonar_encoder.py` | Codificador SONAR. |
| `eam_store.py` | `Quantizer` (cuantiles por rasgo o min-max como en dimex) y `EAMStore` (construcción, recuperación en dos niveles, guardado y carga). |
| `config.py` | Carga `.env` y expone `OPENAI_API_KEY` y `OPENAI_MODEL` al resto del proyecto. |
| `generator.py` | Prompt de *augmentation* y llamada a OpenAI (`gpt-5.5` por defecto, streaming). |
| `rag.py` | CLI del pipeline completo. |
| `evaluate.py`, `questions.json` | Evaluación: 300 consultas sintéticas y 31 preguntas (21 sobre cuentos del corpus y 10 fuera del corpus). |
| `tests/test_fidelity.py` | Comprueba que `MemoryBank` da exactamente lo mismo que el `AssociativeMemory` original (correr con el entorno `eam`, numpy<1.24). |

## Cómo recupera la EAM

1. **Registro:** cada embedding de fragmento se cuantiza a `m=16` niveles por rasgo (cuantiles
   del corpus, es decir, niveles equiprobables) y se registra en la memoria de su obra:
   `R_k[v_j, j] += 1`.
2. **Nivel obra:** el cue se evalúa contra las 693 memorias a la vez.
   - `criterion='loglik'` (por defecto): `mean_j log(Σ_i R_k[i,j]·G(i,v_j) / N_k + ε)`, donde
     `G` es la misma gaussiana `sigma` que usa dimex al recordar. Es una versión graduada de
     *mismatches + weight*: un rasgo del cue que cae en una celda vacía aporta `log ε`.
   - `criterion='dimex'`: reconocimiento con `tolerance/iota/kappa` y orden por `entropy/weight`,
     igual que `AssociativeMemorySystem.recall`.
   - `min_z`: umbral de reconocimiento relativo. Si ninguna memoria queda `min_z` desviaciones
     estándar por encima de la media, no se recupera nada y la respuesta es "No lo sé.".
3. **Nivel fragmento:** dentro de las 5 mejores obras, cada fragmento se puntúa con el peso
   suavizado de una memoria que contiene sólo ese fragmento: `mean_j G(c_j, v_j)`. Todos compiten
   juntos y se pasan al LLM los 8 mejores en total (no 8 por obra).

Por defecto se recuperan 5 obras y 8 fragmentos (`TOP_WORKS` y `TOP_CHUNKS` en `eam_store.py`;
se cambian con `--top-works` y `--top-chunks` en `rag.py` y `evaluate.py`).

## Resultados (`python evaluate.py --grid`)

obra@5 = la obra correcta aparece entre las 5 recuperadas; frag@8 = el fragmento exacto está
entre los 8 recuperados.

| Configuración | Preguntas reales obra@5 | Oración literal obra@1 | Oración literal frag@8 | Rechazo fuera del corpus |
|---|---|---|---|---|
| Vector DB (coseno SONAR) | 0.62 | **0.72** | **0.84** | — |
| EAM, criterio dimex `entropy/weight` | 0.00 | 0.00 | 0.00 | 0.00 |
| **EAM loglik, σ=0.3 (por defecto)** | **0.67** | 0.36 | 0.47 | 0.00 |
| EAM loglik, σ=0.3, `min_z=1.1` | 0.57 (acepta 81%) | 0.30 | 0.35 | **0.90** |

Antes se recuperaban 3 obras y 5 fragmentos. Comparación (σ = 0.3):

| Recuperación | Método | Preguntas obra@K | Oración literal obra@K | Oración literal frag@K |
|---|---|---|---|---|
| 3 obras / 5 fragmentos | EAM | 0.67 | 0.43 | 0.40 |
| 3 obras / 5 fragmentos | Coseno | 0.48 | 0.81 | 0.81 |
| **5 obras / 8 fragmentos** | EAM | 0.67 | 0.49 | 0.47 |
| **5 obras / 8 fragmentos** | Coseno | 0.62 | 0.85 | 0.84 |

Lectura:
- **El criterio original `entropy/weight` no sirve aquí:** una obra con un solo fragmento tiene
  entropía 0, así que su penalización es 0 y gana siempre. Ese criterio está pensado para
  memorias de clase con muchos ejemplos, como los fonemas de DIMEx.
- **Con preguntas reales la EAM supera al coseno (0.67 frente a 0.62 con 5 obras):** la memoria
  abstrae la obra completa, y una pregunta ("¿qué enfermedad sufre Dahlmann…?") se parece más a
  esa abstracción que a un fragmento concreto. Con 3 obras la ventaja era mayor (0.67 frente a
  0.48): la EAM ya encontraba entre sus 3 primeras todas las obras que encuentra entre 5, y el
  coseno necesita más candidatos para alcanzarla. Con 5 obras la diferencia es de una pregunta.
- **Más fragmentos, más contexto:** con 8 fragmentos el fragmento exacto aparece más a menudo
  (EAM 0.40 → 0.47), a cambio de un prompt más largo para el LLM.
- **Buscando una oración literal, el coseno gana:** esa abstracción pierde el detalle del
  fragmento exacto. `sigma` entre 0.2 y 0.4 es lo mejor; el tamaño de la memoria casi no
  cambia nada (ver abajo).
- **La EAM puede rechazar consultas** con `min_z`, cosa que una vector DB no hace por sí sola.
  El precio es rechazar también ~19% de preguntas válidas, por eso viene desactivado.
- Las muestras son pequeñas (21 preguntas del corpus y 10 fuera), así que estas cifras son
  indicativas.

### Tamaño de la memoria (`python evaluate.py --m 4 8 16`)

Cada memoria es una tabla de **m filas × n columnas**: n = 1024 rasgos de SONAR (el dominio) y
m = niveles de cuantización (el rango). Las filas *son* los niveles, así que cambiar el número
de filas es cambiar `m`. Los embeddings no cambian: sólo se vuelve a cuantizar y a registrar.

Con σ = 0.3 y sin umbral:

| Memoria (m × n) | Entropía media (máx.) | Tamaño de R | Sint. obra@1 | Sint. obra@5 | Sint. frag@8 | Preguntas obra@5 |
|---|---|---|---|---|---|---|
| 4 × 1024 | 1.23 bits (2) | 6.8 MB | 0.360 | 0.510 | 0.467 | 0.67 |
| 8 × 1024 | 1.74 bits (3) | 12.2 MB | 0.360 | 0.500 | 0.470 | 0.67 |
| **16 × 1024 (por defecto)** | 2.13 bits (4) | 23.0 MB | 0.357 | 0.493 | 0.467 | 0.67 |
| Coseno (referencia) | — | — | 0.723 | 0.850 | 0.840 | 0.62 |

Con umbral `min_z = 1.1`:

| m | Preguntas válidas aceptadas | Preguntas obra@5 | Rechazo fuera del corpus |
|---|---|---|---|
| 4 | 0.90 | 0.57 | 0.70 |
| 8 | 0.81 | 0.57 | 0.90 |
| 16 | 0.81 | 0.57 | 0.90 |

En los tres tamaños, el mejor σ está entre 0.2 y 0.3.

Lectura:
- **Los tres tamaños dan prácticamente lo mismo.** Las diferencias están dentro del ruido: con
  300 consultas el error típico es de ±0.03, y en las preguntas una sola pregunta vale 0.05.
- **Por qué:** con cuantiles cada nivel tiene la misma cantidad de datos, y σ se mide como
  fracción de m. Con σ = 0.3, la gaussiana cubre la misma porción de cada rasgo con 4, 8 o 16
  niveles. Reducir m sólo quita detalle fino que la gaussiana ya estaba borrando.
- **m = 4 ocupa la cuarta parte sin perder precisión,** pero con el umbral rechaza menos
  preguntas ajenas al corpus (0.70 frente a 0.90). m = 8 conserva el rechazo con la mitad del
  espacio.
- **La entropía queda muy por debajo del máximo** en los tres casos. Muchas obras tienen pocos
  fragmentos y no llenan las columnas, así que más niveles no aportan información.
- **El tamaño no explica la brecha con el coseno** en frases literales (0.36 frente a 0.72).
  Esa brecha viene de abstraer la obra completa en una sola memoria.
