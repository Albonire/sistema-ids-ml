# Parte B: El código importante

Esta parte recorre, módulo por módulo, el código que hace funcionar el proyecto. Los fragmentos de código son **copias literales** del repositorio (se extraen automáticamente al construir el PDF), así que lo que lees aquí es exactamente lo que se ejecuta. Después de cada fragmento se explica qué hace, por qué está escrito así y qué pasaría si fuera distinto.

::: nota
Cómo usar esta parte: léela con el repositorio abierto. Para la sustentación no hace falta memorizar el código, sino poder explicar (1) qué problema resuelve cada módulo, (2) qué decisión de diseño evita un error de evaluación y (3) qué pasaría si esa decisión se cambiara. Cada módulo termina con una "pregunta de defensa" y su respuesta modelo.
:::

## B.1 Mapa del repositorio y flujo de datos

El prototipo es una tubería (pipeline) de seis etapas, cada una implementada por uno o dos módulos de `src/`. Los datos fluyen de izquierda a derecha y cada etapa escribe sus resultados en disco, de modo que se puede repetir una etapa sin repetir las anteriores.

::: {.figura-mediana}
![Arquitectura del prototipo: de los archivos crudos a la decisión](figuras/arquitectura.png)
:::

| Carpeta o archivo | Qué contiene | Se versiona en Git |
|---|---|---|
| `src/` | Código del prototipo (un módulo por responsabilidad) | Sí |
| `tests/` | Pruebas automáticas con datos sintéticos | Sí |
| `app/demo_app.py` | Demo visual en Streamlit | Sí |
| `data/raw/<dataset>/` | CSV originales descargados | No (muy grandes) |
| `data/processed/` | Parquet limpio y reporte de limpieza en JSON | No |
| `models/<dataset>/` | Mejor modelo (`best_model.joblib`) y puntajes (`scores.npz`) | No |
| `reports/<dataset>/` | Métricas, figuras, `resultados.md`, experimentos | Sí |
| `docs/` | Documentación técnica, demo y paquete de entrega | Sí |

El orden de ejecución completo, con los comandos exactos, es:

```bash
python -m src.download_data --dataset all    # 1. descarga verificada
python -m src.preprocess --dataset all       # 2. limpieza
python -m src.train --dataset unsw_nb15      # 3 a 5. partición, entrenamiento, umbrales
python -m src.evaluate --dataset unsw_nb15   # 6. figuras y reporte
python -m src.predict --dataset unsw_nb15 --input flujos.csv
```

::: importante
Principio rector de todo el código: **el conjunto de prueba nunca participa en una decisión**. Ni la limpieza que aprende de los datos, ni los hiperparámetros, ni los umbrales, ni la elección del modelo ganador lo ven. Casi todas las decisiones de diseño que se explican abajo existen para proteger este principio.
:::

::: pregunta
**Pregunta de defensa.** ¿Por qué cada etapa guarda su salida en disco en lugar de pasarla en memoria?

**Respuesta modelo.** Porque entrenar CICIDS2017 tarda entre 15 y 25 minutos (medido en este proyecto) y limpiarlo varios minutos. Si cada etapa escribe su resultado (Parquet, `scores.npz`, `metrics.csv`), se puede cambiar un criterio de decisión, regenerar figuras o repetir un experimento sin reentrenar. Es lo que hace `python -m src.train --rescore`, que recalcula umbrales y métricas desde los puntajes guardados.
:::

## B.2 `config.py`: rutas, constantes y fuentes de datos

Este módulo es la única fuente de verdad de rutas, semillas y orígenes de datos. Ningún otro archivo escribe una ruta a mano ni repite una constante.

{{>codigo src/config.py DatasetSource}}

La clase `DatasetSource` es un `dataclass` **inmutable** (`frozen=True`): describe un dataset (clave, nombre, URL base, huellas SHA256 y columnas categóricas) y calcula, con propiedades, dónde viven sus archivos derivados. Así, agregar un tercer dataset exige solo crear otra instancia, sin tocar el resto del código.

Constantes que conviene saber de memoria:

| Constante | Valor | Para qué sirve |
|---|---|---|
| `RANDOM_STATE` | 42 | Semilla de particiones y modelos, para reproducir resultados |
| `VAL_SIZE`, `TEST_SIZE` | 0.15 y 0.15 | Partición 70/15/15 |
| `RECALL_TARGET` | 0.95 | Meta de Recall del criterio de `AGENT.md` |
| `FPR_TARGET` | 0.02 | Presupuesto de falsas alarmas |
| `BENIGN_LABEL` | `"BENIGN"` | Nombre común del tráfico normal en ambos datasets |

### Revisiones fijadas y huellas SHA256

El enlace oficial de CICIDS2017 (Universidad de New Brunswick) pide un formulario de registro y no se puede automatizar. Por eso el código descarga los mismos archivos desde un espejo en Hugging Face, **fijado a una revisión concreta** (`CICIDS2017_REVISION`, `UNSW_NB15_REVISION`), y verifica cada archivo contra su huella SHA256 en `files_sha256`.

::: ejemplo
Un espejo sin revisión fijada podría cambiar un archivo mañana y alguien reproduciría el proyecto con datos distintos sin saberlo. La revisión fija más el SHA256 garantiza que cualquier computador obtiene **bytes idénticos**, o falla de forma ruidosa.
:::

::: advertencia
En el espejo de UNSW-NB15 los nombres están intercambiados: `test.csv` contiene la partición oficial de entrenamiento (175341 flujos) y `train.csv` la de prueba (82332). El proyecto une ambas y las reparte de nuevo, por lo que el intercambio no afecta; el módulo `experiments.py` asigna los roles **por tamaño**, no por nombre.
:::

{{>codigo src/config.py get_dataset}}

`get_dataset` convierte una clave en su `DatasetSource` y, si la clave no existe, lanza un `ValueError` que lista las opciones válidas, en lugar de un `KeyError` críptico.

::: pregunta
**Pregunta de defensa.** ¿Por qué `DatasetSource` es inmutable?

**Respuesta modelo.** Porque se comparte por todo el programa (descarga, limpieza, entrenamiento, demo). Si alguien pudiera modificar una ruta o una huella en tiempo de ejecución, un módulo trabajaría con una configuración distinta de otro. Inmutable significa que lo que se declara una vez no cambia, y los errores de configuración aparecen al instante.
:::

## B.3 `download_data.py` y `utils/files.py`: descarga verificada

Objetivo: bajar los archivos de cada dataset sin intervención y **no confiar** en lo descargado hasta comprobar su huella.

{{>codigo src/utils/files.py sha256_file}}

`sha256_file` calcula la huella leyendo el archivo en bloques de 1 MB (`_CHUNK_SIZE`). El operador `:=` (morsa) lee un bloque y lo asigna en la misma condición del `while`; el bucle termina cuando `read` devuelve bytes vacíos. Leer por bloques evita cargar en memoria un archivo de cientos de megabytes.

{{>codigo src/download_data.py download_file}}

Líneas clave de `download_file`:

1. Escribe primero en `archivo.csv.part`, no en el destino final. Si la descarga se corta, el archivo final nunca queda a medias.
2. Calcula el SHA256 del archivo parcial. Si no coincide, lo **borra** (`unlink`) y lanza `ValueError`.
3. Solo si la huella coincide hace `partial.replace(destination)`, una operación atómica: el archivo final aparece completo o no aparece.

{{>codigo src/download_data.py download_all}}

`download_all` es **idempotente**: si el archivo ya existe y su huella es correcta, lo salta (`OK (cached)`). Con `--force` se vuelve a bajar todo.

```bash
python -m src.download_data --dataset all          # ambos datasets
python -m src.download_data --dataset unsw_nb15    # solo uno
python -m src.download_data --force                # repetir la descarga
```

::: pregunta
**Pregunta de defensa.** ¿Qué pasaría si se escribiera directo al archivo final y la conexión se cae a la mitad?

**Respuesta modelo.** Quedaría un CSV truncado con el nombre correcto. Una segunda ejecución vería que el archivo existe y, sin verificación de huella, lo usaría; el preprocesado leería menos filas y todos los resultados cambiarían sin aviso. El archivo `.part` más el SHA256 más el reemplazo atómico lo impiden.
:::

## B.4 `preprocess.py`: limpieza sin fuga de datos

Es el módulo donde más decisiones de diseño protegen la validez de los resultados. Convierte los CSV crudos en un Parquet limpio con dos objetivos: `label` (0 normal, 1 ataque) y `attack_type` (la familia).

### Lectura de los archivos crudos

{{>codigo src/preprocess.py load_raw}}

CICIDS2017 no es UTF-8 válido: una etiqueta de ataques web trae un guion largo en codificación cp1252. Se lee como `latin-1`, que acepta cualquier byte, y las etiquetas se normalizan después. `skipinitialspace=True` y el `strip()` de las columnas quitan los espacios que el archivo original trae antes de varios nombres (por ejemplo `" Destination Port"`).

{{>codigo src/preprocess.py normalize_unsw}}

`normalize_unsw` adapta UNSW-NB15 al formato común. Tres decisiones: descarta `id` (es un contador por archivo, no una característica); **verifica** que la columna binaria `label` concuerde con `attack_cat` antes de descartarla (si no concordaran, lanza un error en vez de elegir una en silencio); y renombra `Normal` a `BENIGN` para que ambos datasets hablen el mismo idioma.

{{>codigo src/preprocess.py normalize_labels}}

### La función `clean`

{{>codigo src/preprocess.py clean}}

El **orden de los pasos importa**. Siguiendo el código:

1. **Columna duplicada.** CICIDS2017 trae dos veces `Fwd Header Length`; pandas renombra la segunda a `Fwd Header Length.1`. El código comprueba con `equals` que son idénticas **antes** de descartarla y, si no lo fueran, se niega a hacerlo. Una suposición verificada en lugar de asumida.
2. **Etiquetas.** `normalize_labels` limpia espacios y reemplaza guiones no ASCII por un guion simple.
3. **Tipos.** Las columnas numéricas se fuerzan a número (`errors="coerce"` convierte texto raro en NaN) y las categóricas a texto sin espacios.
4. **Infinitos y NaN.** Los infinitos se convierten en NaN y se eliminan todas las filas con algún NaN. Se **cuentan** antes de eliminar para el reporte.
5. **Conversión a `float32` antes de deduplicar.** Dos filas que difieren solo por debajo de la precisión de `float32` son el mismo vector para el modelo. Si se deduplicara en `float64` y luego se convirtiera, esas filas parecerían distintas, sobrevivirían ambas y una caería en entrenamiento y otra en prueba: **fuga**. Esto se descubrió con la ablación de duplicados: una fracción pequeña de la prueba de CICIDS2017 repetía un vector de entrenamiento hasta que se movió la conversión.
6. **Duplicados por (características, etiqueta binaria).** La tarea es binaria, así que se juzga por la etiqueta binaria: el mismo vector marcado con dos familias de ataque distintas es un duplicado (se conserva la primera fila).
7. **Contradictorios.** Un mismo vector con etiqueta normal **y** de ataque es ruido irreducible; se descartan todas sus filas con `_drop_conflicting`.
8. **Constantes.** Se eliminan las columnas con un solo valor (no aportan información).
9. **Objetivos.** Se construyen `attack_type` y `label`, y se descartan las columnas auxiliares.

::: advertencia
Un error de diseño que se corrigió: la primera versión juzgaba los conflictos con la **familia** de ataque. Un mismo vector etiquetado `DoS` y `Exploits` (ambos ataques) se descartaba como "contradictorio" y desaparecían por completo muchos protocolos raros de UNSW-NB15. Como la tarea es binaria, los conflictos deben juzgarse con la etiqueta binaria. Tiene una prueba automática (`test_clean_treats_same_vector_with_two_attack_families_as_duplicate_not_conflict`).
:::

{{>codigo src/preprocess.py _drop_conflicting}}

`_drop_conflicting` calcula un hash de 64 bits por fila (`hash_pandas_object`) en lugar de comparar decenas de columnas, agrupa por ese hash y cuenta cuántas etiquetas binarias distintas hay (`nunique`). Las filas de grupos con más de una etiqueta se descartan. La probabilidad de colisión de hash es despreciable para estos tamaños.

### El reporte de limpieza

`clean` devuelve también un `CleaningReport` (un `dataclass`) con filas por paso, columnas descartadas, valores negativos por columna y conteos por clase. `run` lo guarda como JSON; las tablas y figuras del informe se generan **desde ese JSON**, no a mano. Los números principales son:

| Dataset | Flujos crudos | Duplicados | Contradictorios | Flujos limpios |
|---|---|---|---|---|
| UNSW-NB15 | {{unsw.clean.rows_raw}} | {{unsw.clean.rows_removed_duplicates}} | {{unsw.clean.rows_removed_conflicting}} | {{unsw.clean.rows_final}} |
| CICIDS2017 | {{cic.clean.rows_raw}} | {{cic.clean.rows_removed_duplicates}} | {{cic.clean.rows_removed_conflicting}} | {{cic.clean.rows_final}} |

```bash
python -m src.preprocess --dataset all        # entre 3 y 4 minutos
```

::: pregunta
**Pregunta de defensa.** ¿Por qué se eliminan duplicados antes de partir los datos y no después?

**Respuesta modelo.** Porque un duplicado puede caer una copia en entrenamiento y otra en prueba. El modelo "acierta" la copia de prueba porque ya la memorizó, y eso infla las métricas. En UNSW-NB15, con un protocolo ingenuo (sin quitar duplicados), el {{unsw.l.naive.leaked_test_share_pct}} de la prueba son vectores ya vistos en entrenamiento. Limpiar primero y partir después garantiza que no haya vectores repetidos entre particiones.
:::

## B.5 `data_loader.py`: partición reproducible

{{>codigo src/data_loader.py make_splits}}

La partición se hace en **dos pasos** con `train_test_split` de scikit-learn:

1. Primero se separa el 15 % de **prueba** (`X_test`), que queda guardado y no se toca hasta el final.
2. Del 85 % restante se separa la **validación**. Como ya se quitó el 15 %, la validación debe ser `0.15 / 0.85` del resto (`relative_val`), que equivale al 15 % del total. Por eso existe esa división en el código.

El argumento `stratify=attack` mantiene la proporción de **cada familia de ataque** (no solo normal frente a ataque) en las tres particiones. Así familias raras, como las que tienen decenas de flujos, aparecen en todas. `random_state` fija el reparto: la misma semilla produce siempre los mismos conjuntos.

{{>codigo src/data_loader.py stratified_subsample}}

`stratified_subsample` extrae una muestra proporcional (se usa para la búsqueda de hiperparámetros con 60000 flujos). Si pides más filas de las que hay (`n_samples >= len(X)`), devuelve todo en vez de fallar.

`Partition` y `DataSplits` son contenedores inmutables: agrupan `X`, `y` y `attack` de cada partición. Evitan pasar seis variables sueltas entre funciones y reducen el riesgo de mezclar la de validación con la de prueba.

::: pregunta
**Pregunta de defensa.** ¿Por qué estratificar por familia de ataque y no solo por la etiqueta binaria?

**Respuesta modelo.** Porque el informe analiza la detección **por familia**. Si una familia con pocos flujos (como Heartbleed, con {{cic.fam.heartbleed}} flujos en CICIDS2017) cayera entera en entrenamiento, no habría forma de evaluarla; si cayera entera en prueba, el modelo nunca la vería. Estratificar por familia reparte cada una en las tres particiones.
:::

## B.6 `features.py`: transformaciones que solo aprenden del entrenamiento

### `CorrelationFilter`

{{>codigo src/features.py CorrelationFilter.fit}}

Es un transformador de scikit-learn (hereda de `BaseEstimator` y `TransformerMixin`), así que encaja en un `Pipeline` y se **ajusta solo con los datos de entrenamiento**. Su lógica, línea por línea:

- `frame.corr().abs()` calcula la matriz de correlación de Pearson en valor absoluto. `np.nan_to_num(..., nan=0.0)` trata como no correlacionadas las columnas constantes (cuya correlación es NaN).
- El bucle recorre las columnas **en orden**. Una columna se conserva solo si su correlación con **todas las ya conservadas** es menor o igual al umbral (`0.95`). Es un criterio voraz y **determinista**: siempre elige la misma columna entre dos redundantes (la primera).
- `keep_indices_` y `dropped_indices_` quedan guardados como atributos terminados en guion bajo, la convención de scikit-learn para "lo aprendido en `fit`".

{{>codigo src/features.py CorrelationFilter.transform}}

`transform` no recalcula nada: aplica los índices aprendidos. Por eso, si en los datos de prueba dos columnas fueran idénticas, **no** se descartaría una (el filtro no mira la prueba).

### `build_preprocessor` y `split_column_types`

{{>codigo src/features.py build_preprocessor}}

- Las columnas numéricas pasan sin cambios (`"passthrough"`): los árboles no necesitan escalado porque comparan valores con umbrales y el orden se conserva.
- Las categóricas (en UNSW-NB15: `proto`, `service`, `state`) se codifican en **one-hot**. `handle_unknown="infrequent_if_exist"` y `min_frequency=0.01` agrupan las categorías raras (menos del 1 %) y las no vistas en una categoría "infrecuente", de modo que clasificar un flujo con un protocolo nunca visto **no falla**.
- `set_output(transform="pandas")` hace que la salida conserve nombres de columna, lo que permite luego mostrar la importancia de variables con nombre.

{{>codigo src/features.py split_column_types}}

::: pregunta
**Pregunta de defensa.** ¿Qué se rompería si el filtro de correlación se calculara con todo el dataset antes de partir?

**Respuesta modelo.** Habría fuga de información: la decisión de qué columnas conservar usaría estadísticas de los flujos de prueba. El efecto en las métricas sería pequeño, pero conceptualmente la prueba habría influido en el modelo, y la evaluación ya no sería honesta. Dentro de un `Pipeline`, scikit-learn llama a `fit` solo con los datos de entrenamiento (y, en la validación cruzada, solo con los de cada pliegue de entrenamiento).
:::

## B.7 `models.py`: base, mejorado y mezcla

Este módulo fabrica los modelos. La idea central: **cada algoritmo existe en dos versiones sobre exactamente los mismos datos**, para poder preguntar con honestidad "¿la mejora sirvió?".

{{>codigo src/models.py _classifier}}

Los parámetros del modelo **base** son los del Entregable 1 (sección 8.4): Random Forest con 100 árboles y XGBoost con 100 árboles y profundidad 5. `n_jobs=-1` usa todos los núcleos; `tree_method="hist"` hace que XGBoost agrupe los valores en intervalos para entrenar mucho más rápido en millones de filas. Desde la última versión recibe `random_state` como argumento para poder repetir el experimento con otras semillas (`experiments.py`).

{{>codigo src/models.py build_pipeline}}

`build_pipeline` arma un `Pipeline` de scikit-learn con hasta tres pasos con nombre:

| Paso | Base | Mejorado | Qué hace |
|---|---|---|---|
| `prep` | sí | sí | One-hot de categóricas, numéricas sin cambios |
| `filter` | no | sí | `CorrelationFilter`: quita variables redundantes |
| `clf` | sí | sí | El clasificador (Random Forest o XGBoost) |

Los nombres `prep`, `filter` y `clf` importan: los hiperparámetros se dirigen con el prefijo `clf__` (por ejemplo `clf__max_depth`), que es la convención de scikit-learn para "el parámetro `max_depth` del paso `clf`".

::: nota
Un `Pipeline` garantiza que **todo lo aprendido** (codificador, filtro, árboles) se ajusta con los mismos datos y se aplica en el mismo orden en entrenamiento y en inferencia. Es la herramienta que evita la fuga entre pasos.
:::

### Espacios de búsqueda

`RF_SEARCH_SPACE` y `XGB_SEARCH_SPACE` son diccionarios con los valores candidatos de cada hiperparámetro (por ejemplo `clf__n_estimators` de 100, 200 o 300 para Random Forest). La búsqueda aleatoria sortea combinaciones de aquí; no prueba todas.

{{>codigo src/models.py SoftVotingEnsemble}}

`SoftVotingEnsemble` es el **Mix**. No se entrena: recibe modelos **ya entrenados** y promedia sus probabilidades de ataque (`np.mean(..., axis=0)`). `predict_proba` devuelve una matriz de dos columnas (normal y ataque) para ser intercambiable con cualquier modelo de scikit-learn. La votación es *suave* porque promedia probabilidades en lugar de contar votos.

{{>codigo src/models.py attack_scores}}

`attack_scores` extrae la columna de la clase "ataque" (índice 1) de `predict_proba`. Todo el resto del código habla de **puntajes** (probabilidades), no de decisiones: la decisión se toma al final comparando con un umbral.

::: pregunta
**Pregunta de defensa.** ¿Por qué el Mix no se vuelve a entrenar y usa los modelos ya ajustados?

**Respuesta modelo.** Porque es un promedio de las probabilidades de dos modelos que ya se ajustaron con los mismos datos de entrenamiento. Reentrenar no aportaría nada y duplicaría el tiempo. Además, usar los mismos modelos garantiza que la diferencia entre el Mix y sus miembros se debe solo al promedio, no a un entrenamiento distinto.
:::

## B.8 `metrics.py`: métricas, umbrales e incertidumbre

Es el corazón estadístico del proyecto. Todas las funciones trabajan con **puntajes** y un umbral.

{{>codigo src/metrics.py compute_metrics}}

`compute_metrics` construye la matriz de confusión comparando `scores >= threshold` con la etiqueta real y deriva todas las métricas. Detalles que importan:

- `_safe_divide` devuelve 0 cuando el denominador es 0 (por ejemplo, precisión sin ninguna alerta) en lugar de lanzar una excepción.
- `fpr = fp / (fp + tn)`: la proporción de tráfico **normal** que se marcó como ataque. Es la métrica central del proyecto.
- `roc_auc` y `pr_auc` se calculan con los puntajes (no con la decisión), así que **no dependen del umbral**. Si solo hay una clase en `y`, valen `nan` en lugar de fallar.

### Elegir el umbral: `select_threshold`

{{>codigo src/metrics.py select_threshold}}

Esta función implementa la regla literal de `AGENT.md`: *mínimo FPR con Recall mayor o igual a 0.95*. Se explica por pasos:

1. `np.argsort(-s, kind="stable")` ordena los puntajes de **mayor a menor**. Un umbral "deja pasar" a todos los flujos con puntaje igual o mayor.
2. `tp_cum` y `fp_cum` son sumas acumuladas: al bajar el umbral hasta la posición *i*, cuántos ataques (`tp_cum`) y cuántos normales (`fp_cum`) se marcan.
3. `last_of_run` conserva solo las posiciones donde el puntaje **cambia**. Si varios flujos tienen exactamente el mismo puntaje, el umbral no puede separarlos: o se marcan todos o ninguno. Esto es el **manejo de empates**.
4. `recall` y `fpr` se calculan para cada umbral candidato; `feasible` marca los que cumplen `recall >= objetivo`.
5. Entre los factibles gana el de menor FPR. `np.flatnonzero(candidate_fpr == candidate_fpr.min())[0]` toma **el primero**; como los umbrales están ordenados de mayor a menor, el primero es el **más alto** (el que genera menos alertas).
6. Si ningún umbral alcanza el objetivo, devuelve el de mayor Recall.

::: advertencia
La regla literal tiene un defecto cuando los modelos son casi perfectos: "mínimo FPR con Recall mayor o igual a 0.95" empuja el Recall **hasta 0.95** aunque el modelo podría dar 0.998, porque bajar el Recall reduce las falsas alarmas. En CICIDS2017, con XGBoost mejorado, los ataques no detectados pasan de {{cic.m.xgb_improved.default.fn}} (umbral 0.5) a {{cic.m.xgb_improved.recall_target.fn}} (umbral de esta regla). Por eso se añadió un segundo criterio.
:::

{{>codigo src/metrics.py select_threshold_for_fpr}}

`select_threshold_for_fpr` es el criterio complementario: *máximo Recall con FPR menor o igual a 0.02*, que modela un equipo de analistas con un presupuesto fijo de falsas alarmas. La estructura es casi idéntica; cambia qué se restringe y qué se maximiza. Si ni el corte más estricto cumple el presupuesto (solo posible con puntajes empatados), devuelve `np.nextafter(max, inf)`, un número apenas mayor que cualquier puntaje, para que **no se marque nada**.

### Incertidumbre: bootstrap de la matriz de confusión

{{>codigo src/metrics.py bootstrap_intervals}}

El bootstrap normal remuestrearía las filas una a una miles de veces: con casi 400 mil filas de prueba sería lento. El truco: si se remuestrean *n* filas con reemplazo, el número de filas que cae en cada celda de la matriz de confusión (VP, FN, FP, VN) sigue una distribución **multinomial** con probabilidades iguales a las proporciones observadas. Así, `rng.multinomial` genera 2000 "matrices de confusión remuestreadas" de una sola vez, y los intervalos salen de los percentiles 2.5 y 97.5.

::: importante
El intervalo solo captura el **ruido de muestreo de la prueba**, no la variación que produciría reentrenar con otra semilla. Por eso hay además un experimento con varias semillas.
:::

### Comparar dos modelos: bootstrap pareado

{{>codigo src/metrics.py paired_bootstrap_difference}}

La misma idea con ocho celdas: cada fila se codifica con `codes = y * 4 + a * 2 + b` (clase real, decisión de A, decisión de B), se cuentan las ocho combinaciones con `np.bincount` y se remuestrea de forma multinomial. Cada remuestreo da el Recall y el FPR de **ambos** modelos sobre las **mismas** filas, y la diferencia A menos B. El valor *p* bilateral es el doble de la cola más pequeña alrededor de cero.

La ventaja sobre comparar dos intervalos separados: dos modelos que ven los mismos flujos cometen errores correlacionados, y el pareado lo aprovecha. Por eso detecta diferencias pequeñas que los intervalos separados, aunque se solapen, esconden.

::: pregunta
**Pregunta de defensa.** Los intervalos de confianza de dos modelos se solapan. ¿Significa que son iguales?

**Respuesta modelo.** No. Que dos intervalos se solapen no prueba igualdad; es una prueba débil. Cuando ambos modelos se evalúan sobre las mismas filas, la comparación correcta es **pareada**. En este proyecto la prueba pareada encontró diferencias pequeñas pero significativas entre XGBoost mejorado y base que los intervalos separados no mostraban, por ejemplo {{unsw.p.xgb_improved__xgb_baseline.recall_target.fpr.diff}} en FPR en el punto de Recall 0.95 (p = {{unsw.p.xgb_improved__xgb_baseline.recall_target.fpr.p}}).
:::

## B.9 `train.py`: entrenamiento, umbrales y selección

Es el orquestador del entrenamiento. Su forma general, vista en `run`, es: cargar datos, partir, entrenar los seis modelos, elegir umbrales con la validación, evaluar, elegir el ganador, guardar todo.

### Búsqueda de hiperparámetros

{{>codigo src/train.py tune_hyperparameters}}

`RandomizedSearchCV` prueba `n_iter` combinaciones sorteadas del espacio de búsqueda. Para cada una hace validación cruzada estratificada de `cv_folds` pliegues (`StratifiedKFold`, con `shuffle=True` y semilla fija). Puntos clave:

- `scoring="average_precision"`: la métrica de la búsqueda es el área bajo la curva de precisión-recall, que **no depende del umbral** y es sensible al desbalance. Se prefiere a la accuracy, que premia no detectar nada cuando hay pocos ataques.
- Como el estimador es el `Pipeline` completo (con el filtro de correlación), **cada pliegue vuelve a ajustar el filtro** solo con sus datos de entrenamiento. No hay fuga entre pliegues.
- `refit=False`: no reentrena el mejor modelo dentro de la búsqueda (lo hace `train_algorithm` con todo el entrenamiento).
- `n_jobs=1`: la búsqueda va en serie porque cada modelo ya usa todos los núcleos.

{{>codigo src/train.py train_algorithm}}

`train_algorithm` produce el par base y mejorado de un algoritmo:

1. Ajusta el **base** con todo el entrenamiento y los parámetros por defecto.
2. Saca una **muestra estratificada** (`tune_sample`, por defecto 60000 flujos) y busca hiperparámetros ahí: buscar con millones de filas tomaría horas.
3. Reentrena el **mejorado** con *todo* el entrenamiento y los mejores hiperparámetros (`set_params(**best_params).fit(X, y)`).

::: advertencia
Límite conocido: buscar hiperparámetros en una muestra puede elegir valores pequeños para el modelo completo. En CICIDS2017 la búsqueda eligió profundidad 12 para Random Forest, y el modelo mejorado salió peor que el base con umbral 0.5. Es una limitación del método, no un error de código.
:::

### Tres umbrales por modelo

{{>codigo src/train.py choose_thresholds}}

`choose_thresholds` define los **tres puntos de operación**: el 0.5 fijo (lo que reporta casi toda la literatura), el que minimiza el FPR con Recall mayor o igual a 0.95 y el que maximiza el Recall con FPR menor o igual a 0.02. Reciben **solo** los puntajes de validación (`y_val`, `val_scores`); la prueba no entra.

{{>codigo src/train.py evaluate_models}}

`evaluate_models` puntúa cada modelo en validación y prueba, elige sus umbrales con la validación y calcula métricas en ambas particiones. Devuelve filas en formato "largo" (una fila por modelo, punto de operación y partición), que se guardan como `metrics.csv`.

### Elegir al ganador

{{>codigo src/train.py select_best}}

La selección usa **solo filas de validación** (`r["split"] == "val"`). Entre los modelos cuyo Recall de validación cumple la meta, gana el de menor FPR y, en caso de empate, el de mayor F1 (`key=lambda r: (r["fpr"], -r["f1"])`: Python compara tuplas en orden, y el signo menos invierte el F1 para que "mayor" gane). Elegir con la validación evita el **sesgo de selección** que habría si se escogiera el ganador mirando la prueba.

### Todo junto: `run`

{{>codigo src/train.py run}}

Lo que `run` deja en disco:

| Archivo | Contenido |
|---|---|
| `models/<dataset>/best_model.joblib` | Modelo ganador, sus tres umbrales y las columnas esperadas |
| `models/<dataset>/scores.npz` | Puntajes de validación y prueba de los seis modelos, etiquetas y familias |
| `reports/<dataset>/metrics.csv` | Métricas en formato largo |
| `reports/<dataset>/training_summary.json` | Partición, ganador, umbrales, hiperparámetros, tiempos, importancias |

### Recalcular sin reentrenar: `rescore`

{{>codigo src/train.py rescore}}

`rescore` vuelve a calcular umbrales, métricas y ganador **desde `scores.npz`**, sin reentrenar. Si el nuevo criterio elegiría un modelo distinto del guardado, se niega (`RuntimeError`) y pide reentrenar, porque el archivo del modelo ya no coincidiría con el ganador. Es la herramienta que permitió añadir el tercer punto de operación sin repetir 25 minutos de entrenamiento.

```bash
python -m src.train --dataset unsw_nb15                 # unos 7 minutos con 4 CPU
python -m src.train --dataset cicids2017                # entre 15 y 25 minutos
python -m src.train --dataset unsw_nb15 --rescore       # recalcular sin reentrenar
python -m src.train --dataset unsw_nb15 --n-iter 1 --tune-sample 20000 --cv-folds 3   # prueba rápida
```

::: advertencia
La prueba rápida **sobrescribe** `models/` y `reports/` del dataset. No reproduce las cifras del informe porque busca con un solo candidato.
:::

::: pregunta
**Pregunta de defensa.** ¿Por qué el umbral se elige en validación y no en prueba?

**Respuesta modelo.** Porque elegir el umbral es una **decisión** que se optimiza con los datos. Si se optimizara con la prueba, el resultado reportado sería optimista: el umbral estaría hecho a la medida de esas filas. Con el umbral fijado en validación, la prueba mide cómo se comporta esa decisión en datos que no vio. Una consecuencia visible: el FPR en prueba puede quedar un poco por encima del presupuesto de 0.02 (el intervalo lo incluye), y se reporta tal cual.
:::

## B.10 `predict.py`: clasificar flujos nuevos

El motor de inferencia. Carga el modelo ganador de un dataset y clasifica un archivo de flujos o un flujo suelto en JSON.

{{>codigo src/predict.py load_bundle}}

El "bundle" es un diccionario guardado con `joblib`: el modelo, sus tres umbrales y las listas de columnas. Guardar **juntos** el modelo y su umbral evita el error clásico de usar un modelo con el umbral de otro.

{{>codigo src/predict.py prepare_features}}

`prepare_features` es la barrera de entrada: recorta los espacios de los nombres de columna (los CSV crudos de CICIDS2017 los traen), ignora columnas sobrantes como las etiquetas, **exige** todas las columnas del modelo y **rechaza** filas con valores no numéricos, faltantes o infinitos con un mensaje que indica cuántas son y cuál es la primera. Rechazar es más seguro que adivinar: un valor imputado en silencio daría una predicción sin sentido.

{{>codigo src/predict.py classify}}

`classify` calcula la probabilidad de ataque y la compara con el umbral del punto de operación elegido (`bundle["thresholds"][operating_point]`). El texto de salida es `Trafico Normal` o `Ataque Detectado`, como pide `AGENT.md`.

```bash
python -m src.predict --dataset unsw_nb15 --input docs/demo/flujos_ejemplo.csv
python -m src.predict --dataset unsw_nb15 --input flujos.csv --operating-point fpr_budget
python -m src.predict --dataset unsw_nb15 --json "$(cat docs/demo/flujo_ejemplo.json)"
```

::: pregunta
**Pregunta de defensa.** ¿Qué pasa si se le da a `predict` un flujo con un protocolo que no existía en el entrenamiento?

**Respuesta modelo.** No falla. El codificador one-hot se configuró con `handle_unknown="infrequent_if_exist"`, así que las categorías no vistas (o raras) caen en el grupo "infrecuente". El modelo las trata como cualquier categoría poco común. Lo que sí se rechaza es un flujo al que le faltan columnas o con valores infinitos.
:::

## B.11 `evaluate.py`: figuras y reporte en español

Lee lo que dejó `train.py` (`scores.npz`, `metrics.csv`, `training_summary.json`) y produce seis figuras y `resultados.md`. **No carga ningún modelo**: trabaja con los puntajes guardados, por eso corre en segundos.

{{>codigo src/evaluate.py detection_by_attack_type}}

`detection_by_attack_type` es la función más útil para la defensa. Para cada familia de ataque calcula qué proporción de sus flujos de prueba supera el umbral, en cada punto de operación:

- `pd.Series(scores[...] >= thresholds[point])` convierte los puntajes en una serie de verdadero o falso.
- `.groupby(families).mean()` promedia esa serie por familia: el promedio de verdaderos es la **tasa de detección** de la familia.
- En la fila `BENIGN` el mismo promedio es la **tasa de falsas alarmas**, porque ahí marcar como ataque es un error.
- Se añade la columna `n` (flujos de prueba por familia): las familias con pocos flujos tienen estimaciones muy inestables y hay que decirlo al interpretarlas.

{{>codigo src/evaluate.py run}}

Las seis figuras son: matrices de confusión, curvas ROC (lineal y con FPR logarítmico), precisión-recall, comparación de FPR y Recall en los tres puntos, detección por familia e importancia de variables. `write_markdown` arma tablas con intervalos de confianza llamando a `bootstrap_intervals`.

```bash
python -m src.evaluate --dataset unsw_nb15     # reports/unsw_nb15/resultados.md y figures/
```

::: pregunta
**Pregunta de defensa.** ¿Por qué el eje del FPR en la curva ROC se muestra en escala logarítmica?

**Respuesta modelo.** Porque la zona que importa para un IDS es la de FPR muy pequeño (de una centésima a una diezmilésima). En escala lineal esa región queda aplastada contra el eje y las curvas de todos los modelos parecen iguales. La escala logarítmica la amplía y permite ver dónde caen los puntos de operación y la zona objetivo del proyecto.
:::

## B.12 `leakage_ablation.py`: cuánto inflan los duplicados las métricas

Responde a una pregunta concreta: *si no se depuran los duplicados, ¿cuánto se equivoca la evaluación?* Entrena el **mismo** XGBoost base bajo tres protocolos de limpieza y mide, además, qué parte de la prueba ya estaba en el entrenamiento.

{{>codigo src/leakage_ablation.py leaked_share}}

`leaked_share` reduce cada fila de entrenamiento a un hash de 64 bits y guarda los hashes en un `set` (búsqueda en tiempo constante). Luego mira qué fracción de las filas de prueba tiene su hash en ese conjunto. Es la fracción de la prueba que el modelo puede "acertar por memoria".

{{>codigo src/leakage_ablation.py evaluate_protocol}}

Los tres protocolos (`PROTOCOLS`) se definen con las dos banderas de `clean`:

| Protocolo | Quita duplicados | Quita contradictorios | Qué representa |
|---|---|---|---|
| `naive` | no | no | Solo la limpieza obligatoria (infinitos, NaN): lo que haría un análisis apresurado |
| `dedup` | sí | no | Quita duplicados pero deja los contradictorios |
| `full` | sí | sí | El protocolo del proyecto |

{{>tabla_fuga unsw}}

::: nota
En UNSW-NB15 el protocolo ingenuo sobrestima el Recall y la accuracy porque casi la mitad de la prueba son vectores ya vistos. En CICIDS2017 el efecto es despreciable porque el dataset ya está saturado (los modelos son casi perfectos de todos modos). Es evidencia de **magnitud** con una semilla y un modelo, no una prueba estadística.
:::

```bash
python -m src.leakage_ablation --dataset unsw_nb15
```

## B.13 `experiments.py`: experimentos formales

Reúne los cuatro experimentos de la entrega final. Todos escriben CSV en `reports/<dataset>/`.

```bash
python -m src.experiments --dataset unsw_nb15 --task all
python -m src.experiments --dataset cicids2017 --task seeds
```

### Varias semillas

{{>codigo src/experiments.py seed_rows}}

`seed_rows` repite el protocolo completo con una semilla dada: parte los datos (`make_splits(df, random_state=seed)`), ajusta los seis modelos (la semilla también va al modelo) y devuelve las filas de métricas. Los hiperparámetros de las versiones mejoradas **no se vuelven a buscar**: se reutilizan los de la semilla 42 (`params`).

::: advertencia
Límite declarado: como la búsqueda de hiperparámetros se hizo una sola vez, la desviación entre semillas **no incluye** la variación que produciría repetir la búsqueda. Además, los datos con los que se ajustaron esos hiperparámetros se solapan con las pruebas de las otras semillas. La desviación estándar subestima la incertidumbre real.
:::

{{>codigo src/experiments.py run_seeds}}

`run_seeds` añade robustez: guarda cada semilla terminada en `multiseed.partial.csv` y, si el proceso se interrumpe, **retoma** desde ahí en lugar de empezar de cero. Esto nació de un hecho real: un reinicio del contenedor interrumpió el cómputo de CICIDS2017 y se perdía todo lo hecho. Al final escribe `multiseed.csv`, el resumen y borra el archivo parcial. La semilla 42 se lee de `metrics.csv` (no se recalcula) salvo con `--recompute-primary`, que además verifica que reproduce las métricas guardadas.

{{>codigo src/experiments.py summarize_seeds}}

`summarize_seeds` calcula media, desviación estándar muestral, mínimo y máximo por modelo y punto de operación, sobre la partición de prueba.

{{>codigo src/experiments.py seed_differences}}

`seed_differences` mira, semilla por semilla, la diferencia "mejorado menos base" y cuenta en cuántas semillas la versión mejorada gana según el criterio propio de cada punto de operación. Es la forma de responder "¿la mejora es consistente?" sin depender de un solo reparto. Se calcula con la tarea `--task differences`, que lee `multiseed.csv` y escribe `multiseed_differences.csv`.

### Pruebas pareadas

`run_pairwise` aplica `paired_bootstrap_difference` (sección B.8) a siete pares de modelos y tres puntos de operación, usando los puntajes guardados de la semilla 42. Los pares comparan la versión mejorada con la base de cada algoritmo, XGBoost con Random Forest y el Mix con XGBoost.

### Particiones oficiales de UNSW-NB15

{{>codigo src/experiments.py split_official_partitions}}

Asigna **por tamaño**, no por nombre, porque el espejo tiene los nombres intercambiados. Si no recibe exactamente dos particiones, falla con un mensaje claro.

{{>codigo src/experiments.py seen_mask}}

`seen_mask` devuelve, fila por fila, si el vector de prueba aparece en el entrenamiento. Se usa en el protocolo B para **quitar de la prueba** lo que ya estaba en el entrenamiento oficial.

{{>codigo src/experiments.py official_rows}}

`official_rows` ejecuta tres protocolos: **A**, entrenar con la partición oficial de entrenamiento y probar en la oficial de prueba, sin depurar (como la literatura); **B**, lo mismo con ambas depuradas y sin vectores repetidos entre ellas; y **C**, validación cruzada de 5 pliegues sobre la partición de entrenamiento, ingenua y depurada. Se compara con las cifras de un estudio reciente, pero sin atribuirle un protocolo que no se pudo verificar.

{{>tabla_oficial}}

::: importante
Lectura honesta. La hipótesis de que los duplicados explicaran por sí solos la accuracy de 0.97 que reporta Alkhater (2026) **no se confirmó**: la validación cruzada ingenua sobre la partición oficial de entrenamiento queda por debajo de 0.97, y la depurada más abajo aún. Los duplicados explican una parte de la diferencia, no toda. Además, el protocolo A (particiones oficiales) da una accuracy mucho menor y un FPR alto: hay un **cambio de distribución** entre la partición oficial de entrenamiento y la de prueba.
:::

### Ablación de variables

{{>codigo src/experiments.py ablation_rows}}

Reentrena XGBoost con los hiperparámetros de la versión mejorada **sin** un grupo de variables sospechosas de ser atajos (por ejemplo `sttl`, `dttl`, `ct_state_ttl` y `state` en UNSW-NB15) y vuelve a elegir los umbrales en validación. `drop_feature_group` es estricto: si un nombre no existe lanza `KeyError`, para que un error de tipeo no haga "nada" en silencio.

{{>tabla_ablacion unsw}}

::: nota
Que el rendimiento no baje al quitar un grupo **no prueba** que el modelo no use atajos: otras variables correlacionadas pueden tomar su lugar. Sí muestra que el rendimiento no *depende* de ese grupo.
:::

### `experiments_report.py`

Lee los CSV de los experimentos y escribe `experimentos.md` y tres figuras (media y desviación por semilla, diferencias pareadas, ablación). Tiene una regla: **si falta un CSV, esa sección se omite** en lugar de fallar.

```bash
python -m src.experiments_report --dataset unsw_nb15
```

::: pregunta
**Pregunta de defensa.** ¿Por qué se repite con varias semillas si ya hay intervalos de confianza?

**Respuesta modelo.** Porque miden cosas distintas. El intervalo bootstrap mide el ruido de muestreo de **una** prueba. Las semillas miden cuánto cambia el resultado al repartir los datos de otra forma y reentrenar. Una conclusión sólida debería sobrevivir a ambos. Y hay que decir que la desviación entre semillas no incluye repetir la búsqueda de hiperparámetros.
:::

## B.14 `demo.py` y `app/demo_app.py`: la demostración

La demo visual (Streamlit) **no entrena ni recalcula nada pesado**: carga el modelo y los resultados ya generados. `src/demo.py` contiene la lógica en pandas y numpy puro (para poder probarla sin Streamlit) y `app/demo_app.py` solo dibuja.

{{>codigo src/demo.py metrics_at_threshold}}

`metrics_at_threshold` es la pieza que hace interactivo el deslizador de umbral: recalcula Recall, FPR y matriz de confusión **al instante** con los puntajes guardados de la prueba, para cualquier umbral.

{{>codigo src/demo.py meets_criterion}}

`meets_criterion` aplica el criterio completo de `AGENT.md`: Recall mayor o igual a 0.95 **y** FPR menor o igual a 0.02 a la vez. La app muestra un cartel verde o rojo según su resultado.

{{>codigo src/demo.py judge}}

`judge` añade a cada predicción su veredicto cuando el archivo trae etiquetas reales: ataque detectado, normal correcto, **falsa alarma** o **ataque no detectado**. Se usa para colorear la tabla de la pestaña de clasificación.

{{>codigo src/demo.py build_example_flows}}

`build_example_flows` arma los flujos de ejemplo del guion: elige filas al azar del conjunto de **prueba** y, además, dos casos **elegidos a propósito** que muestran errores (una falsa alarma que aparece solo con cierto umbral y un ataque que se escapa en todos los puntos). La nota de cada fila lo declara, para no presentar un caso escogido como si fuera típico.

### Estructura de la app

{{>codigo app/demo_app.py main}}

| Pestaña | Función | Qué muestra |
|---|---|---|
| 1. Datos | `tab_data` | Embudo de limpieza y flujos por tipo de tráfico |
| 2. Clasificar en vivo | `tab_classify` | Ejemplos, CSV subido o JSON, con probabilidad y veredicto |
| 3. Umbral interactivo | `tab_threshold` | Deslizador, matriz de confusión, ROC y detección por familia |
| 4. Comparación de modelos | `tab_models` | Seis modelos en el plano FPR contra Recall e importancias |
| 5. Fuga de datos | `tab_leakage` | La ablación de duplicados |

`st.cache_resource` (en `get_context`) carga el modelo una sola vez por dataset: sin él, cada movimiento del deslizador recargaría el archivo del disco.

```bash
streamlit run app/demo_app.py        # abre http://localhost:8501
```

::: pregunta
**Pregunta de defensa.** ¿Por qué la lógica de la demo está en `src/demo.py` y no dentro de la app?

**Respuesta modelo.** Para poder **probarla** automáticamente. Streamlit es una interfaz difícil de verificar con pruebas unitarias, mientras que funciones puras de pandas y numpy se prueban con datos sintéticos. La app queda como una capa fina que solo dibuja lo que calcula `demo.py`.
:::

## B.15 Pruebas automáticas, calidad de código y CI

El repositorio tiene más de 60 funciones de prueba (`pytest`), todas con **datos sintéticos**: no necesitan descargar nada, corren en pocos segundos y por eso pueden ejecutarse en cualquier computador y en la nube.

| Archivo | Qué protege |
|---|---|
| `test_preprocess.py` | Cada paso de la limpieza, incluidos los dos errores corregidos (conflictos por etiqueta binaria y conversión a `float32` antes de deduplicar) |
| `test_data_loader.py` | Tamaños 70/15/15, estratificación, determinismo y ausencia de solapamiento entre particiones |
| `test_metrics.py` | Las métricas contra cálculo a mano, los umbrales (empates, objetivo inalcanzable) y los bootstrap |
| `test_features.py` | El filtro solo usa datos de ajuste; el codificador tolera categorías nuevas |
| `test_train.py` | El flujo completo entrenar, evaluar y predecir con datos sintéticos, y que `rescore` reproduce las métricas |
| `test_leakage.py` | La fracción de prueba repetida |
| `test_experiments.py` | Semillas, pruebas pareadas, particiones oficiales, ablación y la reanudación desde el archivo parcial |
| `test_demo.py` | La lógica de la demo (métricas por umbral, curva ROC, ejemplos) |
| `test_files.py` | La huella SHA256 y la descarga verificada |

`conftest.py` define dos datos sintéticos reutilizables: `raw_frame` (un crudo pequeño con infinitos, NaN, duplicados, contradictorios y una columna constante) y `processed_frame` (un dataset limpio con tres tipos de ataque y una clase rara).

### Configuración y CI

`pyproject.toml` configura tres herramientas:

- **ruff**: reglas de errores, estilo y buenas prácticas (`E`, `F`, `W`, `I`, `B`, `UP`), con 120 columnas. Es un "corrector" estático que busca importaciones sin usar y errores comunes.
- **mypy**: revisa los tipos declarados en `src/` (el proyecto exige tipado estático donde aplique).
- **pytest**: busca pruebas en `tests/`.

El flujo `.github/workflows/tests.yml` ejecuta en GitHub, en cada *push* a `main` y en cada *pull request*, los tres pasos (ruff, mypy y pytest) en **Python 3.10 y 3.13**. Probar el límite inferior declarado en el README y la versión actual detecta incompatibilidades de versiones (por ejemplo, pandas 2 frente a pandas 3).

```bash
python -m pytest              # todas las pruebas
ruff check .                  # estilo y errores comunes
mypy                          # tipos
```

::: advertencia
Ejecuta siempre `python -m pytest` y no `pytest` a secas: el shell puede tener en caché un `pytest` de fuera del entorno virtual, que no ve `xgboost` y falla al importar. Esto le pasó realmente a un integrante del equipo.
:::

::: pregunta
**Pregunta de defensa.** ¿Qué garantiza que el código funciona si no hay datos reales en las pruebas?

**Respuesta modelo.** Las pruebas reproducen con datos sintéticos **cada rareza** de los datos reales (infinitos, duplicados, contradictorios, categorías nuevas, clases raras) y verifican el comportamiento esperado. Además, la tubería completa se ejecutó sobre los datos reales y sus resultados se versionan en `reports/`. Las pruebas no reemplazan esa ejecución, pero impiden que un cambio rompa una decisión de diseño (por ejemplo, volver a deduplicar antes de convertir a `float32`).
:::

## B.16 Cómo se construyen los cuatro PDF

Este paquete de entrega también está hecho con código, en `docs/entrega/`, para que **ninguna cifra se escriba a mano**:

| Archivo | Función |
|---|---|
| `fuentes/*.md` | El texto en Markdown. Cada cifra es un marcador con el nombre de su clave entre dobles llaves y cada tabla un marcador de tabla con sus argumentos |
| `datos_docs.py` | Lee `reports/` y `data/processed/` y reemplaza cada marcador; si una clave no existe, la construcción **falla** |
| `make_figures.py` | Genera diagramas y gráficas con datos reales |
| `build.py` | Convierte Markdown a HTML (pandoc), lo imprime a PDF (Chromium) y vuelve a imprimirlo con el índice numerado |
| `check_source.py` | Comprueba marcadores sin resolver y caracteres prohibidos (guiones largos, emojis) |

El principio: si cambian los resultados, se regeneran los reportes y se reconstruyen los PDF, y las cifras se actualizan solas. Además, los fragmentos de código de esta guía se extraen del propio repositorio con una función (`codigo`), de modo que **nunca quedan desactualizados**.

```bash
python docs/entrega/make_figures.py
python docs/entrega/build.py            # los cuatro PDF a docs/entrega/pdf/
python docs/entrega/check_source.py docs/entrega/fuentes/guia_b_codigo.md
```
