# RAG con Memorias Asociativas Entrópicas (EAM)

Implementación del diagrama `../rag_modificado.png`: un RAG donde la *vector database*
se sustituye por memorias asociativas entrópicas (código base: `../dimex/associative.py`).
La memoria decide **en qué obras buscar** (y, con `--min-z`, si se responde); al LLM se le pasa el
texto completo de esas obras o, dentro de ellas, los fragmentos que elige BM25.

```
User query ──SONAR──► cue (1024 rasgos cuantizados a m niveles)
                          │
Knowledge Base ──SONAR──► EAM: una memoria por obra (693 memorias de 16×1024)
(Borges Corpus)           │  1) cada memoria puntúa el cue (log-verosimilitud) → mejores obras
                          │  2) texto para el LLM: obras completas (por defecto) o fragmentos BM25
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
python rag.py "¿Qué enfermedad sufre Dahlmann tras golpearse la frente?"   # 3 obras completas
python rag.py --modo bm25 "..."        # 3 obras, 16 fragmentos elegidos con BM25
python rag.py --modo eam "..."         # 5 obras, 8 fragmentos con la puntuación de la memoria
python rag.py --no-llm "..."           # sólo recuperación + prompt aumentado, sin llamar al LLM
python rag.py                          # modo interactivo
python rag.py --min-z 1.1 "..."        # la EAM rechaza consultas que no reconoce → "No lo sé."
```

`--modo` decide qué texto recibe el LLM de las obras que elige la EAM:

| Modo | Obras | Qué recibe el LLM | Exactitud* | Texto típico |
|---|---|---|---|---|
| `obras` (por defecto) | 3 | el texto completo de las obras | **0.66** | ~10 000 palabras |
| `bm25` | 3 | los 16 fragmentos con mejor puntaje BM25 | 0.61 | ~1 700 palabras |
| `eam` | 5 | los 8 fragmentos con mejor puntaje de la memoria | 0.38 | ~1 000 palabras |

\* Exactitud de las respuestas con las 89 preguntas sobre el corpus (ver Resultados).
`--top-works` y `--top-chunks` cambian el número de obras y de fragmentos.

Evaluación:

```bash
python evaluate.py --grid              # criterios de selección, σ y rechazo (Tabla 1 de abajo)
python compare_whole_works.py --obras 3   # obras completas frente a fragmentos (con juez LLM)
python compare_bm25.py                 # fragmentos BM25 dentro de las obras elegidas (con juez LLM)
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `associative.py` | `MemoryBank`: K memorias EAM apiladas en un tensor `R[K, m+1, n]`. Es un port vectorizado de `dimex/associative.py` (register, entropy, iota, kappa, mismatches, weight, recognize, recall) y agrega `log_likelihood`. |
| `corpus.py` | Lee los CSV, elimina los 26 links duplicados, corrige autores mal etiquetados y parte cada obra en fragmentos de unas 120 palabras (por oraciones, con traslape de 1). |
| `sonar_encoder.py` | Codificador SONAR. |
| `eam_store.py` | `Quantizer` (cuantiles por rasgo o min-max como en dimex) y `EAMStore` (construcción, elección de obras, recuperación de obras completas o de fragmentos, guardado y carga). |
| `bm25.py` | Índice BM25 (palabras clave) de los fragmentos. |
| `config.py` | Carga `.env` y expone `OPENAI_API_KEY` y `OPENAI_MODEL` al resto del proyecto. |
| `generator.py` | Prompt de *augmentation* y llamada a OpenAI (streaming). |
| `rag.py` | CLI del pipeline completo. |
| `evaluate.py`, `questions.json` | Recuperación: 300 consultas sintéticas y 100 preguntas (89 sobre el corpus, con respuesta de referencia y cita literal, y 11 fuera del corpus). |
| `compare_whole_works.py`, `compare_bm25.py` | Exactitud de las respuestas con un LLM juez; resultados en `results/`. Las llamadas se guardan en caché y los prompts repetidos se generan una sola vez. |
| `tests/test_fidelity.py` | Comprueba que `MemoryBank` da exactamente lo mismo que el `AssociativeMemory` original (correr con el entorno `eam`, numpy<1.24). |

## Cómo recupera la EAM

1. **Registro:** cada embedding de fragmento se cuantiza a `m=16` niveles por rasgo (cuantiles
   del corpus, es decir, niveles equiprobables) y se registra en la memoria de su obra:
   `R_k[v_j, j] += 1`.
2. **Nivel obra:** el cue se evalúa contra las 693 memorias a la vez.
   - `criterion='loglik'` (por defecto): `mean_j log(Σ_i R_k[i,j]·G(i,v_j) / N_k + ε)`, donde
     `G` es la misma gaussiana `sigma` que usa dimex al recordar. Es una versión graduada de
     *mismatches + weight*: un rasgo del cue que cae en una celda vacía aporta `log ε`, y no
     depende del número de fragmentos de la obra.
   - `criterion='dimex'`: reconocimiento con `tolerance/iota/kappa` y orden por `entropy/weight`,
     igual que `AssociativeMemorySystem.recall`. No sirve aquí: una obra con un solo fragmento
     tiene entropía 0 y gana siempre.
   - `min_z`: umbral de reconocimiento relativo. Si ninguna memoria queda `min_z` desviaciones
     estándar por encima de la media, no se recupera nada y la respuesta es "No lo sé.".
   - Se saltan las obras cuyo texto ya está contenido en otra elegida (p. ej. *Los hrönir de Tlön*,
     un fragmento de *Tlön, Uqbar, Orbis Tertius*).
3. **Texto para el LLM** (`--modo`):
   - `obras`: el texto completo de las obras elegidas.
   - `bm25`: BM25 puntúa los fragmentos de esas obras por las palabras de la pregunta (rareza en el
     corpus, frecuencia y longitud; k1 = 1.2, b = 0.75) y se pasan los mejores en total.
   - `eam`: cada fragmento se puntúa con el peso suavizado de una memoria que lo contiene sólo a él,
     `mean_j G(c_j, v_j)`. Sobre los códigos cuantizados no distingue bien el pasaje con la respuesta.

## Resultados

Conjuntos: 300 consultas sintéticas (una oración interior de un fragmento) y 100 preguntas:
89 sobre el corpus (56 de obras conocidas y 33 poco conocidas) y 11 fuera del corpus.

### 1. Criterios de selección y σ (`python evaluate.py --grid`)

5 obras recuperadas. obra@5 = la obra correcta está entre las 5; frag@8 = el fragmento exacto está
entre los 8 recuperados.

| Configuración | Preguntas obra@5 | Oración literal obra@1 | Oración literal frag@8 |
|---|---|---|---|
| Vector DB (coseno SONAR) | **0.83** | **0.72** | **0.84** |
| EAM, criterio dimex `entropy/weight` | 0.00 | 0.00 | 0.00 |
| EAM loglik, σ=0.1 | 0.42 | 0.30 | 0.40 |
| EAM loglik, σ=0.2 | 0.64 | 0.35 | 0.47 |
| **EAM loglik, σ=0.3 (por defecto)** | 0.73 | 0.36 | 0.47 |
| EAM loglik, σ=0.4 | 0.78 | 0.31 | 0.44 |

- El criterio original `entropy/weight` falla por construcción: las obras de un solo fragmento ganan
  cualquier consulta.
- Con la log-verosimilitud la obra correcta queda entre las 5 primeras en el 73 % de las preguntas;
  el coseno lo hace en el 83 % y es mucho mejor para localizar una oración literal.
- σ = 0.3 es el mejor en el conjunto sintético; en las preguntas el acierto sigue subiendo hasta 0.4.

### 2. Rechazo con `min_z`

| `min_z` | Preguntas válidas aceptadas | Preguntas obra@5 | Ajenas rechazadas |
|---|---|---|---|
| sin umbral | 1.00 | 0.73 | 0 de 11 |
| 1.05 | 0.96 | 0.69 | 5 de 11 |
| **1.10** | 0.74 | 0.60 | **10 de 11** |
| 1.15 | 0.45 | 0.42 | 10 de 11 |

La única pregunta ajena aceptada con 1.10 es "¿Qué es un agujero negro?"; la de *Cien años de
soledad* (literaria, pero fuera del corpus) se rechaza. Viene desactivado por defecto.

### 3. Obras completas y fragmentos BM25 (`compare_whole_works.py`, `compare_bm25.py`)

89 preguntas sobre el corpus; un LLM juez compara cada respuesta con la de referencia
(exactitud = correcto + 0.5·parcial). `gpt-6-luna` como generador y juez.

| Obras | Qué recibe el LLM | Evidencia en el prompt | Palabras | Exactitud | Incorrectas | Conocidas | Poco conocidas |
|---|---|---|---|---|---|---|---|
| EAM, 5 | 8 fragm. (puntuación de la memoria) | 0.33 | ~1 000 | 0.38 | 2% | 0.43 | 0.29 |
| EAM, 1 | obra completa | 0.61 | 2 120 | 0.56 | 2% | 0.56 | 0.56 |
| EAM, 1 | 16 fragm. BM25 | 0.58 | 1 690 | 0.56 | 3% | 0.55 | 0.56 |
| **EAM, 3** | **obras completas** | 0.71 | 10 140 | **0.66** | **1%** | **0.66** | 0.67 |
| EAM, 3 | 16 fragm. BM25 | 0.64 | 1 700 | 0.61 | 3% | 0.58 | 0.65 |
| EAM, 3 | 8 fragm. BM25 | 0.55 | 860 | 0.53 | 4% | 0.51 | 0.58 |
| Coseno, 3 | obras completas | 0.78 | 6 150 | 0.71 | 4% | 0.65 | 0.82 |
| Coseno, 3 | 16 fragm. BM25 | 0.73 | 1 690 | 0.69 | 4% | 0.60 | 0.83 |
| Coseno (vector DB) | 8 fragm. (coseno) | 0.43 | ~1 000 | 0.48 | 3% | 0.48 | 0.47 |
| — | LLM sin recuperación | — | — | 0.40 | 4% | 0.62 | 0.03 |

- La memoria encuentra la obra, pero su propia puntuación de fragmentos elige mal el pasaje (0.38).
- Con las 3 obras completas que elige la EAM la exactitud llega a 0.66 (p = 0.01 frente a la vector DB
  estándar); con 16 fragmentos BM25, a 0.61 con unas 6 veces menos texto.
- Eligiendo las obras por coseno se llega a 0.71 / 0.69, sin diferencia significativa con la EAM
  (p = 0.44 / 0.19); la diferencia está en las obras poco conocidas.
- Cuando la evidencia llega al prompt, el modelo acierta el 88–92 % de las veces.

Detalle por pregunta en `results/`.

## Cómo reproducir los experimentos

Todos los scripts se corren desde `eam_rag/` con el entorno `eamrag` activo y el índice ya construido
(`python build_index.py`, que espera el corpus en `../datasets_csv`). Las preguntas están en
`questions.json`: cada una tiene `q`, `title` y `author` (nulos si es ajena al corpus), `answer`
(respuesta de referencia) y, si es del corpus, `evidence` (cita literal) y `fame`
(`conocida` / `poco_conocida`).

**1. Recuperación, criterios y rechazo (sin API).**

```bash
python evaluate.py --grid       # Tabla de criterios, σ y min_z (secciones 1 y 2 de Resultados)
python evaluate.py -v           # detalle por pregunta: obras de la EAM y del coseno
```

Codifica las consultas con SONAR la primera vez y guarda un caché en `store/eval_queries_300.npz`.

**2. Respuestas con juez (usan la API de OpenAI).** Generador y juez son el modelo de
`OPENAI_MODEL` en `.env` (los resultados de arriba son con `gpt-6-luna`; con otro modelo cambian).
Hay que correrlos en este orden, porque los dos últimos toman de `results/retrievers.json` las filas
de referencia (EAM y coseno con 8 fragmentos, y el LLM sin recuperación):

```bash
python compare_retrievers.py            # referencias: EAM (m = 16, 8, 4) y coseno con 8 fragmentos + LLM directo
python compare_whole_works.py --obras 1 # obras completas, K = 1
python compare_whole_works.py --obras 3 # obras completas, K = 3
python compare_bm25.py                  # fragmentos BM25: EAM y coseno, K = 1 y 3, 8 y 16 fragmentos
```

| Script | Llamadas a la API (aprox.) | Resultados |
|---|---|---|
| `compare_retrievers.py` | ~900 | `results/retrievers.json`, `.md` |
| `compare_whole_works.py --obras 1` | ~190 | `results/whole_works_k1.json`, `.md` |
| `compare_whole_works.py --obras 3` | ~200 (prompts de ~10 000 palabras) | `results/whole_works_k3.json`, `.md` |
| `compare_bm25.py` | ~600 | `results/bm25.json`, `.md` |

Para gastar menos:

- Cada script acepta `--no-llm`, que calcula sólo la recuperación (obra@K y evidencia en el prompt)
  sin llamar a la API.
- Las llamadas se guardan en `results/compare_cache.jsonl`: si un script se interrumpe (por ejemplo,
  por falta de créditos), al volver a correrlo sólo hace las llamadas que faltan. El caché no se sube
  al repositorio, así que en una copia nueva todas las llamadas se hacen otra vez.
- Los prompts idénticos entre configuraciones se generan una sola vez, y las respuestas
  "No lo sé." no pasan por el juez.

**3. Figuras y documentos.** `make_pdf.py` genera `../RAG_EAM_documentacion.pdf` con las figuras PNG de
`results/` (`fig_obra_completa.png`, `fig_bm25.png`, ...). Las figuras se generan desde los `.json` de
`results/` con el script de figuras del artículo (`../articulo/figuras/make_figs.py`, en `es` y `en`).
