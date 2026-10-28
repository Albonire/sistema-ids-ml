# Fase 1: Pipeline de datos (CICIDS2017 y UNSW-NB15)

Documento técnico de la primera fase de implementación (semanas 7 a 9 del cronograma). Describe qué hace el pipeline, por qué se tomaron cada una de las decisiones y qué cifras produce sobre los datos reales.

## 1. Alcance

Incluido: descarga reproducible y verificada de los dos datasets, limpieza, carga determinista, partición 70/15/15 estratificada, fábrica de escaladores, análisis exploratorio y pruebas unitarias. Entrenamiento, inferencia y evaluación están documentados en `docs/fase2_modelos.md`.

La fase se escribió primero para CICIDS2017 y se extendió a UNSW-NB15 (dataset principal del Entregable 1) en la fase 2.

## 2. Uso

```bash
pip install -r requirements-dev.txt
python -m src.download_data --dataset all
python -m src.preprocess --dataset all
pytest -q
```

```python
from src.data_loader import load_processed, make_splits
splits = make_splits(load_processed("unsw_nb15"))   # splits.train / .val / .test
```

## 3. Decisiones de diseño

| Decisión | Motivo |
|---|---|
| Espejo fijado a una revisión con SHA256 | El enlace oficial exige registro. La revisión fija y los hashes garantizan que todo el equipo trabaja con bytes idénticos. |
| Lectura en `latin-1` y normalización de etiquetas | Un byte cp1252 (guion largo) en las etiquetas de ataques web rompe la lectura UTF-8. Se reemplaza por un guion simple: `Web Attack - Brute Force`. |
| Eliminación de la columna `Fwd Header Length` duplicada | El CSV la trae dos veces. Se comprueba en código que son idénticas antes de descartarla. |
| Eliminación de filas con `Infinity` o NaN | Aparecen en `Flow Bytes/s` y `Flow Packets/s` (división por duración cero). Son el 0,1 por ciento del total. |
| Eliminación de duplicados (características más etiqueta binaria) | Los duplicados a ambos lados de la partición inflan las métricas (fuga de datos). Un mismo vector con dos familias de ataque distintas se trata como duplicado y se conserva una fila. |
| Eliminación de vectores contradictorios (normal y ataque a la vez) | Es ruido irreducible. Se descartan todas sus filas. Se juzga con la etiqueta binaria porque la tarea es binaria: una primera versión usaba la familia de ataque y descartaba por error 38,642 flujos de UNSW-NB15 (126 protocolos raros desaparecían por completo). |
| Eliminación de columnas constantes | No aportan información (ocho columnas, ver sección 4). |
| Valores negativos conservados | Se documentan pero no se alteran: `Init_Win_bytes_* = -1` es un centinela válido y el resto es marginal (menos de 3000 filas). |
| Sin escalado en el preprocesado | El escalador se ajusta solo con entrenamiento (`src/utils/scaling.py`) para evitar fuga de estadísticas del conjunto de prueba. |
| Partición 70/15/15 estratificada por tipo de ataque | Es el esquema del Entregable 1. Garantiza que familias muy raras (Heartbleed: 11 flujos) aparezcan en todos los conjuntos. `random_state=42`. La validación se usa para ajustar y elegir umbrales; la prueba solo al final. |
| Formato Parquet `float32` | El dataset limpio de CICIDS2017 ocupa unos 245 MB en disco y 734 MB en memoria. Las variables categóricas de UNSW-NB15 (`proto`, `service`, `state`) se conservan como texto. |

## 4. Resultados sobre los datos reales

| Paso | Filas |
|---|---|
| Filas crudas (8 archivos) | 2.830.743 |
| Con infinitos o NaN (eliminadas) | 2.867 |
| Duplicados exactos (eliminadas) | 307.078 |
| Etiquetas conflictivas (eliminadas) | 1.394 |
| Filas finales | 2.519.404 |

El total crudo coincide con la cifra publicada del dataset. Variables finales: 69 (77 únicas menos 8 constantes: `Bwd PSH Flags`, `Bwd URG Flags` y las seis variables `Avg Bytes/Packets/Bulk Rate` de ambos sentidos).

Distribución final: 2.094.360 flujos normales (83,1 por ciento) y 425.044 ataques (16,9 por ciento). Clases más pequeñas: Heartbleed 11, SQL Injection 21, Infiltration 36. La partición 70/15/15 deja 1.763.582 flujos de entrenamiento, 377.911 de validación y 377.911 de prueba, con las 15 clases presentes en los tres conjuntos.

El análisis de correlación (`notebooks/01_eda_cicids2017.ipynb`) muestra 38 pares con |r| > 0,95 y 22 variables candidatas a eliminarse por redundancia; varias parejas son idénticas (por ejemplo `Total Fwd Packets` y `Subflow Fwd Packets`). Esta reducción queda para la fase de selección de características, donde se evaluará con validación y no solo con correlación.

## 5. Implicaciones para la evaluación

- **Desbalance**: la Accuracy es engañosa; un clasificador que siempre diga "normal" obtendría 83 por ciento. Por eso el criterio del proyecto es Recall y FPR.
- **Limitaciones conocidas del dataset**: la literatura documenta errores de construcción de flujos, extracción de características y etiquetado en CICIDS2017, que afectan los resultados de los modelos. Este pipeline no los corrige (requeriría reprocesar los PCAP); deben mencionarse como amenaza a la validez en el informe final.
  - Engelen, G., Rimmer, V. y Joosen, W. (2021). "Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study". IEEE Security and Privacy Workshops (SPW), pp. 7-12. DOI 10.1109/SPW53761.2021.00009.
  - Lanvin, M., Gimenez, P.-F., Han, Y., Majorczyk, F., Mé, L. y Totel, E. (2023). "Errors in the CICIDS2017 dataset and the significant differences in detection performances it makes". CRiSIS 2022, Lecture Notes in Computer Science, Springer, pp. 18-33.
- **Variable `Destination Port`**: se conserva por ser parte del conjunto estándar, pero puede favorecer atajos (ciertos ataques usan puertos fijos). Se recomienda un experimento de ablación en la fase de modelos.
- **UNSW-NB15**: ver la sección 6.

## 6. UNSW-NB15

El mismo pipeline procesa UNSW-NB15 (`notebooks/02_eda_unsw_nb15.ipynb`). Se unen las particiones oficiales de entrenamiento (175.341 flujos) y de prueba (82.332) y se reparten de nuevo en 70/15/15. Se descarta la columna `id` (contador por archivo) y se verifica que `label` coincide con `attack_cat`.

El dato crudo tiene 257.673 flujos de los cuales 103.575 son duplicados y solo 828 son contradictorios, y quedan 153.270 (ver `data/processed/unsw_nb15_cleaning_report.json`). Es decir, el 40 % de las filas son redundantes, y si no se depuran antes de partir los datos inflan las métricas; la ablación `python -m src.leakage_ablation --dataset unsw_nb15` lo cuantifica en `docs/fase2_modelos.md`.
