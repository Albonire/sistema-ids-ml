# Introducción y problema

## Contexto

Un sistema de detección de intrusiones de red (IDS, por *Intrusion Detection System*) observa el tráfico de una red y avisa cuando algo parece un ataque. Es una capa de **detección** dentro de la gestión de riesgo de ciberseguridad: en la terminología del Marco de Ciberseguridad del NIST, versión 2.0, corresponde a la función *Detectar* (NIST, 2024), como se planteó en el Entregable 1. No reemplaza al cortafuegos, al endurecimiento de equipos ni a la gestión de vulnerabilidades; los complementa generando alertas que luego alimentan la respuesta a incidentes.

El Entregable 1 recogió cifras sobre el contexto colombiano (ICEX España Exportación e Inversiones, 2025; Centro Cibernético Policial, citado en Impacto TIC, 2025). Se mantienen aquí como contexto tomado de ese documento y no se volvieron a verificar para este informe.

## El problema de los IDS tradicionales

Los IDS clásicos se basan en **firmas**: reglas escritas de antemano que reconocen patrones conocidos. Esto produce dos limitaciones que motivan el proyecto:

1. **Amenazas desconocidas.** Una variante de ataque sin regla previa pasa desapercibida (el caso *zero-day*).
2. **Falsas alarmas.** Las reglas rígidas marcan como malicioso tráfico legítimo pero atípico. Cada falsa alarma consume tiempo de un analista, y si son demasiadas el equipo deja de confiar en el sistema (fatiga por alertas).

El aprendizaje automático permite aprender, a partir de ejemplos etiquetados, la forma estadística del tráfico normal y de los ataques, y generalizar a casos nuevos. La contrapartida es que su calidad depende de cómo se construyan y se evalúen los datos, y ese es el eje metodológico de este trabajo.

## Pregunta de investigación

> ¿Qué algoritmo de aprendizaje automático proporciona el mejor equilibrio entre capacidad de detección y tasa de falsos positivos para un IDS basado en un dataset de tráfico de red?

La pregunta contiene dos magnitudes en tensión: la **capacidad de detección** (Recall, la fracción de ataques detectados) y la **tasa de falsos positivos** (FPR, la fracción de tráfico normal marcado como ataque). Ningún algoritmo maximiza ambas a la vez; lo que existe es una curva de compromiso. Por eso el informe responde con tres puntos de operación sobre esa curva y no con un solo número.

## Alcance

- Se trabaja con archivos históricos de flujos de red, no con captura de tráfico en vivo (fuera de alcance, como se declaró en el Entregable 1).
- Se usan dos datasets públicos: **UNSW-NB15** (principal) y **CICIDS2017** (contraste).
- Por indicación de la docente se limitó el número de modelos: Random Forest, XGBoost y la combinación de ambos (*Mix*), cada uno en versión **base** y **mejorada**. SVM, redes neuronales y árboles CART quedaron fuera.

# Objetivos

## Objetivo general

Desarrollar un prototipo basado en aprendizaje automático capaz de identificar y clasificar tráfico de red normal y malicioso, y evaluar con rigor el equilibrio entre detección y falsas alarmas.

## Objetivos específicos y estado

| Objetivo | Estado | Dónde se cumple |
|---|---|---|
| Descargar, limpiar y preparar dos datasets públicos con evaluación libre de fuga de datos | Cumplido | Capítulos 5 y 6 |
| Entrenar y comparar Random Forest, XGBoost y su combinación, en versión base y mejorada | Cumplido | Capítulos 4 y 7 |
| Evaluar con métricas formales (Accuracy, Precisión, Recall, F1, FPR, ROC-AUC) analizando la frontera entre detección y falsas alarmas | Cumplido | Capítulo 7 |
| Construir un prototipo reproducible en Python (`train`, `predict`, `evaluate`) para lotes y flujos individuales | Cumplido | Capítulo 6 |
| Experimentación formal: varias semillas, pruebas de significancia, particiones oficiales y ablación de variables | Cumplido, con límites declarados | Capítulos 7 y 10 |

# Marco teórico y estado del arte

## Detección de intrusiones

Un NIDS (de red) analiza **flujos**: resúmenes de una conversación entre dos equipos (duración, paquetes y bytes en cada sentido, banderas TCP, tiempos entre paquetes). Herramientas como CICFlowMeter calculan decenas de estas variables por flujo. La detección por **firmas** reconoce lo ya visto; la detección por **anomalías** o por aprendizaje modela lo normal y lo malicioso para generalizar.

## Los algoritmos usados

- **Random Forest** (Breiman, 2001): un conjunto de árboles de decisión entrenados cada uno con una muestra aleatoria de los datos y de las variables; la predicción es la votación del conjunto. Es estable y poco sensible al sobreajuste.
- **XGBoost** (Chen y Guestrin, 2016): árboles construidos en secuencia, cada uno corrige los errores del conjunto anterior (*gradient boosting*), con regularización. Suele ser el mejor en datos tabulares.
- **Mix**: promedio de las probabilidades de ataque de Random Forest y XGBoost (votación suave). No se reentrena.

## Métricas y puntos de operación

Con el ataque como clase positiva, la matriz de confusión tiene verdaderos positivos (VP), falsos positivos (FP), verdaderos negativos (VN) y falsos negativos (FN):

$$\mathrm{Recall}=\frac{VP}{VP+FN}\qquad \mathrm{FPR}=\frac{FP}{FP+VN}\qquad \mathrm{Precisi\acute{o}n}=\frac{VP}{VP+FP}\qquad F_1=\frac{2\cdot \mathrm{Precisi\acute{o}n}\cdot \mathrm{Recall}}{\mathrm{Precisi\acute{o}n}+\mathrm{Recall}}$$

Un clasificador entrega una probabilidad de ataque y una **regla de decisión** la convierte en alerta: se marca ataque si la probabilidad supera un umbral. Cambiar el umbral recorre la curva ROC. Un **punto de operación** es un umbral concreto. Este trabajo evalúa tres, siempre con el umbral elegido en validación:

| Punto | Regla | Para qué sirve |
|---|---|---|
| Umbral 0.5 | Valor fijo por defecto | Referencia sencilla |
| Mínimo FPR con Recall >= 0.95 | Criterio literal de `AGENT.md` | Selección oficial del modelo |
| Máximo Recall con FPR <= 0.02 | Presupuesto de falsas alarmas | Modela un SOC con capacidad limitada de revisar alertas |

La **accuracy** engaña cuando las clases están desbalanceadas: un clasificador que dijera siempre "normal" acertaría el porcentaje de tráfico normal. Por eso el criterio del proyecto se expresa con Recall y FPR.

## Datasets

**UNSW-NB15** (Moustafa y Slay, 2015) fue generado por la Universidad de Nueva Gales del Sur con tráfico real y ataques sintéticos. Tiene nueve familias de ataque (Fuzzers, Analysis, Backdoor, DoS, Exploits, Generic, Reconnaissance, Shellcode y Worms) más tráfico normal y variables categóricas (`proto`, `service`, `state`). Se publica en una partición oficial de entrenamiento (175 341 flujos) y otra de prueba (82 332).

**CICIDS2017** (Sharafaldin, Habibi Lashkari y Ghorbani, 2018) fue generado por el Canadian Institute for Cybersecurity con CICFlowMeter durante cinco días de captura. Incluye DoS, DDoS, PortScan, fuerza bruta (SSH y FTP), ataques web, botnet e infiltración.

## Antecedentes verificados

| Referencia | Aporte relevante | Alcance de la verificación |
|---|---|---|
| Engelen, Rimmer y Joosen (2021) | Errores de generación de flujos, extracción de variables y etiquetado en CICIDS2017: más del 20 % del tráfico se reconstruye o reetiqueta al corregirlo, y los llamados "apéndices TCP" son el 25.9 % del dataset. Con Random Forest, las métricas agregadas coinciden (0.99) pero por clase difieren mucho (por ejemplo, F1 de 0.18 en XSS y 0.60 en Bot). Detectan aprendizaje por atajos. | PDF leído completo |
| Lanvin y otros (2023) | Fallos de etiquetado y de captura en CICIDS2017 (paquetes desordenados, duplicados, ataques no etiquetados) y su efecto en la evaluación. | Solo resumen |
| Alkhater (2026) | Compara árbol de decisión, Random Forest, SVM y XGBoost en UNSW-NB15 con validación cruzada estratificada de 5 folds; XGBoost fue el mejor (accuracy 0.97, AUC 0.98); variables clave `sttl`, `sload` y `dload`. | Solo resumen (el editor bloquea el acceso automático al texto completo) |

## Vacío que aborda este trabajo

Los antecedentes reportan métricas agregadas con protocolos que no siempre separan duplicados entre entrenamiento y prueba. Engelen y otros (2021) advierten que las métricas agregadas sobre datasets desbalanceados no bastan para juzgar un IDS. Este trabajo hace tres cosas distintas: evalúa **sin fuga de datos**, reporta **tres puntos de operación** con **intervalos de confianza** y pruebas pareadas, y **cuantifica** cuánto cambian las cifras al relajar cada precaución.

# Metodología

## Tipo de investigación

Aplicada y experimental: se implementa un prototipo y se valida empíricamente. Todo el proceso es reproducible con `python -m src.download_data`, `src.preprocess`, `src.train`, `src.evaluate` y `src.experiments`, con semillas fijas y descarga verificada por suma SHA256.

## Limpieza de datos

Se aplican, en este orden y antes de partir los datos:

1. **Infinitos y valores faltantes**: se eliminan las filas afectadas (aparecen sobre todo en `Flow Bytes/s` y `Flow Packets/s` de CICIDS2017).
2. **Conversión a `float32`** antes de buscar duplicados: dos vectores que difieren por debajo de la precisión del modelo son el mismo vector para el modelo.
3. **Duplicados**: se juzgan con las características y la etiqueta **binaria**. Un mismo vector con dos familias de ataque distintas es un duplicado y se conserva una fila.
4. **Vectores contradictorios**: un mismo vector etiquetado a la vez como normal y como ataque es ruido irreducible; se descartan todas sus filas.
5. **Columnas constantes**: se eliminan.

Una primera versión juzgaba los conflictos por familia de ataque en vez de por etiqueta binaria y descartaba por error decenas de miles de flujos de UNSW-NB15 (126 protocolos raros desaparecían por completo). Se corrigió y quedó cubierto por una prueba.

## Partición

70 % entrenamiento, 15 % validación y 15 % prueba, estratificada por tipo de ataque, con `random_state=42`. El conjunto de prueba **no interviene en ninguna decisión**: ni hiperparámetros, ni filtro de variables, ni umbrales, ni la elección del modelo. Todo paso que aprende de los datos se ajusta solo con entrenamiento o validación.

## Modelos: base y mejorada

- **Base**: la configuración del Entregable 1, sección 8.4 (Random Forest con 100 árboles; XGBoost con 100 árboles y profundidad 5) y umbral 0.5.
- **Mejorada**: (1) filtro de correlación que elimina una variable de cada par con |r| > 0.95, ajustado con entrenamiento; (2) hiperparámetros por búsqueda aleatoria con validación cruzada estratificada de 5 folds (8 candidatos, sobre una muestra estratificada de 60 000 flujos; el modelo final se reentrena con todo el entrenamiento); (3) umbrales elegidos en validación.

Las variables categóricas de UNSW-NB15 se codifican en *one-hot*, agrupando las categorías raras (menos del 1 %) en una categoría "infrecuente" para que la inferencia nunca falle con valores nuevos. Los árboles no necesitan escalado.

## Criterio de decisión y selección del modelo

El criterio literal de `AGENT.md` es: mínimo FPR con Recall >= 0.95. El modelo ganador se elige **en validación** con esa regla. Como esa regla resulta degenerada cuando los modelos son casi perfectos (capítulo 8), se reportan además el punto de presupuesto de falsas alarmas y el umbral 0.5.

## Cómo se mide la incertidumbre

- **Intervalos de confianza bootstrap** del Recall y del FPR de cada modelo. Remuestrear n filas con reemplazo hace que las cuatro celdas de la matriz de confusión sigan una distribución multinomial, por lo que el bootstrap exacto se calcula sobre conteos.
- **Pruebas pareadas** entre dos modelos sobre las mismas filas de prueba, cada uno con su umbral. Son más sensibles que comparar dos intervalos separados, porque ambos modelos ven los mismos flujos.
- **Repetición con semillas**: cinco particiones y ajustes distintos.

## Experimentos formales

| Experimento | Pregunta que responde |
|---|---|
| Cinco semillas | ¿Los resultados dependen de una partición afortunada? |
| Pruebas pareadas | ¿Las diferencias entre modelos superan el ruido de la prueba? |
| Particiones oficiales de UNSW-NB15 | ¿Qué pasa al usar la partición oficial de prueba en vez de una partición aleatoria? |
| Ablación de variables | ¿Depende el modelo de variables sospechosas de ser atajos? |
| Ablación de duplicados | ¿Cuánto inflan las métricas los duplicados entre entrenamiento y prueba? |

# Datos y hallazgos de la limpieza

## Qué cambió con la limpieza

{{>tabla_limpieza}}

En UNSW-NB15, {{unsw.clean.dup_pct}} de los flujos crudos son duplicados y {{unsw.clean.conf_pct}} son contradictorios: en total se descarta {{unsw.clean.removed_pct}} del dataset, y quedan {{unsw.clean.rows_final}} flujos. En CICIDS2017 se descarta {{cic.clean.removed_pct}} y quedan {{cic.clean.rows_final}} flujos con {{cic.clean.n_features}} variables (tras quitar {{cic.clean.constant}} columnas constantes).

::: {.figura-mediana}
![Flujos que se conservan y que se eliminan en cada paso de la limpieza.](figuras/embudo_limpieza.png)
:::

## Desbalance de clases

- **UNSW-NB15**: {{unsw.clean.normal_pct}} de los flujos limpios son normales y {{unsw.clean.attack_pct}} son ataques. Las familias más pequeñas son Worms ({{unsw.fam.worms}} flujos), Backdoor ({{unsw.fam.backdoor}}) y Analysis ({{unsw.fam.analysis}}).
- **CICIDS2017**: {{cic.clean.normal_pct}} son normales y {{cic.clean.attack_pct}} son ataques. Hay familias minúsculas: Heartbleed ({{cic.fam.heartbleed}} flujos), Web Attack con inyección SQL ({{cic.fam.web_attack_sql_injection}}) e Infiltration ({{cic.fam.infiltration}}). Con tan pocos flujos, cualquier tasa de detección por familia es muy inestable.

Por eso la partición se estratifica por tipo de ataque, y la accuracy no se usa como criterio de decisión.

# Diseño e implementación

## Arquitectura

::: {.figura-mediana}
![Arquitectura del prototipo, de los archivos crudos a la decisión.](figuras/arquitectura.png)
:::

| Módulo | Función |
|---|---|
| `config.py` | Rutas, constantes y fuentes de datos fijadas a una revisión con suma SHA256 |
| `download_data.py` | Descarga verificada; rechaza archivos con suma distinta |
| `preprocess.py` | Limpieza descrita en el capítulo 4 y reporte de cada paso |
| `data_loader.py` | Partición 70/15/15 estratificada y submuestreo estratificado |
| `features.py`, `models.py` | Filtro de correlación, codificación, modelos base y mejorados, Mix |
| `metrics.py` | Métricas, selección de umbrales, intervalos bootstrap y prueba pareada |
| `train.py` | Entrenamiento, búsqueda de hiperparámetros, elección del modelo |
| `evaluate.py`, `experiments.py` | Reportes, figuras y experimentos formales |
| `predict.py` | Clasifica un archivo de flujos o un flujo en JSON, con cualquiera de los tres umbrales |
| `app/demo_app.py` | Demostración visual en el navegador (Streamlit) |

## Hiperparámetros elegidos

La búsqueda de hiperparámetros se hizo una vez por dataset, con la semilla 42.

**UNSW-NB15**

{{>tabla_hiperparametros unsw}}

**CICIDS2017**

{{>tabla_hiperparametros cic}}

## Calidad del software

El repositorio incluye una suite de pruebas automáticas (con datos sintéticos que reproducen cada anomalía de los datasets), análisis estático de estilo y de tipos, y un flujo de integración continua en GitHub Actions que ejecuta todo en Python 3.10 y 3.13. Las dependencias y la reproducción completa están descritas en `README.md`.

# Resultados

Todas las cifras de este capítulo son del **conjunto de prueba**, que no se usó para ajustar nada. Las tablas se generan directamente de `reports/` para que no pueda haber diferencias de transcripción.

## UNSW-NB15: resultado principal

El modelo elegido en validación con el criterio de `AGENT.md` es **{{unsw.best}}**. Su desempeño en los tres puntos de operación:

| Punto de operación | Umbral | Recall | FPR | Precisión | Ataques no detectados | Falsas alarmas |
|---|---|---|---|---|---|---|
| Umbral 0.5 | {{unsw.thr.xgb_improved.default}} | {{unsw.m.xgb_improved.default.recall}} | {{unsw.m.xgb_improved.default.fpr}} | {{unsw.m.xgb_improved.default.precision}} | {{unsw.m.xgb_improved.default.fn}} | {{unsw.m.xgb_improved.default.fp}} |
| Mínimo FPR con Recall >= 0.95 | {{unsw.thr.xgb_improved.recall_target}} | {{unsw.m.xgb_improved.recall_target.recall}} | {{unsw.m.xgb_improved.recall_target.fpr}} | {{unsw.m.xgb_improved.recall_target.precision}} | {{unsw.m.xgb_improved.recall_target.fn}} | {{unsw.m.xgb_improved.recall_target.fp}} |
| Máximo Recall con FPR <= 0.02 | {{unsw.thr.xgb_improved.fpr_budget}} | {{unsw.m.xgb_improved.fpr_budget.recall}} | {{unsw.m.xgb_improved.fpr_budget.fpr}} | {{unsw.m.xgb_improved.fpr_budget.precision}} | {{unsw.m.xgb_improved.fpr_budget.fn}} | {{unsw.m.xgb_improved.fpr_budget.fp}} |

Con umbral 0.5 la accuracy es {{unsw.m.xgb_improved.default.accuracy}} y el ROC-AUC {{unsw.m.xgb_improved.default.roc_auc}}. **Ningún modelo cumple a la vez Recall >= 0.95 y FPR <= 0.02 en ningún punto de operación.** Pasar del presupuesto de falsas alarmas al Recall 0.95 cuesta casi seis veces más falsas alarmas ({{unsw.m.xgb_improved.fpr_budget.fp}} frente a {{unsw.m.xgb_improved.recall_target.fp}}).

::: {.figura-mediana}
![Distribución de la probabilidad de ataque que asigna el modelo ganador en UNSW-NB15 y los tres umbrales.](figuras/distribucion_puntajes_unsw.png)
:::

La figura muestra por qué: los flujos normales y los ataques se **solapan** en la franja media de probabilidades. Mover el umbral no separa mejor los grupos; solo decide qué error se prefiere aceptar.

::: {.figura-mediana}
![Matrices de confusión del mismo modelo con los tres umbrales (UNSW-NB15, prueba).](figuras/matrices_confusion_unsw.png)
:::

### Comparación de los seis modelos

**Punto de operación: mínimo FPR con Recall >= 0.95**

{{>tabla_modelos unsw recall_target}}

**Punto de operación: máximo Recall con FPR <= 0.02**

{{>tabla_modelos unsw fpr_budget}}

### Dónde se concentran los errores

{{>tabla_familias unsw}}

Las familias Fuzzers y Analysis concentran los errores y son las que más caen cuando se exige un presupuesto estricto de falsas alarmas. Las demás se detectan casi siempre. Las variables más importantes para el modelo ganador son:

{{>tabla_importancias unsw}}

## CICIDS2017: resultado principal

El modelo elegido es **{{cic.best}}** (y también es el mejor con el presupuesto de falsas alarmas: {{cic.best_budget}}).

| Punto de operación | Recall | FPR | Ataques no detectados | Falsas alarmas |
|---|---|---|---|---|
| Umbral 0.5 | {{cic.m.xgb_improved.default.recall}} | {{cic.m.xgb_improved.default.fpr5}} | {{cic.m.xgb_improved.default.fn}} | {{cic.m.xgb_improved.default.fp}} |
| Mínimo FPR con Recall >= 0.95 | {{cic.m.xgb_improved.recall_target.recall}} | {{cic.m.xgb_improved.recall_target.fpr5}} | {{cic.m.xgb_improved.recall_target.fn}} | {{cic.m.xgb_improved.recall_target.fp}} |
| Máximo Recall con FPR <= 0.02 | {{cic.m.xgb_improved.fpr_budget.recall}} | {{cic.m.xgb_improved.fpr_budget.fpr5}} | {{cic.m.xgb_improved.fpr_budget.fn}} | {{cic.m.xgb_improved.fpr_budget.fp}} |

CICIDS2017 está **saturado**: con umbral 0.5 los seis modelos superan la meta, con ROC-AUC prácticamente igual a 1, y las diferencias entre modelos son de decenas de flujos sobre cientos de miles. Sirve poco para distinguir algoritmos.

::: advertencia
Aquí se ve que el criterio literal de `AGENT.md` es **degenerado** cuando el modelo es casi perfecto. "Mínimo FPR con Recall >= 0.95" empuja el Recall hasta 0.95 aunque el modelo pueda dar {{cic.m.xgb_improved.default.recall}}: las falsas alarmas bajan de {{cic.m.xgb_improved.default.fp}} a {{cic.m.xgb_improved.recall_target.fp}}, pero los ataques no detectados suben de {{cic.m.xgb_improved.default.fn}} a {{cic.m.xgb_improved.recall_target.fn}}.
:::

::: {.figura-mediana}
![Curva ROC del modelo ganador con los tres puntos de operación, en ambos datasets.](figuras/roc_puntos_operacion.png)
:::

{{>tabla_familias cic}}

Los puntos débiles son Bot, Slowhttptest y PortScan cuando se aplica el umbral del criterio literal. Heartbleed, Infiltration e inyección SQL tienen tan pocos flujos de prueba que sus cifras no permiten concluir nada.

## Repetición con cinco semillas

Se repitió la partición y el ajuste con cinco semillas. Los hiperparámetros de las versiones mejoradas son los de la búsqueda con la semilla 42 y no se volvieron a buscar, de modo que la desviación **subestima** la variación real de repetir también la búsqueda; además, los datos de ajuste de la semilla 42 se solapan con las pruebas de las otras semillas.

**UNSW-NB15, mínimo FPR con Recall >= 0.95** (media ± desviación estándar)

{{>tabla_semillas unsw recall_target}}

**UNSW-NB15, máximo Recall con FPR <= 0.02**

{{>tabla_semillas unsw fpr_budget}}

Con la regla de `AGENT.md`, {{unsw.best}} gana en {{unsw.s.wins.recall_target.xgb_improved}} de las {{unsw.s.n}} semillas y el Mix base en {{unsw.s.wins.recall_target.mix_baseline}}; con el presupuesto de falsas alarmas, XGBoost mejorado gana en {{unsw.s.wins.fpr_budget.xgb_improved}}. Reentrenar la semilla 42 reproduce las métricas guardadas con una diferencia máxima de {{unsw.s.repro}}.

**¿La versión mejorada supera a la base?** La tabla compara semilla por semilla (diferencias emparejadas):

{{>tabla_diferencias_semillas unsw}}

- **XGBoost**: la mejorada gana en {{unsw.sd.xgb.recall_target.fpr.better}} de {{unsw.sd.n}} semillas con la regla de `AGENT.md` (FPR menor en promedio {{unsw.sd.xgb.recall_target.fpr.mean}}) y en {{unsw.sd.xgb.fpr_budget.recall.better}} de {{unsw.sd.n}} con el presupuesto (Recall mayor en promedio {{unsw.sd.xgb.fpr_budget.recall.mean}}). La mejora es **pequeña pero consistente**.
- **Random Forest** y **Mix**: la mejora no es consistente; con umbral 0.5 el Random Forest mejorado incluso pierde Recall ({{unsw.sd.rf.default.recall.mean}} en promedio).

## Pruebas pareadas

Comparan dos modelos sobre las mismas filas de prueba (semilla 42), cada uno con su propio umbral, con IC de 95 % y p bilateral. Solo miden el ruido de muestreo de la prueba.

**UNSW-NB15**

{{>tabla_pareadas unsw}}

**CICIDS2017**

{{>tabla_pareadas cic}}

::: nota
Un intervalo de confianza de cada modelo por separado puede solaparse aunque exista una diferencia real, porque ignora que ambos modelos ven los mismos flujos. Por eso este informe corrige una lectura anterior, hecha solo con intervalos separados y una semilla, que concluía que la mejora no era demostrable: la prueba pareada y las cinco semillas muestran que para XGBoost sí lo es, aunque sea pequeña.
:::

## Particiones oficiales de UNSW-NB15

{{>tabla_oficial}}

Tres lecturas:

1. Con el uso directo de las particiones oficiales (protocolo A), XGBoost obtiene accuracy {{unsw.o.A_oficial_ingenuo.xgb_baseline.accuracy}} y **FPR {{unsw.o.A_oficial_ingenuo.xgb_baseline.fpr}}**, muy por debajo de lo que sale con una partición aleatoria. Una partición aleatoria mezcla los flujos de todo el dataset; la partición oficial de prueba parece distinta de la de entrenamiento. No se probó la causa, pero el resultado indica que las dos formas de evaluar no son intercambiables.
2. La depuración (protocolo B) baja aún más la accuracy ({{unsw.o.B_oficial_depurado.xgb_baseline.accuracy}}): al quitar duplicados desaparece parte de lo que el modelo acertaba por memoria.
3. La validación cruzada de 5 folds sobre el entrenamiento oficial, sin depurar (C1), da accuracy {{unsw.o.C_cv5_ingenuo.xgb_baseline.accuracy}} con {{unsw.o.C_cv5_ingenuo.xgb_baseline.leaked_pct}} de los flujos retenidos ya vistos en el ajuste; depurada (C2) baja a {{unsw.o.C_cv5_depurado.xgb_baseline.accuracy}}. **Los duplicados explican una parte de la distancia con el 0.97 de Alkhater (2026), pero no toda**: no se pudo reproducir esa cifra, y no se conoce el detalle de su preprocesamiento porque solo se verificó el resumen.

## Ablación de variables

**UNSW-NB15**

{{>tabla_ablacion unsw}}

**CICIDS2017**

{{>tabla_ablacion cic}}

En UNSW-NB15 quitar los tres grupos sospechosos (TTL, `state`, categóricas) casi no cambia nada: el FPR con Recall 0.95 va de {{unsw.a.completo.recall_target.fpr}} a valores entre {{unsw.a.sin_ttl_sttl_dttl_ct_state_ttl.recall_target.fpr}} y {{unsw.a.sin_categoricas_proto_service_state.recall_target.fpr}}. Es decir, **el rendimiento no depende de esas variables**. Esto no prueba que el modelo no use atajos, porque otras variables correlacionadas pueden ocupar su lugar. En CICIDS2017 quitar las variables que Engelen y otros (2021) señalan como atajos baja algo el Recall con umbral 0.5 (de {{cic.a.completo.default.recall}} a {{cic.a.sin_atajos_de_engelen_et_al_2021.default.recall}}) pero el ROC-AUC sigue en {{cic.a.sin_atajos_de_engelen_et_al_2021.default.roc_auc}}.

## Cuánto inflan los duplicados las métricas

Se entrena el mismo XGBoost base con tres protocolos de limpieza y se mide qué parte de la prueba tiene un vector idéntico en el entrenamiento.

**UNSW-NB15**

{{>tabla_fuga unsw}}

**CICIDS2017**

{{>tabla_fuga cic}}

::: {.figura-mediana}
![Efecto de no quitar duplicados en ambos datasets.](figuras/fuga_de_datos.png)
:::

En UNSW-NB15 el protocolo ingenuo deja {{unsw.l.naive.leaked_test_share_pct}} de la prueba ya vista en entrenamiento y sobrestima el Recall: {{unsw.l.naive.recall}} frente a {{unsw.l.full.recall}} con el protocolo completo. En CICIDS2017 el efecto es despreciable porque el dataset ya está saturado.

[[CIC_SEEDS]]

# Análisis crítico

## Qué algoritmo ofrece el mejor equilibrio

**XGBoost, en su versión mejorada**, en ambos datasets. La evidencia en UNSW-NB15:

- Frente a Random Forest mejorado, con la regla de `AGENT.md`, el FPR de XGBoost es menor en {{unsw.p.xgb_improved__rf_improved.recall_target.fpr.diff}} (IC 95 % [{{unsw.p.xgb_improved__rf_improved.recall_target.fpr.low}}, {{unsw.p.xgb_improved__rf_improved.recall_target.fpr.high}}]) con el mismo Recall; con el presupuesto de falsas alarmas, su Recall es mayor en {{unsw.p.xgb_improved__rf_improved.fpr_budget.recall.diff}}.
- El **Mix no mejora a XGBoost mejorado**: con la regla de `AGENT.md` tiene el mismo Recall ({{unsw.p.mix_improved__xgb_improved.recall_target.recall.diff}}) y un FPR mayor ({{unsw.p.mix_improved__xgb_improved.recall_target.fpr.diff}}). Combinar dos modelos que cometen errores parecidos no aporta.
- La ventaja se repite en las semillas: XGBoost mejorado es el modelo ganador en la mayoría de ellas (capítulo 7).

En CICIDS2017 las diferencias son diminutas por saturación, y con umbral 0.5 XGBoost mejorado también supera a Random Forest mejorado en Recall ({{cic.p.xgb_improved__rf_improved.default.recall.diff}}).

## Qué aportó la versión "mejorada"

La mejora combina filtro de correlación y búsqueda de hiperparámetros; **no se aislaron** una de otra, de modo que no se puede atribuir el efecto a una sola. Lo medido:

- Para **XGBoost** la mejora es pequeña pero consistente (capítulo 7): gana en todas las semillas en los dos puntos calibrados.
- Para **Random Forest** no ayuda y con umbral 0.5 perjudica. En CICIDS2017 la búsqueda, hecha sobre una muestra de 60 000 flujos, eligió una profundidad máxima de 12, que probablemente limita el modelo cuando se reentrena con más de un millón de flujos; es una explicación plausible, no probada.
- Para el **Mix** no hay mejora consistente.

La conclusión honesta es que el aporte distintivo del trabajo **no es un modelo mejorado que supere ampliamente a la base**, sino el protocolo de evaluación (sin fuga, con tres puntos de operación y con incertidumbre) y lo que ese protocolo permite descubrir.

## El criterio de decisión de AGENT.md es degenerado en los extremos

"Mínimo FPR con Recall >= 0.95" tiene dos fallos. Si el modelo es casi perfecto (CICIDS2017), empuja el Recall hacia abajo hasta 0.95 para ahorrar unas pocas falsas alarmas. Si el modelo no llega (UNSW-NB15), el criterio es inalcanzable junto con FPR <= 0.02. Se recomienda usar el criterio completo (Recall >= 0.95 **y** FPR <= 0.02) y reportar la curva ROC con los puntos marcados, no un solo umbral.

## Calidad de los datos y evaluación

- **Los duplicados importan según el dataset.** En UNSW-NB15 inflan el Recall medido en {{unsw.l.naive.recall}} frente a {{unsw.l.full.recall}}; en CICIDS2017 casi no cambian nada.
- **La forma de partir los datos cambia el resultado más que el algoritmo.** Entre la partición aleatoria y la oficial de UNSW-NB15 el FPR pasa de {{unsw.m.xgb_improved.default.fpr}} a {{unsw.o.A_oficial_ingenuo.xgb_baseline.fpr}} con el mismo tipo de modelo. Una cifra de desempeño sin su protocolo de evaluación no es comparable.
- **La accuracy agregada oculta los errores por familia.** Es la advertencia de Engelen y otros (2021) y se observa aquí: Fuzzers y Analysis en UNSW-NB15, Bot y Slowhttptest en CICIDS2017.

## Atajos

La ablación no encontró dependencia del rendimiento en las variables sospechosas de UNSW-NB15 (TTL, `state`) ni, de forma marcada, en las de CICIDS2017. Pero una ablación no demuestra la ausencia de atajos, porque variables correlacionadas pueden sustituir a las eliminadas.

## Amenazas a la validez

- **De construcción de los datos.** CICIDS2017 tiene errores de etiquetado y de construcción de flujos documentados (Engelen y otros, 2021; Lanvin y otros, 2023) que no se corrigieron aquí; UNSW-NB15 es un dataset sintético de laboratorio.
- **De la repetición.** Las cinco semillas reutilizan los hiperparámetros de la semilla 42; la búsqueda no se repitió.
- **De generalización.** Se evalúa sobre archivos de flujos de dos entornos de laboratorio, no sobre tráfico de una red real, y no se midió la resistencia a ataques que intenten evadir al modelo.
- **De los antecedentes.** De Alkhater (2026) y de Lanvin y otros (2023) solo se verificó el resumen.

# Conclusiones

1. **XGBoost mejorado** es el algoritmo con el mejor equilibrio entre detección y falsas alarmas en los dos datasets; el Mix no aporta una ventaja sobre él y Random Forest queda por debajo.
2. **En UNSW-NB15 ningún modelo cumple el objetivo del proyecto** (Recall >= 0.95 con FPR <= 0.02). Con Recall 0.95 el FPR ronda {{unsw.m.xgb_improved.recall_target.fpr_pct}}; con FPR <= 0.02 el Recall queda en {{unsw.m.xgb_improved.fpr_budget.recall_pct}}. Las clases se solapan, sobre todo en las familias Fuzzers y Analysis.
3. **CICIDS2017 está saturado** y sirve poco para distinguir algoritmos; todos cumplen el objetivo con umbral 0.5.
4. **La mejora de la versión mejorada es real pero pequeña y solo consistente en XGBoost**; un análisis con una sola semilla y comparación de intervalos sueltos la habría ocultado.
5. **El protocolo de evaluación pesa más que el algoritmo**: duplicados, tipo de partición y punto de operación cambian las cifras más que cambiar de modelo.
6. **El punto de operación es una decisión de negocio, no de aprendizaje automático**: cuántas falsas alarmas puede revisar un equipo determina el umbral.

# Limitaciones y trabajo futuro

## Limitaciones

- Búsqueda de hiperparámetros acotada (8 candidatos, muestra de 60 000 flujos) y no repetida por semilla.
- Una sola búsqueda por dataset; sin ablación que aísle el filtro de correlación del ajuste de hiperparámetros.
- Evaluación sobre archivos históricos, sin captura de tráfico en vivo ni medición de latencia.
- Dos datasets de laboratorio con errores documentados.

## Trabajo futuro

1. Repetir la búsqueda de hiperparámetros por semilla y aislar el efecto del filtro de correlación.
2. Probar sobre tráfico real o sobre un dataset más reciente y con mejor etiquetado.
3. Evaluar la robustez frente a ataques adversariales que intenten evadir el modelo.
4. Integrar la captura en vivo (por ejemplo con Scapy) y medir la latencia por flujo.
5. Añadir explicabilidad por flujo para que el analista entienda por qué se generó una alerta.

# Referencias

- Alkhater, N. (2026). A rigorous comparative study of supervised machine learning techniques for network anomaly detection: Empirical insights from the UNSW-NB15 dataset. *Computers*, 15(5), 285. https://doi.org/10.3390/computers15050285 (solo resumen verificado).
- Breiman, L. (2001). Random forests. *Machine Learning*, 45, 5-32. https://doi.org/10.1023/A:1010933404324
- Chen, T., y Guestrin, C. (2016). XGBoost: A scalable tree boosting system. *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 785-794. https://doi.org/10.1145/2939672.2939785
- Engelen, G., Rimmer, V., y Joosen, W. (2021). Troubleshooting an intrusion detection dataset: the CICIDS2017 case study. *2021 IEEE Security and Privacy Workshops (SPW)*, 7-12. https://doi.org/10.1109/SPW53761.2021.00009
- Lanvin, M., Gimenez, P.-F., Han, Y., Majorczyk, F., Mé, L., y Totel, E. (2023). Errors in the CICIDS2017 dataset and the significant differences in detection performances it makes. *Lecture Notes in Computer Science* (CRiSIS 2022), 18-33. https://doi.org/10.1007/978-3-031-31108-6_2 (solo resumen verificado).
- Moustafa, N., y Slay, J. (2015). UNSW-NB15: a comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set). *2015 Military Communications and Information Systems Conference (MilCIS)*, 1-6. https://doi.org/10.1109/MilCIS.2015.7348942
- Sharafaldin, I., Habibi Lashkari, A., y Ghorbani, A. A. (2018). Toward generating a new intrusion detection dataset and intrusion traffic characterization. *Proceedings of the 4th International Conference on Information Systems Security and Privacy (ICISSP)*, 108-116. https://doi.org/10.5220/0006639801080116

Tomadas del Entregable 1, sin reverificar para este informe: National Institute of Standards and Technology (2024), *The NIST Cybersecurity Framework (CSF) 2.0*; ICEX España Exportación e Inversiones (2025), *El mercado de la ciberseguridad en Colombia*; Centro Cibernético Policial, citado en Redacción Impacto TIC (2025).

# Anexos {.sin-salto}

## Anexo A: reproducción

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m src.download_data --dataset all
python -m src.preprocess --dataset all
python -m src.train --dataset unsw_nb15
python -m src.train --dataset cicids2017
python -m src.leakage_ablation --dataset unsw_nb15
python -m src.leakage_ablation --dataset cicids2017
python -m src.experiments --dataset unsw_nb15
python -m src.experiments --dataset cicids2017
python -m src.evaluate --dataset unsw_nb15
python -m src.evaluate --dataset cicids2017
python -m pytest
streamlit run app/demo_app.py
```

## Anexo B: correcciones al Entregable 1

Detectadas al contrastar el Entregable 1 con los datos; el documento ya se entregó, y estas correcciones quedan registradas aquí.

1. Las secciones 5.3 y 7.1 citan 2 540 044 registros de UNSW-NB15. Esa cifra corresponde al dataset completo (cuatro archivos CSV). Los archivos usados son las particiones oficiales de entrenamiento y prueba: {{unsw.clean.rows_raw}} flujos en total antes de limpiar.
2. La sección 5.3 enumera las categorías de ataque de UNSW-NB15 como "backdoor, DoS, exploits, análisis de reconocimiento, shellcode, desbordamiento de buffer, phishing, fuerza bruta y XSS". Las nueve categorías reales, según la página oficial y los datos, son Fuzzers, Analysis, Backdoor, DoS, Exploits, Generic, Reconnaissance, Shellcode y Worms.
3. Las secciones 4.2 y 8.2 proponen balanceo con SMOTE. No se aplicó: el desbalance de UNSW-NB15 es moderado y el umbral elegido en validación ya controla el compromiso entre falsas alarmas y detección. Si se aplicara, tendría que ser solo sobre el entrenamiento.
