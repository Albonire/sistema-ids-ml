# Parte D: Repaso para la sustentación

Esta parte es para estudiar en las horas previas: resume el proyecto en una página, repasa los resultados con su lectura en lenguaje llano, justifica cada decisión de diseño, anticipa las preguntas del jurado con respuestas modelo y cierra con un cuestionario de autoevaluación, un glosario, las fórmulas y los comandos.

::: nota
Todas las cifras de esta parte salen de los reportes del repositorio (`reports/`, `data/processed/`). Si el equipo vuelve a entrenar, los números de los PDF se regeneran solos.
:::

## D.1 El proyecto en una página

**Problema.** Los sistemas de detección de intrusiones (IDS) tradicionales funcionan por firmas: solo reconocen lo que ya conocen, y sus reglas rígidas generan muchas falsas alarmas que saturan a los analistas.

**Pregunta de investigación.** ¿Qué algoritmo de aprendizaje automático da el mejor equilibrio entre capacidad de detección y tasa de falsos positivos para un IDS basado en un dataset de tráfico de red?

**Enfoque.**

1. Dos datasets públicos: UNSW-NB15 (principal, el del Entregable 1) y CICIDS2017 (contraste). Se limpian y se reparten en 70 % entrenamiento, 15 % validación y 15 % prueba, de forma estratificada y con semilla fija.
2. Tres modelos (Random Forest, XGBoost y su mezcla por votación suave), cada uno en versión **base** (configuración típica de la literatura) y **mejorada** (filtro de correlación, hiperparámetros por validación cruzada de 5 pliegues y umbral elegido en validación). Son seis modelos por dataset.
3. Tres **puntos de operación** por modelo, con el umbral siempre elegido en validación: 0.5, mínimo FPR con Recall mayor o igual a 0.95, y máximo Recall con FPR menor o igual a 0.02.
4. Evaluación en la prueba con intervalos de confianza, pruebas pareadas, varias semillas, particiones oficiales de UNSW-NB15, ablación de variables y una ablación del efecto de los duplicados.

**Respuesta.** En ambos datasets el modelo elegido en validación es {{unsw.best}}. En UNSW-NB15 ningún modelo cumple a la vez Recall mayor o igual a 0.95 y FPR menor o igual a 0.02: con Recall de {{unsw.m.xgb_improved.recall_target.recall}} el FPR es {{unsw.m.xgb_improved.recall_target.fpr}}, y con FPR de {{unsw.m.xgb_improved.fpr_budget.fpr}} el Recall es {{unsw.m.xgb_improved.fpr_budget.recall}}. En CICIDS2017, todos los modelos superan el criterio con umbral 0.5, pero el dataset está saturado y discrimina poco entre algoritmos.

**Lo que aporta.** No es "un modelo mejor", es una **evaluación honesta**: sin duplicados entre entrenamiento y prueba, con umbrales elegidos fuera de la prueba, con la incertidumbre medida y con las hipótesis que no se confirmaron dichas con claridad.

**Lo que no se puede afirmar.** Que el modelo funcione igual en una red real (los datasets son de laboratorio), que los resultados sean estables frente a repetir la búsqueda de hiperparámetros (solo se repitió la partición), ni que la versión mejorada sea claramente superior a la base.

## D.2 Resultados y cómo leerlos

### Qué datos quedan tras la limpieza

{{>tabla_limpieza}}

**Lectura.** En UNSW-NB15 se elimina el {{unsw.clean.removed_pct}} de los flujos crudos, casi todo duplicados; en CICIDS2017 la proporción es mucho menor. Los contradictorios (el mismo vector con etiqueta normal y de ataque) son pocos pero se eliminan porque son ruido irreducible. UNSW-NB15 queda con {{unsw.clean.normal_pct}} de tráfico normal (desbalance moderado); CICIDS2017 con {{cic.clean.normal_pct}}.

![Dónde se van los flujos crudos en cada paso de la limpieza](figuras/embudo_limpieza.png)

### UNSW-NB15: los seis modelos en el punto Recall 0.95

{{>tabla_modelos unsw recall_target}}

**Lectura.** Con el umbral elegido para que el Recall llegue a 0.95, el FPR ronda el 12 al 14 por ciento: de cada diez flujos normales, más de uno se marca como ataque. El menor FPR lo tiene {{unsw.best}} ({{unsw.m.xgb_improved.recall_target.fpr}}). FN son los ataques no detectados y FP las falsas alarmas, ambos en conteos sobre {{unsw.split.test}} flujos de prueba.

Los otros dos puntos de operación del modelo elegido muestran el compromiso:

| Punto de operación | Recall | FPR | Ataques no detectados | Falsas alarmas |
|---|---|---|---|---|
| Umbral 0.5 | {{unsw.m.xgb_improved.default.recall}} | {{unsw.m.xgb_improved.default.fpr}} | {{unsw.m.xgb_improved.default.fn}} | {{unsw.m.xgb_improved.default.fp}} |
| Mínimo FPR con Recall mayor o igual a 0.95 | {{unsw.m.xgb_improved.recall_target.recall}} | {{unsw.m.xgb_improved.recall_target.fpr}} | {{unsw.m.xgb_improved.recall_target.fn}} | {{unsw.m.xgb_improved.recall_target.fp}} |
| Máximo Recall con FPR menor o igual a 0.02 | {{unsw.m.xgb_improved.fpr_budget.recall}} | {{unsw.m.xgb_improved.fpr_budget.fpr}} | {{unsw.m.xgb_improved.fpr_budget.fn}} | {{unsw.m.xgb_improved.fpr_budget.fp}} |

::: importante
Moverse de un punto a otro no cambia el modelo, cambia **qué error se acepta**. Es el mismo modelo con tres umbrales distintos. En UNSW-NB15 no existe un punto que cumpla ambas metas, porque las dos clases se solapan.
:::

![El mismo modelo con tres umbrales](figuras/matrices_confusion_unsw.png)

![Distribución de los puntajes: normales y ataques se solapan](figuras/distribucion_puntajes_unsw.png)

### CICIDS2017: casi perfecto con umbral 0.5

{{>tabla_modelos cic default}}

**Lectura.** Aquí todos los modelos están cerca de la perfección: accuracy y ROC-AUC casi iguales entre sí. Las diferencias son de decenas de flujos sobre cientos de miles. Un dataset **saturado** no sirve para distinguir algoritmos: cualquiera acierta. Además, el modelo mejorado de Random Forest sale peor que el base en Recall ({{cic.m.rf_improved.default.recall}} frente a {{cic.m.rf_baseline.default.recall}}) porque la búsqueda de hiperparámetros, hecha con una muestra, eligió profundidad 12 y limitó al modelo cuando se entrena con millones de filas.

::: advertencia
La regla literal de `AGENT.md` es mala cuando los modelos son casi perfectos. Con ella, en CICIDS2017 el modelo elegido tiene Recall de {{cic.m.xgb_improved.recall_target.recall}}: sacrifica Recall (de {{cic.m.xgb_improved.default.recall}} con umbral 0.5) para bajar las falsas alarmas, y los ataques no detectados pasan de {{cic.m.xgb_improved.default.fn}} a {{cic.m.xgb_improved.recall_target.fn}}. Por eso el proyecto reporta tres puntos de operación y recomienda usar el criterio completo.
:::

![ROC del modelo ganador con los tres puntos de operación](figuras/roc_puntos_operacion.png)

### Repetir con varias semillas (UNSW-NB15)

{{>tabla_semillas unsw recall_target}}

**Lectura.** Cada celda es media ± desviación estándar sobre {{unsw.s.n}} semillas (cinco repartos distintos de los datos). Las desviaciones son pequeñas (del orden de unas milésimas en Recall y de medio punto en FPR): el resultado no depende de un reparto afortunado. La regla de `AGENT.md` eligió a {{unsw.best}} en {{unsw.s.wins.recall_target.xgb_improved}} de las {{unsw.s.n}} semillas.

::: advertencia
Esa desviación **subestima** la incertidumbre real: los hiperparámetros de las versiones mejoradas se buscaron una sola vez (con la semilla 42) y se reutilizaron en las demás semillas, y los datos con los que se ajustaron se solapan con las pruebas de las otras semillas. Repetir la búsqueda en cada semilla es un trabajo pendiente.
:::

### ¿La versión mejorada es mejor que la base? Pruebas pareadas

{{>tabla_pareadas unsw}}

**Lectura.** Cada fila compara dos modelos sobre las **mismas** filas de prueba, cada uno con su umbral. Entre corchetes va el intervalo de confianza al 95 % y `p` es el valor *p* bilateral. Hallazgos:

- La prueba pareada detecta diferencias **pequeñas pero reales** que los intervalos separados escondían. Por ejemplo, XGBoost mejorado frente a XGBoost base en el punto de Recall 0.95: diferencia de FPR de {{unsw.p.xgb_improved__xgb_baseline.recall_target.fpr.diff}} (p = {{unsw.p.xgb_improved__xgb_baseline.recall_target.fpr.p}}).
- Las diferencias son de **menos de un punto porcentual** en casi todos los casos: estadísticamente detectables, prácticamente modestas.
- En el Mix, y en varios pares de Random Forest, la mejora no es consistente: depende del punto de operación e incluso cambia de signo.
- XGBoost mejorado frente a Random Forest mejorado en el punto de Recall 0.95: diferencia de FPR de {{unsw.p.xgb_improved__rf_improved.recall_target.fpr.diff}} (p = {{unsw.p.xgb_improved__rf_improved.recall_target.fpr.p}}).

::: nota
El valor *p* no mide la importancia práctica: con muchas filas de prueba, hasta una diferencia diminuta sale "significativa". Hay que mirar siempre el **tamaño** de la diferencia, no solo el *p*.
:::

### Cuánto inflan los duplicados la evaluación

{{>tabla_fuga unsw}}

**Lectura.** Con el protocolo ingenuo (solo limpieza obligatoria), el {{unsw.l.naive.leaked_test_share_pct}} de la prueba son vectores que el modelo ya vio al entrenar. El Recall sale {{unsw.l.naive.recall}} frente a {{unsw.l.full.recall}} con el protocolo completo, y la accuracy {{unsw.l.naive.accuracy}} frente a {{unsw.l.full.accuracy}}: una evaluación ingenua **sobrestima la detección**. En CICIDS2017 el efecto es despreciable porque ya está saturado.

![Efecto de los duplicados en la evaluación](figuras/fuga_de_datos.png)

### Particiones oficiales de UNSW-NB15

{{>tabla_oficial}}

**Lectura.**

- **Protocolo A** (el habitual en la literatura): entrenar con la partición oficial de entrenamiento y probar con la oficial de prueba. XGBoost obtiene accuracy {{unsw.o.A_oficial_ingenuo.xgb_baseline.accuracy}} y FPR {{unsw.o.A_oficial_ingenuo.xgb_baseline.fpr}}: mucho peor que con la partición aleatoria del proyecto. Las particiones oficiales **no tienen la misma distribución**: hay un cambio de distribución entre ellas, y eso es otro motivo por el que no se pueden comparar cifras entre estudios que usan protocolos distintos.
- **Protocolos C** (validación cruzada de 5 pliegues sobre la partición de entrenamiento): sin depurar, XGBoost saca accuracy {{unsw.o.C_cv5_ingenuo.xgb_baseline.accuracy}}, con el {{unsw.o.C_cv5_ingenuo.xgb_baseline.leaked_pct}} de lo retenido repetido; depurada, {{unsw.o.C_cv5_depurado.xgb_baseline.accuracy}}.

::: importante
Hipótesis que **no se confirmó**: pensamos que los duplicados explicarían por sí solos la accuracy de 0.97 que reporta Alkhater (2026) con XGBoost. La validación cruzada ingenua sobre la partición oficial de entrenamiento da {{unsw.o.C_cv5_ingenuo.xgb_baseline.accuracy}}, no 0.97. Los duplicados explican **una parte** de la distancia entre una evaluación ingenua y una limpia, pero no podemos atribuirle ese 0.97 a un solo factor, porque no pudimos verificar el protocolo exacto de ese estudio (solo se tuvo acceso a su resumen).
:::

### ¿Dependen los resultados de variables sospechosas?

{{>tabla_ablacion unsw}}

**Lectura.** Quitar las variables de TTL (`sttl`, `dttl`, `ct_state_ttl`), `state` o las tres categóricas **casi no cambia** el rendimiento en UNSW-NB15. El modelo no *depende* de ellas: otras variables aportan la misma información. Pero esto no demuestra que el modelo no use atajos, solo que su rendimiento aguanta sin ese grupo.

{{>tabla_importancias unsw}}

**Lectura.** La variable más importante para XGBoost es `{{unsw.imp.1.name}}` (importancia {{unsw.imp.1.value}}). La importancia dice cuánto usa el modelo una variable, no que esa variable **cause** el ataque: puede reflejar cómo se generó el tráfico de laboratorio.

Para CICIDS2017, el mismo experimento:

{{>tabla_ablacion cic}}

**Lectura.** Quitar `Destination Port` o las seis variables que Engelen et al. (2021) señalaron como atajos baja un poco el Recall con umbral 0.5 y sube un poco el FPR, pero el modelo no se desploma. Es una caída modesta, no un colapso.

### Dónde falla el modelo: detección por familia (UNSW-NB15)

{{>tabla_familias unsw}}

**Lectura.** Las familias Worms, Backdoor, Reconnaissance, Generic, DoS y Exploits se detectan casi siempre. Los errores se concentran en **Fuzzers** (la familia con más flujos de las difíciles) y **Analysis**, que se parecen al tráfico normal: con el presupuesto de falsas alarmas del 2 % solo se detecta menos de la mitad de cada una. La última fila (`BENIGN`) es la tasa de falsas alarmas, no una detección.

::: advertencia
Las familias con pocos flujos de prueba (columna `Flujos de prueba`) tienen estimaciones muy inestables: un caso más o menos cambia mucho el porcentaje. En CICIDS2017 pasa con Heartbleed ({{cic.fam.heartbleed}} flujos en total) e Infiltration ({{cic.fam.infiltration}}): no se pueden sacar conclusiones fiables de ellas.
:::

## D.3 Decisiones de diseño y su justificación

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Dos datasets (UNSW-NB15 principal, CICIDS2017 contraste) | Solo uno | Un solo dataset puede tener rarezas propias; el segundo comprueba si las conclusiones se sostienen. CICIDS2017 resultó saturado, y eso también es un hallazgo |
| Tres modelos (RF, XGBoost y Mix) | Añadir SVM, redes neuronales, CART | La docente pidió pocos modelos y que el aporte fuera mejorarlos frente a los antecedentes. RF y XGBoost eran el núcleo del Entregable 1 |
| Versión base y mejorada del mismo modelo | Comparar solo modelos distintos | Permite responder con honestidad "¿la mejora sirvió?" sobre los mismos datos |
| Partición 70/15/15 estratificada por familia | Partición 70/30, o estratificar solo por clase binaria | Hace falta una validación para elegir umbrales sin tocar la prueba; estratificar por familia garantiza que las raras aparezcan en las tres particiones |
| Quitar duplicados **antes** de partir | Quitar después, o no quitar | Un duplicado repartido entre entrenamiento y prueba infla las métricas |
| Convertir a `float32` antes de deduplicar | Deduplicar en `float64` | Vectores casi idénticos pasan a serlo para el modelo; sin esto se filtraba una pequeña parte de la prueba |
| Juzgar duplicados y conflictos con la etiqueta binaria | Hacerlo con la familia de ataque | La tarea es binaria; con la familia se descartaban flujos válidos y desaparecían protocolos enteros |
| Umbral elegido en validación | Elegirlo en prueba o fijar 0.5 | La prueba no debe influir en ninguna decisión; 0.5 es arbitrario |
| Tres puntos de operación | Uno solo | La regla literal de `AGENT.md` es degenerada con modelos casi perfectos; el presupuesto de falsas alarmas la complementa |
| Métrica de búsqueda: precisión promedio | Accuracy | La accuracy premia no detectar ataques cuando hay pocos; la precisión promedio no depende del umbral |
| Búsqueda aleatoria con 8 candidatos sobre una muestra | Búsqueda en cuadrícula con todos los datos | Es suficientemente buena (Bergstra y Bengio, 2012) y cabe en el tiempo disponible. Es una limitación declarada |
| Filtro de correlación (se elimina la variable cuya correlación absoluta con una ya conservada supera 0.95) | Selección por importancia o PCA | Es simple, determinista, se ajusta solo con entrenamiento y mantiene variables interpretables |
| Sin escalado de variables | `StandardScaler` | Los árboles comparan con umbrales y el orden no cambia al escalar |
| Intervalos bootstrap y prueba pareada | Solo la media | Sin incertidumbre no se puede saber si una diferencia es real |
| Varias semillas | Una sola | Comprueba que el resultado no depende de un reparto afortunado |
| Descarga verificada por SHA256 desde un espejo con revisión fija | Descarga manual | Reproducibilidad: todos obtienen los mismos bytes |

## D.4 Preguntas probables de la sustentación

Cada respuesta es un **modelo**: adáptenla con sus palabras. Los números salen de los reportes; si el jurado pide una cifra, cítenla del cuadro correspondiente de la sección D.2.

### Problema y justificación

**P1. ¿Qué problema resuelve el proyecto y por qué importa?**

Un IDS vigila el tráfico de red para detectar ataques. Los tradicionales comparan contra firmas conocidas: no ven lo nuevo (amenazas de día cero) y sus reglas rígidas marcan como sospechoso tráfico legítimo, lo que llena de falsas alarmas a los analistas. El proyecto estudia si el aprendizaje automático puede detectar ataques con menos falsas alarmas y compara algoritmos de forma rigurosa.

**P2. ¿Cuál es la pregunta de investigación y qué responden?**

"¿Qué algoritmo da el mejor equilibrio entre capacidad de detección y tasa de falsos positivos?". Respuesta: entre los comparados, XGBoost (versión mejorada) es el que ofrece el mejor equilibrio en ambos datasets según la regla de validación, y el Mix no aporta una ventaja demostrable. Pero la respuesta más importante es que **el punto de operación pesa más que el algoritmo**: en UNSW-NB15 ningún algoritmo logra Recall de 0.95 con FPR de 0.02.

**P3. ¿Qué es un falso positivo y por qué es la métrica central?**

Es tráfico normal marcado como ataque. Cada uno cuesta tiempo de un analista. Si son demasiados, los analistas dejan de creer en las alertas y se les escapan las reales (fatiga por alertas). Por eso no basta con detectar casi todos los ataques: hay que hacerlo con pocas falsas alarmas. Con el presupuesto de 0.02, un millón de flujos normales produciría unas veinte mil falsas alarmas (cuenta ilustrativa).

**P4. ¿Dónde encaja esto en la seguridad informática?**

El Entregable 1 lo ubica en la función **Detectar** del NIST Cybersecurity Framework 2.0: un IDS complementa firewalls, endurecimiento y gestión de vulnerabilidades, no los reemplaza. Su salida (normal o ataque) alimenta procesos de respuesta, como alertas o un SIEM.

**P5. ¿Por qué no capturaron tráfico en vivo?**

Porque el alcance acordado en el Entregable 1 es offline: se usan registros históricos de flujos de datasets públicos. La integración con captura en vivo se planteó como trabajo futuro. Un IDS en vivo exigiría además lidiar con latencia, cifrado y cambios en el tráfico, que aquí no se evalúan.

**P6. ¿Qué es un flujo de red?**

Un resumen estadístico de una conexión entre dos equipos: duración, paquetes y bytes en cada sentido, tiempos entre paquetes, banderas TCP, etc. No contiene la carga útil de los paquetes. Los archivos usados no traen direcciones IP; cada fila son estadísticas de un flujo.

### Datos y limpieza

**P7. ¿Por qué esos dos datasets?**

UNSW-NB15 es el declarado como principal en el Entregable 1: nueve familias de ataque modernas y variables categóricas (`proto`, `service`, `state`). CICIDS2017 es muy citado y sirve de contraste. Usar dos permite ver si las conclusiones se sostienen, y de hecho se comportan muy distinto: uno resulta difícil y el otro saturado.

**P8. En UNSW-NB15 se elimina más de un 40 %. ¿No es perder datos?**

Se pierden filas **redundantes**, no información: casi todo son copias exactas de otro flujo. Conservarlas haría que una copia cayera en entrenamiento y otra en prueba, y el modelo "acertara" por memoria. La ablación lo mide: con el protocolo ingenuo el {{unsw.l.naive.leaked_test_share_pct}} de la prueba son vectores ya vistos, y el Recall se sobrestima ({{unsw.l.naive.recall}} frente a {{unsw.l.full.recall}}).

**P9. ¿Qué es un vector contradictorio y por qué se descarta?**

Es el mismo conjunto de valores de variables con etiqueta normal en una fila y ataque en otra. Ningún modelo puede acertar ambas, así que son ruido irreducible. Se descartan **todas** sus filas. Son pocos (ver tabla de limpieza). Se juzgan con la etiqueta binaria, no con la familia, porque la tarea es binaria.

**P10. ¿Por qué convertir a `float32` antes de deduplicar?**

Porque dos filas que solo difieren por debajo de la precisión de `float32` son el mismo vector para el modelo. Si se deduplicara antes en `float64`, ambas sobrevivirían y una podría caer en entrenamiento y otra en prueba. Se descubrió con la ablación de duplicados, se corrigió y tiene una prueba automática.

**P11. El Entregable 1 decía 2540044 registros de UNSW-NB15 y ustedes usan {{unsw.clean.rows_raw}}. ¿Por qué?**

Porque esa cifra del Entregable 1 corresponde al dataset **completo** (cuatro archivos CSV). Los archivos que usa el proyecto son las particiones oficiales de entrenamiento y de prueba, que suman {{unsw.clean.rows_raw}} flujos antes de limpiar. Es un error de descripción del Entregable 1 que se corrige en el informe final; no afecta a los resultados.

**P12. ¿Por qué unir las particiones oficiales y volver a repartirlas?**

Para tener una partición propia de 70/15/15 con validación, estratificada por familia y con semilla. Además se evaluó el protocolo oficial por separado, y resulta mucho más difícil (accuracy {{unsw.o.A_oficial_ingenuo.xgb_baseline.accuracy}} con XGBoost y FPR {{unsw.o.A_oficial_ingenuo.xgb_baseline.fpr}}), lo que indica un cambio de distribución entre las dos particiones oficiales.

**P13. ¿Qué problemas conocidos tiene CICIDS2017?**

Engelen, Rimmer y Joosen (2021) documentan errores de generación de tráfico, construcción de flujos, extracción de variables y etiquetado: más del 20 % de las trazas se reconstruyen o reetiquetan al corregirlos, y los llamados "apéndices TCP" son el 25.9 % del dataset. Lanvin et al. (2023) describen fallos de etiquetado y captura. Este proyecto **no** corrige esos errores (exigiría reprocesar las capturas) y lo declara como amenaza a la validez.

**P14. ¿Por qué estratificar por familia de ataque?**

Porque se analiza la detección por familia. Una familia con pocos flujos podría caer entera en entrenamiento (y no se podría evaluar) o entera en prueba (y el modelo nunca la vería). Estratificar reparte cada familia en las tres particiones.

### Modelos

**P15. ¿Por qué Random Forest y XGBoost?**

Son el núcleo obligatorio del Entregable 1 y son la referencia en datos tabulares como estos. Además, la docente pidió pocos modelos y que el aporte fuera mejorarlos frente a lo reportado. Son árboles: rápidos de entrenar, no necesitan escalado, manejan relaciones no lineales y dan importancia de variables.

**P16. ¿Cómo funciona un Random Forest?**

Entrena muchos árboles de decisión, cada uno con una muestra aleatoria con reemplazo de los flujos (bagging) y con un subconjunto aleatorio de variables en cada división. Para clasificar, los árboles votan (o promedian probabilidades). Como cada árbol se equivoca de forma distinta, el promedio es más estable que un árbol solo (Breiman, 2001).

**P17. ¿Cómo funciona XGBoost y en qué se diferencia?**

Construye los árboles **en secuencia**: cada árbol nuevo corrige los errores de la suma de los anteriores (descenso de gradiente sobre la función de pérdida), con una tasa de aprendizaje que reduce el aporte de cada árbol y regularización para no sobreajustar (Chen y Guestrin, 2016). En Random Forest los árboles son independientes y se promedian; en XGBoost son dependientes y se suman.

**P18. ¿Qué es el Mix y por qué promedia probabilidades?**

Es un conjunto de votación suave: promedia la probabilidad de ataque de Random Forest y de XGBoost. Se promedian probabilidades y no votos para conservar la información de qué tan seguro está cada modelo y poder elegir un umbral. No se reentrena: usa los dos modelos ya ajustados.

**P19. ¿Qué significa exactamente "versión mejorada"?**

Tres cosas respecto a la base (la configuración del Entregable 1): (1) un filtro de correlación que quita variables redundantes, (2) hiperparámetros elegidos por búsqueda aleatoria con validación cruzada de 5 pliegues, y (3) el umbral elegido en validación en vez de fijarlo en 0.5. El tercer punto aplica a **todos** los modelos en la comparación de los tres puntos de operación.

**P20. ¿Por qué no usaron aprendizaje profundo?**

Porque en datos tabulares los modelos de árboles son competitivos y mucho más baratos, y la docente pidió acotar el alcance. Además, el Entregable 1 dejó las redes profundas como complementarias "sujetas a la disponibilidad de tiempo y cómputo". No se probaron en este proyecto, así que no se puede afirmar que sean peores; solo que no se evaluaron.

**P21. AGENT.md mencionaba SVM, MLP y CART. ¿Dónde están?**

Se dejaron fuera de alcance por indicación de la docente (pocos modelos, mejorados). Es una decisión de alcance, no un olvido, y está documentada en `AGENT.md`. El SVM, además, tiene un costo alto en datasets masivos, como anticipaba el propio documento.

**P22. El Entregable 1 proponía SMOTE. ¿Por qué no lo usaron?**

El desbalance de UNSW-NB15 es moderado ({{unsw.clean.normal_pct}} normal) y el umbral elegido en validación ya controla el compromiso entre detección y falsas alarmas. Si se aplicara SMOTE tendría que hacerse solo sobre el entrenamiento, nunca antes de partir, porque contaminaría la prueba con muestras sintéticas.

**P23. ¿Qué hace el filtro de correlación y por qué 0.95?**

Recorre las variables en orden y descarta la que tiene correlación absoluta mayor que 0.95 con alguna ya conservada, porque aporta información casi idéntica. En UNSW-NB15 descarta {{unsw.filter.dropped}} variables y en CICIDS2017 {{cic.filter.dropped}}. El 0.95 es un valor convencional; no se afinó. Se ajusta solo con el entrenamiento.

**P24. ¿Por qué no hay escalado de variables?**

Los árboles dividen con umbrales sobre una variable a la vez; escalar no cambia el orden de los valores, así que no cambia el modelo. El escalado sí sería necesario para SVM o redes neuronales.

### Métricas y umbrales

**P25. ¿Por qué la accuracy no basta?**

Porque con clases desbalanceadas un modelo que dijera siempre "normal" tendría una accuracy alta sin detectar nada. Por eso se reportan Recall (qué fracción de los ataques se detecta), FPR (qué fracción del tráfico normal se marca) y precisión, y se mira cada familia.

**P26. ¿En qué se diferencian FPR y precisión?**

El FPR es falsas alarmas entre **todo el tráfico normal**: FP / (FP + TN). La precisión es aciertos entre **todo lo que se alertó**: VP / (VP + FP). Dependen de cuánto tráfico normal hay: con muchísimo tráfico normal, un FPR pequeño puede seguir produciendo muchas alertas falsas frente a las reales.

**P27. ¿Qué es el umbral y por qué hay tres puntos de operación?**

El modelo da una probabilidad de ataque; el umbral es el valor a partir del cual se declara ataque. Subirlo reduce falsas alarmas pero pierde ataques; bajarlo hace lo contrario. No hay un umbral "correcto": depende de qué error se tolera. Se reportan el 0.5 (el habitual), el que busca el mínimo FPR con Recall 0.95 (la regla de `AGENT.md`) y el que busca el máximo Recall con FPR 0.02 (un presupuesto de falsas alarmas).

**P28. ¿Por qué se elige el umbral en validación y no en prueba?**

Porque el umbral es una decisión optimizada con datos. Si se optimiza con la prueba, el resultado es optimista. Con el umbral fijado en validación, la prueba mide cómo se comporta esa decisión en datos nuevos. Consecuencia visible: el FPR de prueba puede quedar apenas por encima del presupuesto ({{unsw.m.xgb_improved.fpr_budget.fpr}} frente a 0.02) y se reporta así.

**P29. ¿Qué es ROC-AUC y qué es PR-AUC?**

La curva ROC grafica Recall contra FPR para todos los umbrales; el AUC resume el área bajo ella (1 es perfecto, 0.5 es azar). La curva de precisión-recall grafica precisión contra Recall; su área (PR-AUC o precisión promedio) es más sensible cuando hay pocos ataques. Ninguna depende de un umbral concreto (Fawcett, 2006).

**P30. ¿Qué significa que la regla de AGENT.md sea "degenerada"?**

La regla dice "mínimo FPR con Recall mayor o igual a 0.95". Si el modelo es casi perfecto, bajar el Recall hasta 0.95 reduce un poco las falsas alarmas, así que la regla **empuja el Recall hacia abajo**. En CICIDS2017 los ataques no detectados pasan de {{cic.m.xgb_improved.default.fn}} a {{cic.m.xgb_improved.recall_target.fn}} por ganar muy pocas falsas alarmas. Por eso se recomienda usar el criterio completo (Recall mayor o igual a 0.95 **y** FPR menor o igual a 0.02) y mirar la curva ROC.

**P31. ¿Qué es el bootstrap y qué mide el intervalo de confianza?**

Remuestrear la prueba con reemplazo muchas veces para ver cuánto varía una métrica por el azar del muestreo. El intervalo al 95 % es el rango donde cae el 95 % de esas repeticiones. Mide solo el ruido de la prueba, no la variación por reentrenar con otra semilla (Efron, 1979).

**P32. ¿Qué significa el valor *p* en las pruebas pareadas?**

Es la probabilidad, bajo la hipótesis de que no hay diferencia, de ver una diferencia al menos tan grande por azar de muestreo. Un *p* pequeño indica que la diferencia no parece ser azar de esa prueba, no que sea importante en la práctica. Aquí las diferencias significativas son de menos de un punto porcentual.

**P33. ¿Por qué comparar de forma pareada?**

Porque los dos modelos se evalúan sobre los mismos flujos y suelen equivocarse en los mismos casos. La prueba pareada aprovecha esa correlación y detecta diferencias pequeñas que dos intervalos separados (aunque se solapen) no muestran. Que dos intervalos se solapen no prueba igualdad.

### Resultados

**P34. ¿Es bueno un 0.92 de accuracy?**

Sin contexto, no se puede decir. La accuracy engaña con clases desbalanceadas. Lo importante es el compromiso entre Recall y FPR, y ahí el resultado es mixto: con umbral 0.5 el Recall de {{unsw.m.xgb_improved.default.recall}} deja pasar un 10 % de los ataques, y para llegar a 0.95 el FPR sube a {{unsw.m.xgb_improved.recall_target.fpr}}. Para un IDS real eso sería demasiadas falsas alarmas.

**P35. ¿Por qué ningún modelo cumple el criterio en UNSW-NB15?**

Porque las clases se solapan: familias como Fuzzers y Analysis se parecen al tráfico normal en las variables disponibles (se ve en la distribución de puntajes). Cambiar de algoritmo no resuelve eso: la curva ROC de los seis modelos es casi la misma (ROC-AUC entre {{unsw.m.rf_improved.default.roc_auc}} y {{unsw.m.xgb_improved.default.roc_auc}}). Harían falta mejores variables, más datos de esas familias o información de contexto.

**P36. ¿Por qué la versión mejorada no gana claramente?**

Porque las diferencias son pequeñas: la prueba pareada detecta mejoras de menos de un punto porcentual en XGBoost, e inconsistentes en el Mix y en Random Forest. Los modelos base de árboles ya están cerca del máximo que permiten estos datos. En CICIDS2017, además, el dataset está saturado y en Random Forest la versión mejorada incluso resulta peor con umbral 0.5, por la búsqueda con muestra. Es un resultado honesto, no un fracaso.

**P37. CICIDS2017 da resultados casi perfectos. ¿Se puede confiar?**

Con cautela. Casi perfecto significa saturado: no discrimina entre algoritmos. Además, el dataset tiene errores documentados de construcción de flujos y etiquetado, y el modelo podría explotar atajos del laboratorio. La ablación de variables sospechosas ( `Destination Port` y las seis que señalan Engelen et al.) baja un poco el rendimiento pero no lo desploma. Por eso el principal es UNSW-NB15 y CICIDS2017 se usa como contraste.

**P38. ¿Qué modelo recomiendan?**

XGBoost, en su versión mejorada o base: bajo la misma restricción de Recall o de FPR iguala o mejora a Random Forest en este estudio, y el Mix no aporta una ventaja demostrable. Pero se debe decir con las salvedades: la mejora sobre la base es pequeña, el resultado es de laboratorio y el umbral debe escogerlo quien opera el sistema según cuántas falsas alarmas pueda atender.

**P39. ¿Qué pasó con las particiones oficiales y con la hipótesis sobre Alkhater (2026)?**

Se probó la hipótesis de que los duplicados explican la accuracy de 0.97 que ese estudio reporta con XGBoost. No se confirmó: con validación cruzada ingenua sobre la partición oficial de entrenamiento sale {{unsw.o.C_cv5_ingenuo.xgb_baseline.accuracy}}, y con datos depurados {{unsw.o.C_cv5_depurado.xgb_baseline.accuracy}}. Los duplicados explican parte de la diferencia, no todo. Además, solo se accedió al resumen de ese estudio, así que no se puede atribuir su cifra a un factor concreto.

**P40. ¿Qué detecta peor el modelo y por qué?**

Fuzzers y Analysis en UNSW-NB15. Se parecen al tráfico normal. Con el presupuesto de falsas alarmas del 2 %, se detecta menos de la mitad de cada una (ver tabla por familia). En CICIDS2017 las familias con muy pocos flujos (Heartbleed, Infiltration) no permiten conclusiones fiables.

### Críticas y limitaciones

**P41. ¿Está contaminado el conjunto de prueba?**

No por duplicados: se eliminan antes de partir y la ablación mide que la fracción de prueba repetida en el entrenamiento es cero con el protocolo del proyecto. Tampoco por decisiones: el filtro de correlación, los hiperparámetros, los umbrales y la elección del modelo ganador usan solo entrenamiento y validación. Una excepción documentada: en los experimentos con otras semillas se reutilizan los hiperparámetros hallados con la semilla 42, que se solapan con las pruebas de esas semillas (afecta a la desviación entre semillas, no al resultado principal).

**P42. ¿Por qué una sola semilla?**

La corrida principal usa la semilla 42, fija por reproducibilidad. Para el dataset principal (UNSW-NB15) se repitió el reparto y el ajuste con {{unsw.s.n}} semillas y las desviaciones son pequeñas. La limitación que sigue vigente es que **no se repitió la búsqueda de hiperparámetros** en cada semilla, así que esa desviación subestima la incertidumbre real.

**P43. ¿Es válido buscar hiperparámetros con una muestra de 60000 flujos?**

Es una decisión práctica por tiempo, con un costo conocido: puede elegir valores pensados para un conjunto pequeño. En CICIDS2017 eligió profundidad 12 para Random Forest y la versión mejorada salió peor que la base con umbral 0.5. Es una limitación declarada, no corregida.

**P44. ¿Los datasets representan una red real?**

No necesariamente. Son tráfico generado en laboratorio con ataques conocidos. Una red real tiene otro tráfico normal, otras proporciones y ataques nuevos. Los resultados dicen cuánto se puede lograr en estos datos, no cuánto se lograría en producción.

**P45. ¿Funcionaría en producción?**

No sin más trabajo. Faltaría capturar tráfico en vivo y calcular las mismas variables en tiempo real, reentrenar con tráfico propio de la organización, vigilar la deriva de los datos (el tráfico cambia con el tiempo) y fijar el umbral según la capacidad de respuesta del equipo. Con el FPR actual en UNSW-NB15 las alertas falsas serían abrumadoras.

**P46. ¿Un atacante podría evadir el modelo?**

Es una amenaza real y conocida: un atacante que conozca o pueda sondear el modelo puede modificar su tráfico para parecer normal (ataques adversarios). Este proyecto no evalúa robustez frente a evasión; sus resultados valen para tráfico de ataque "ingenuo" de los datasets. Es trabajo futuro.

**P47. La importancia de variables dice que `{{unsw.imp.1.name}}` es la más importante. ¿Eso es un atajo?**

La importancia indica cuánto usa el modelo la variable, no que cause el ataque. Puede reflejar el montaje del laboratorio. Se probó quitar variables de TTL y `state` y el rendimiento casi no cambia: otras variables correlacionadas toman su lugar. Eso no demuestra que no haya atajos; muestra que el rendimiento no depende de ese grupo.

**P48. ¿Qué harían con más tiempo?**

Repetir la búsqueda de hiperparámetros en cada semilla; validar en otro dataset o con tráfico propio; probar modelos de otra familia (redes, SVM) con el mismo protocolo; corregir los errores de etiquetado de CICIDS2017 reprocesando las capturas; evaluar robustez frente a evasión; y estudiar la deriva temporal.

### Código y reproducibilidad

**P49. ¿Cómo se reproduce todo?**

Con comandos deterministas: descarga verificada por SHA256 desde un espejo con revisión fija, limpieza, entrenamiento con `random_state=42`, evaluación y experimentos. Los comandos están en la sección D.8. Las pruebas automáticas corren con datos sintéticos y hay CI en GitHub (ruff, mypy y pytest en Python 3.10 y 3.13).

**P50. ¿Qué garantiza en el código que la prueba no se usa para decidir?**

La estructura: `make_splits` aparta la prueba primero; el umbral se elige con `choose_thresholds` que solo recibe puntajes de validación; el ganador lo elige `select_best` filtrando filas de validación; y la búsqueda de hiperparámetros ocurre dentro del entrenamiento. Las transformaciones que aprenden (filtro de correlación, codificador) están dentro de un `Pipeline`, que las ajusta solo con los datos de entrenamiento.

**P51. ¿Qué pasa si alguien cambia los datos descargados?**

La descarga verifica el SHA256 de cada archivo contra el esperado; si no coincide, borra el archivo y falla con un mensaje. Así nadie entrena con datos distintos sin saberlo.

**P52. ¿Por qué las pruebas usan datos sintéticos?**

Para que corran en segundos, en cualquier máquina y sin descargar nada. Cada rareza de los datos reales (infinitos, duplicados, contradictorios, categorías nuevas, clases raras) está reproducida a pequeña escala, y así un cambio que rompa una decisión de diseño falla de inmediato.

**P53. ¿Cómo se agregaría un tercer dataset o un cuarto modelo?**

Un dataset: crear otra instancia de `DatasetSource` en `config.py` con su URL, huellas y columnas categóricas, y adaptar su lectura en `preprocess.py` si su formato lo exige. Un modelo: añadir su fábrica en `models.py` y su espacio de búsqueda; el resto (umbrales, métricas, informes) trabaja con puntajes y no cambia.

### Ética y uso real

**P54. ¿Hay problemas de privacidad?**

Los archivos usados contienen estadísticas de flujos, sin direcciones IP ni carga útil de los paquetes, lo que reduce el riesgo. En una implementación real, analizar tráfico de usuarios plantea cuestiones de privacidad y de cumplimiento normativo que habría que resolver (qué se registra, cuánto tiempo, quién accede).

**P55. ¿Qué cuesta más, un falso negativo o un falso positivo?**

Depende. Un ataque no detectado puede ser un incidente grave; una falsa alarma cuesta tiempo y, acumulada, hace que los analistas ignoren las alertas. Por eso el proyecto no impone un solo umbral: muestra el compromiso y deja que quien opera el sistema lo fije según su riesgo y su capacidad de respuesta.

**P56. ¿Quién debería decidir el umbral en una organización?**

El equipo de seguridad, con la dirección del riesgo: es una decisión de negocio tanto como técnica. El modelo da la probabilidad; el umbral traduce cuántas falsas alarmas se pueden atender a cambio de cuántos ataques más se detectan.

**P57. ¿Qué riesgo hay en confiar ciegamente en el modelo?**

Que un buen resultado de laboratorio se tome por garantía en producción. Los propios datasets tienen errores documentados, el tráfico real cambia y un atacante puede adaptarse. Un IDS con aprendizaje automático debe usarse como una capa más de detección, con supervisión humana y reentrenamiento periódico.

## D.5 Cuestionario de autoevaluación

Responde primero sin mirar la clave. Los ejemplos con números son didácticos (no son datos del proyecto) y todos fueron verificados con Python.

**Q1.** Un conjunto tiene 1000 flujos, 990 normales y 10 ataques. Un modelo dice siempre "normal". ¿Cuál es su accuracy?

- (a) 0.50
- (b) 0.90
- (c) 0.99
- (d) 0.10

**Q2.** Con TP = 90, FN = 10, FP = 30 y TN = 870, ¿cuánto vale el Recall?

- (a) 0.75
- (b) 0.90
- (c) 0.96
- (d) 0.03

**Q3.** Con los mismos conteos, ¿cuánto vale el FPR?

- (a) 0.0333
- (b) 0.25
- (c) 0.10
- (d) 0.75

**Q4.** Con los mismos conteos, ¿cuánto vale la precisión?

- (a) 0.90
- (b) 0.75
- (c) 0.96
- (d) 0.97

**Q5.** Si se **sube** el umbral de decisión, normalmente:

- (a) Sube el Recall y sube el FPR
- (b) Baja el Recall y baja el FPR
- (c) Sube el Recall y baja el FPR
- (d) No cambia nada

**Q6.** Un nodo de un árbol tiene 3 flujos de ataque y 1 normal. Su impureza de Gini es:

- (a) 0.25
- (b) 0.375
- (c) 0.50
- (d) 0.75

**Q7.** Dos modelos dan probabilidades de ataque 0.9 y 0.5 para el mismo flujo. El Mix (votación suave) da:

- (a) 0.9
- (b) 0.5
- (c) 0.7
- (d) 1.4

**Q8.** Con el Mix y un umbral de 0.6, ese flujo se clasifica como:

- (a) Normal
- (b) Ataque
- (c) No se puede saber
- (d) Depende de la semilla

**Q9.** ¿Qué métrica **no** depende del umbral?

- (a) Recall
- (b) FPR
- (c) ROC-AUC
- (d) Precisión

**Q10.** ¿Por qué se eliminan los duplicados **antes** de partir los datos?

- (a) Para que el entrenamiento sea más rápido
- (b) Para que una copia no caiga en entrenamiento y otra en prueba
- (c) Porque los árboles no admiten duplicados
- (d) Porque lo exige scikit-learn

**Q11.** ¿Cuál de estas situaciones es **fuga de datos**?

- (a) Partir los datos con una semilla fija
- (b) Ajustar un escalador con todos los datos antes de partirlos
- (c) Usar validación cruzada
- (d) Guardar el modelo en disco

**Q12.** ¿Qué hace `stratify` en `train_test_split` aquí?

- (a) Ordena los datos por tiempo
- (b) Mantiene la proporción de cada familia de ataque en cada partición
- (c) Elimina las clases raras
- (d) Mezcla las particiones

**Q13.** ¿Cuál es la diferencia esencial entre Random Forest y XGBoost?

- (a) Random Forest usa redes neuronales
- (b) En Random Forest los árboles son independientes y se promedian; en XGBoost se construyen en secuencia, cada uno corrigiendo al anterior
- (c) XGBoost no usa árboles
- (d) Random Forest no puede clasificar

**Q14.** ¿Por qué los árboles no necesitan escalado de variables?

- (a) Porque ignoran los números
- (b) Porque dividen con umbrales y el orden de los valores no cambia al escalar
- (c) Porque se escalan automáticamente al clasificar
- (d) Porque usan solo variables categóricas

**Q15.** ¿Qué hace el `OneHotEncoder` con una categoría que nunca vio en el entrenamiento?

- (a) Falla
- (b) La agrupa en la categoría "infrecuente"
- (c) La borra del dato
- (d) Le asigna un valor al azar

**Q16.** El intervalo de confianza bootstrap de una métrica mide:

- (a) La variación por reentrenar con otra semilla
- (b) El ruido de muestreo de la prueba
- (c) El error del código
- (d) La importancia de las variables

**Q17.** Dos intervalos de confianza se solapan. ¿Qué se puede concluir?

- (a) Que los modelos son iguales
- (b) Que no se puede afirmar nada con una comparación pareada
- (c) Que no queda probada una diferencia con esa comparación débil; conviene una prueba pareada
- (d) Que uno de los modelos es mejor

**Q18.** Un valor *p* de 0.001 en una diferencia de FPR de 0.007 significa:

- (a) Que la diferencia es muy importante en la práctica
- (b) Que la diferencia difícilmente es azar de muestreo, pero es pequeña
- (c) Que el modelo es perfecto
- (d) Que hay fuga de datos

**Q19.** ¿Qué busca el punto de operación `recall_target`?

- (a) Máximo Recall con FPR menor o igual a 0.02
- (b) Mínimo FPR con Recall mayor o igual a 0.95
- (c) El umbral 0.5
- (d) Máxima accuracy

**Q20.** ¿Qué busca el punto de operación `fpr_budget`?

- (a) Máximo Recall con FPR menor o igual a 0.02
- (b) Mínimo FPR con Recall mayor o igual a 0.95
- (c) El umbral 0.5
- (d) Máxima precisión

**Q21.** ¿Por qué la regla literal de `AGENT.md` es "degenerada" con modelos casi perfectos?

- (a) Porque no se puede calcular
- (b) Porque empuja el Recall hacia abajo hasta 0.95 para ganar pocas falsas alarmas
- (c) Porque exige FPR cero
- (d) Porque ignora el Recall

**Q22.** ¿Dónde se elige el umbral de decisión?

- (a) En el conjunto de prueba
- (b) En el conjunto de validación
- (c) En el de entrenamiento
- (d) Se fija a mano sin datos

**Q23.** ¿Qué cantidad de registros tiene el dataset UNSW-NB15 **completo**, según la descripción oficial, y cuántos flujos usa el proyecto?

- (a) 257673 y 2540044
- (b) 2540044 y 257673
- (c) 175341 y 82332
- (d) Ambos son 2540044

**Q24.** ¿Para qué se calcula un hash por fila en la limpieza?

- (a) Para cifrar los datos
- (b) Para comparar rápido vectores completos al buscar duplicados y contradictorios
- (c) Para ordenar las filas
- (d) Para comprimir el archivo

**Q25.** ¿Qué mide la desviación estándar entre semillas del proyecto?

- (a) Todo el azar posible, incluida la búsqueda de hiperparámetros
- (b) La variación al repartir los datos y reentrenar, sin repetir la búsqueda de hiperparámetros
- (c) Solo el ruido de la prueba
- (d) El error de redondeo

**Q26.** ¿Qué comando es el recomendado para ejecutar las pruebas?

- (a) `pytest`
- (b) `python -m pytest`
- (c) `python tests`
- (d) `make test`

**Q27.** ¿Qué hace `select_threshold` con puntajes empatados?

- (a) Los separa al azar
- (b) Solo evalúa cortes donde el puntaje cambia, de modo que nunca separa un empate
- (c) Ignora los empates y falla
- (d) Los elimina

**Q28.** ¿Sobre qué datos se ajusta el filtro de correlación?

- (a) Todo el dataset
- (b) Solo los de entrenamiento
- (c) Solo los de prueba
- (d) Validación y prueba

**Q29.** ¿Qué es el aprendizaje por atajos (*shortcut learning*)?

- (a) Entrenar más rápido
- (b) Que el modelo use variables sin relación real con el ataque, que correlacionan con la etiqueta por cómo se generaron los datos
- (c) Usar menos árboles
- (d) Reducir el número de variables

**Q30.** En un caso didáctico, hay 1 ataque por cada 1000 flujos, el Recall es 0.95 y el FPR 0.02. ¿Cuál es aproximadamente la precisión?

- (a) 0.95
- (b) 0.98
- (c) 0.045
- (d) 0.50

### Clave de respuestas

| N.º | Respuesta | Explicación en una línea |
|---|---|---|
| Q1 | c | 990 de 1000 aciertos: 0.99, sin detectar ningún ataque |
| Q2 | b | 90 / (90 + 10) = 0.90 |
| Q3 | a | 30 / (30 + 870) = 0.0333 |
| Q4 | b | 90 / (90 + 30) = 0.75 |
| Q5 | b | Un umbral más alto marca menos flujos: menos falsas alarmas y menos ataques detectados |
| Q6 | b | 1 - (0.75 al cuadrado + 0.25 al cuadrado) = 0.375 |
| Q7 | c | (0.9 + 0.5) / 2 = 0.7 |
| Q8 | b | 0.7 es mayor o igual a 0.6 |
| Q9 | c | El AUC resume todos los umbrales |
| Q10 | b | Una copia en cada partición hace que el modelo acierte por memoria |
| Q11 | b | La estadística de la prueba influiría en la transformación |
| Q12 | b | Estratificar por familia reparte cada una en las tres particiones |
| Q13 | b | Bagging (independientes) frente a boosting (secuencial) |
| Q14 | b | Escalar no cambia el orden de los valores |
| Q15 | b | `handle_unknown="infrequent_if_exist"` |
| Q16 | b | Remuestrea la prueba; no reentrena |
| Q17 | c | El solapamiento no prueba igualdad; la comparación pareada es más sensible |
| Q18 | b | Significativo no es lo mismo que importante |
| Q19 | b | Es la regla literal de `AGENT.md` |
| Q20 | a | Un presupuesto fijo de falsas alarmas |
| Q21 | b | Bajar el Recall reduce un poco el FPR, así que la regla lo empuja hasta el mínimo permitido |
| Q22 | b | La prueba no puede influir en ninguna decisión |
| Q23 | b | El completo son cuatro CSV; el proyecto usa las particiones oficiales |
| Q24 | b | Es más rápido que comparar decenas de columnas fila contra fila |
| Q25 | b | No incluye repetir la búsqueda de hiperparámetros |
| Q26 | b | Evita usar un `pytest` de fuera del entorno virtual |
| Q27 | b | Los empates no se pueden separar con ningún umbral |
| Q28 | b | Está dentro del `Pipeline`, que ajusta solo con entrenamiento |
| Q29 | b | El modelo aprende pistas del laboratorio, no del ataque |
| Q30 | c | VP = 0.001 por 0.95; FP = 0.999 por 0.02; precisión de unos 4.5 % (el ejemplo de la tasa base) |

::: nota
Q30 es la idea más importante del cuestionario: con muy pocos ataques entre muchísimo tráfico normal, hasta un FPR pequeño produce más falsas alarmas que ataques reales. Por eso el FPR, y no solo el Recall, decide si un IDS es utilizable.
:::

## D.6 Glosario

| Término | Definición breve |
|---|---|
| Accuracy | Proporción de aciertos totales. Engaña con clases desbalanceadas |
| Ataque de día cero | Ataque nuevo, sin firma conocida |
| Atajo (*shortcut learning*) | Que el modelo use pistas sin relación real con el ataque, que correlacionan con la etiqueta por cómo se generaron los datos |
| Bagging | Entrenar modelos sobre muestras con reemplazo y promediarlos (base de Random Forest) |
| Bootstrap | Remuestrear con reemplazo para medir la variabilidad de una estadística |
| Búsqueda aleatoria | Probar combinaciones sorteadas de hiperparámetros en lugar de todas |
| CICFlowMeter | Herramienta que convierte capturas de red en flujos con variables estadísticas |
| CICIDS2017 | Dataset de tráfico con ataques (DoS, DDoS, PortScan, fuerza bruta, web, botnet, infiltración) |
| Clasificación binaria | Decidir entre dos clases: normal o ataque |
| Contradictorio (vector) | Mismo vector de variables con etiqueta normal en una fila y de ataque en otra |
| Correlación de Pearson | Medida de relación lineal entre dos variables, de -1 a 1 |
| CI (integración continua) | Ejecución automática de pruebas y revisiones en cada cambio del repositorio |
| Curva ROC | Recall contra FPR para todos los umbrales |
| Desbalance de clases | Una clase mucho más frecuente que otra |
| Deriva de datos | Cambio del tráfico con el tiempo que degrada un modelo entrenado antes |
| Duplicado | Fila idéntica a otra |
| Ensamble | Combinación de varios modelos |
| Estratificación | Repartir manteniendo la proporción de cada clase en cada partición |
| Falsa alarma (falso positivo) | Tráfico normal marcado como ataque |
| Falso negativo | Ataque no detectado |
| F1 | Media armónica de precisión y Recall |
| Flujo de red | Resumen estadístico de una conexión entre dos equipos |
| FPR | Falsos positivos sobre todo el tráfico normal: FP / (FP + TN) |
| Fuga de datos (*leakage*) | Información de la prueba que influye en el entrenamiento o en una decisión |
| Gini | Medida de impureza de un nodo de un árbol |
| Gradient boosting | Árboles construidos en secuencia, cada uno corrigiendo los errores de los anteriores |
| Hash | Resumen numérico corto de un dato, para compararlo rápido |
| Hiperparámetro | Ajuste del modelo que se fija antes de entrenar (profundidad, número de árboles) |
| IDS | Sistema de detección de intrusiones |
| Intervalo de confianza | Rango plausible de una métrica dado el ruido de muestreo |
| Matriz de confusión | Tabla de VP, FN, FP y VN |
| Mix | Promedio de probabilidades de Random Forest y XGBoost |
| NIST CSF | Marco de ciberseguridad del NIST; este proyecto se ubica en su función Detectar |
| One-hot | Codificar una categoría como columnas de ceros y unos |
| Overfitting | Memorizar el entrenamiento y generalizar mal |
| Parquet | Formato de archivo columnar y comprimido, usado para los datos limpios |
| Pipeline | Cadena de pasos que se ajustan juntos con los mismos datos |
| Precisión | Aciertos entre todo lo que se alertó: VP / (VP + FP) |
| PR-AUC | Área bajo la curva de precisión-recall |
| Prueba pareada | Comparar dos modelos sobre las mismas filas |
| Punto de operación | Combinación de Recall y FPR que resulta de elegir un umbral |
| Random Forest | Muchos árboles independientes que votan |
| Recall | Fracción de ataques detectados: VP / (VP + FN) |
| Reproducibilidad | Obtener los mismos resultados repitiendo los pasos |
| SHA256 | Huella criptográfica de un archivo, para comprobar que no cambió |
| Semilla (`random_state`) | Valor que fija el azar para poder repetir un experimento |
| Soft voting | Promediar probabilidades en lugar de contar votos |
| SOC | Centro de operaciones de seguridad, donde trabajan los analistas |
| Umbral | Probabilidad a partir de la cual se declara ataque |
| UNSW-NB15 | Dataset de tráfico con nueve familias de ataque, de la Universidad de Nueva Gales del Sur |
| Validación | Partición usada para ajustar y elegir umbrales sin tocar la prueba |
| Validación cruzada | Repetir entrenamiento y evaluación sobre varios pliegues |
| Valor *p* | Probabilidad, bajo "no hay diferencia", de ver una diferencia así por azar |
| XGBoost | Implementación eficiente de gradient boosting |

## D.7 Fórmulas

Con VP, FN, FP y VN los conteos de la matriz de confusión (el ataque es la clase positiva):

$$\mathrm{Accuracy}=\frac{VP+VN}{VP+VN+FP+FN}\qquad \text{Precisión}=\frac{VP}{VP+FP}$$

$$\mathrm{Recall}=\frac{VP}{VP+FN}\qquad \mathrm{FPR}=\frac{FP}{FP+VN}\qquad F_1=\frac{2\cdot \text{Precisión}\cdot \mathrm{Recall}}{\text{Precisión}+\mathrm{Recall}}$$

Impureza de Gini de un nodo con proporciones $p_k$ de cada clase:

$$G=1-\sum_k p_k^{2}$$

Votación suave (Mix) con $M$ modelos:

$$\hat p=\frac{1}{M}\sum_{m=1}^{M} p_m\qquad \text{ataque si } \hat p\ge \tau$$

Precisión según la tasa base (prevalencia $\pi$ de ataques):

$$\text{Precisión}=\frac{\pi\cdot \mathrm{Recall}}{\pi\cdot \mathrm{Recall}+(1-\pi)\cdot \mathrm{FPR}}$$

Reglas de los puntos de operación (umbral $\tau$ elegido en validación):

$$\tau_{\mathrm{recall}}=\arg\min_{\tau}\ \mathrm{FPR}(\tau)\ \ \text{sujeto a}\ \ \mathrm{Recall}(\tau)\ge 0.95$$

$$\tau_{\mathrm{FPR}}=\arg\max_{\tau}\ \mathrm{Recall}(\tau)\ \ \text{sujeto a}\ \ \mathrm{FPR}(\tau)\le 0.02$$

Intervalo bootstrap al 95 %: percentiles 2.5 y 97.5 de la métrica sobre las remuestras. Diferencia pareada: $d=m_A-m_B$ sobre las mismas filas, con valor $p$ bilateral igual al doble de la cola más pequeña de $d$ alrededor de cero.

## D.8 Comandos

```bash
# Entorno
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Datos
python -m src.download_data --dataset all [--force]
python -m src.preprocess --dataset all

# Entrenamiento y evaluación
python -m src.train --dataset unsw_nb15 [--n-iter 8] [--tune-sample 60000] [--cv-folds 5] [--rescore]
python -m src.train --dataset cicids2017
python -m src.evaluate --dataset unsw_nb15
python -m src.leakage_ablation --dataset unsw_nb15

# Inferencia
python -m src.predict --dataset unsw_nb15 --input flujos.csv [--output salida.csv] [--operating-point default|recall_target|fpr_budget]
python -m src.predict --dataset unsw_nb15 --json "$(cat docs/demo/flujo_ejemplo.json)"

# Experimentos formales
python -m src.experiments --dataset unsw_nb15 --task all
python -m src.experiments --dataset unsw_nb15 --task seeds [--seeds 42 1 2 3 4] [--recompute-primary]
python -m src.experiments --dataset unsw_nb15 --task pairwise|official|features|differences
python -m src.experiments_report --dataset unsw_nb15

# Demo
streamlit run app/demo_app.py
python -m src.demo --dataset cicids2017 --write-examples

# Calidad
python -m pytest
ruff check .
mypy

# Paquete de entrega (PDF)
python docs/entrega/make_figures.py
python docs/entrega/build.py
python docs/entrega/check_source.py docs/entrega/fuentes/guia_d_repaso.md
```

## D.9 Referencias verificadas

Se incluyen solo trabajos cuyos metadatos se comprobaron en Crossref (por DOI) o en la página de la revista, o que se verificaron al preparar el proyecto. Las citas del texto de la guía se refieren a estas entradas.

- Alkhater, N. (2026). A rigorous comparative study of supervised machine learning techniques for network anomaly detection: Empirical insights from the UNSW-NB15 dataset. *Computers*, 15(5), 285. https://doi.org/10.3390/computers15050285 (solo se pudo verificar el resumen, no el texto completo).
- Bergstra, J. y Bengio, Y. (2012). Random search for hyper-parameter optimization. *Journal of Machine Learning Research*, 13, 281-305. (Verificado en jmlr.org; la revista no usa DOI.)
- Breiman, L. (2001). Random forests. *Machine Learning*, 45, 5-32. https://doi.org/10.1023/A:1010933404324
- Chen, T. y Guestrin, C. (2016). XGBoost: a scalable tree boosting system. En *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, pp. 785-794. https://doi.org/10.1145/2939672.2939785
- Efron, B. (1979). Bootstrap methods: another look at the jackknife. *The Annals of Statistics*, 7(1), 1-26. https://doi.org/10.1214/aos/1176344552
- Engelen, G., Rimmer, V. y Joosen, W. (2021). Troubleshooting an intrusion detection dataset: the CICIDS2017 case study. En *2021 IEEE Security and Privacy Workshops (SPW)*, pp. 7-12. https://doi.org/10.1109/SPW53761.2021.00009
- Fawcett, T. (2006). An introduction to ROC analysis. *Pattern Recognition Letters*, 27, 861-874. https://doi.org/10.1016/j.patrec.2005.10.010
- Kaufman, S., Rosset, S., Perlich, C. y Stitelman, O. (2012). Leakage in data mining: formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data*, 6. https://doi.org/10.1145/2382577.2382579
- Lanvin, M., Gimenez, P.-F., Han, Y., Majorczyk, F., Mé, L. y Totel, E. (2023). Errors in the CICIDS2017 dataset and the significant differences in detection performances it makes. En *CRiSIS 2022*, Lecture Notes in Computer Science, Springer, pp. 18-33. HAL hal-03775466 (se verificó el resumen y la ficha; no se verificó un DOI).
- Moustafa, N. y Slay, J. (2015). UNSW-NB15: a comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set). En *2015 Military Communications and Information Systems Conference (MilCIS)*. https://doi.org/10.1109/MilCIS.2015.7348942
- Pedregosa, F. et al. (2011). Scikit-learn: machine learning in Python. *Journal of Machine Learning Research*, 12, 2825-2830. (Verificado en jmlr.org.)
- Sharafaldin, I., Habibi Lashkari, A. y Ghorbani, A. A. (2018). Toward generating a new intrusion detection dataset and intrusion traffic characterization. En *4th International Conference on Information Systems Security and Privacy (ICISSP)*. (Cita indicada por los autores del dataset.)

::: nota
El Entregable 1 también cita el marco NIST CSF 2.0 (NIST, 2024) y fuentes sobre el mercado de ciberseguridad en Colombia; esas citas no se reverificaron al preparar esta guía.
:::
