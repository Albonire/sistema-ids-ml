# Parte A: Teoría

Esta parte explica, en orden, todo lo que hay detrás del proyecto: primero la seguridad (qué se quiere detectar y por qué es difícil), luego el aprendizaje automático (cómo aprende un modelo y cómo saber si aprendió de verdad), después los dos algoritmos y su combinación, las métricas, la calidad de los datos, la búsqueda de hiperparámetros y por último los dos datasets. En cada sección el orden es el mismo: **intuición**, **definición precisa**, **cómo aparece en este proyecto**.

::: nota
Las cifras del proyecto que aparecen aquí vienen de los reportes y se actualizan solas al reconstruir el PDF. Los ejemplos con números inventados están en la Parte C y llevan la etiqueta "ejemplo didáctico". Las referencias entre paréntesis (autor y año) se listan completas en la Parte D.
:::

## A.1 Detección de intrusiones y seguridad de redes

### Qué es un IDS

Un **sistema de detección de intrusiones** (IDS, *intrusion detection system*) es un componente que observa actividad y avisa cuando algo parece un ataque. No bloquea nada por sí mismo: **detecta y alerta**. Lo que bloquea es otro componente (un firewall, un IPS) o una persona que reacciona a la alerta.

Hay dos grandes familias según **qué observan**:

| Tipo | Observa | Ejemplo de señal | Ventaja | Límite |
|---|---|---|---|---|
| **NIDS** (de red) | El tráfico que circula por la red | Un equipo envía miles de conexiones a puertos distintos (escaneo de puertos) | Ve toda la red desde un punto | No ve lo que ocurre dentro de un equipo; el tráfico cifrado limita lo que se puede inspeccionar |
| **HIDS** (de equipo) | Un equipo: archivos, procesos, registros | Un proceso modifica archivos del sistema | Ve detalle fino de un equipo | Hay que instalarlo en cada equipo |

**Este proyecto es un NIDS**: trabaja con descripciones del tráfico de red (flujos), no con lo que pasa dentro de los equipos.

### Firmas frente a anomalías

Hay dos formas de decidir que algo es un ataque:

- **Detección por firmas** (*signature-based*): se compara el tráfico con una lista de patrones conocidos de ataque. Es como un guardia con fotos de delincuentes buscados. Snort y Suricata en su configuración estándar funcionan así. Es muy precisa con lo que conoce, pero **no ve lo nuevo**.
- **Detección por anomalías**: se aprende cómo es lo "normal" y se avisa de lo que se desvía. Es como un guardia que conoce a los vecinos y se fija en el desconocido. Puede ver cosas nuevas, pero se equivoca más: un tráfico legítimo pero raro también se desvía.

El proyecto usa un enfoque **supervisado**: se entrena con ejemplos etiquetados como normal o ataque. Eso lo acerca a las firmas (aprende de ataques ya vistos) pero con una diferencia importante: en lugar de buscar una cadena exacta, el modelo aprende **combinaciones estadísticas** de muchas variables (duración, paquetes, bytes, tiempos) y, en principio, puede reconocer variantes de un ataque que no coinciden con ninguna regla exacta (el proyecto mide esto solo con familias ya conocidas, ver la advertencia siguiente).

::: advertencia
**No** se probó la detección de ataques completamente nuevos (*zero-day*). Los datasets solo contienen familias de ataque conocidas, y la evaluación mide qué tan bien se reconocen esas familias en flujos no vistos, no ataques que el modelo jamás conoció. Es un límite que hay que declarar: el proyecto motiva el aprendizaje automático por su capacidad de generalizar, pero no demuestra esa capacidad frente a amenazas desconocidas.
:::

### Falsos positivos y la fatiga del SOC

Un IDS puede equivocarse de dos maneras:

- **Falso negativo (FN)**: un ataque real pasa sin alerta. Es el error "peligroso": el atacante entra.
- **Falso positivo (FP)**: tráfico legítimo genera una alerta. Es el error "costoso": alguien tiene que revisar esa alerta.

En un **SOC** (*Security Operations Center*, centro de operaciones de seguridad) trabajan analistas que revisan las alertas. Si hay demasiadas falsas alarmas, ocurre la **fatiga de alertas**: se ignoran, se tardan en revisar, y entre ellas se pierde la real. Por eso la pregunta de investigación del proyecto no es "¿cuál detecta más?", sino "¿cuál da el mejor **equilibrio** entre detectar ataques y no generar falsas alarmas?". Todo el análisis de métricas (A.6) gira alrededor de ese compromiso.

### Dónde encaja en el marco NIST

El Entregable 1 ubica el proyecto en la función **Detectar** (*Detect*) del **NIST Cybersecurity Framework 2.0** (NIST, 2024), que establece la identificación oportuna de eventos de ciberseguridad como un pilar de la gestión de riesgo. El prototipo **complementa** los controles defensivos tradicionales (firewalls, endurecimiento de sistemas, gestión de vulnerabilidades) como una capa de detección inteligente, y su salida (normal o malicioso) está pensada para alimentar procesos posteriores como la generación de alertas o la integración con un SIEM. El Entregable 1 también aclara el alcance: detección con aprendizaje automático, **sin captura de tráfico en producción** ni componentes de pruebas de penetración.

### Qué es un flujo de red

El tráfico de una red está hecho de **paquetes** (pequeños bloques de datos). Mirar paquete por paquete es demasiado detallado y pesado. Por eso los datasets de este proyecto trabajan con **flujos**:

::: definicion
Un **flujo de red** agrupa los paquetes que pertenecen a la misma conversación: misma dirección de origen, de destino, mismos puertos y mismo protocolo, dentro de una ventana de tiempo. Un **flujo bidireccional** cuenta lo que va en ambos sentidos (origen a destino y destino a origen). Cada flujo se resume en una fila de números: es una "ficha" de la conversación.
:::

Herramientas como **CICFlowMeter** (la que generó CICIDS2017) leen capturas de paquetes y producen esas fichas. Un flujo termina cuando se cierra la conexión TCP (paquetes FIN) o cuando pasa un tiempo sin actividad (*timeout*). Algunas variables típicas:

| Grupo | Ejemplos | Qué cuenta |
|---|---|---|
| Duración | `dur`, `Flow Duration` | Cuánto dura la conversación |
| Volumen | `spkts`, `dpkts`, `sbytes`, `dbytes`; `Total Fwd Packets` | Cuántos paquetes y bytes en cada sentido |
| Tasas | `rate`, `sload`, `dload`; `Flow Bytes/s` | Velocidad de la transferencia |
| Tamaños | `smean`, `dmean`; `Packet Length Mean` | Tamaño medio de los paquetes |
| Tiempos | `sinpkt`, `sjit`; `Flow IAT Mean` | Intervalos entre paquetes y su variación |
| Banderas TCP | `SYN Flag Count`, `PSH Flag Count` | Cuántos paquetes con cada bandera de control |
| Servicio y estado | `proto`, `service`, `state` | Protocolo, aplicación y estado de la conexión |

(Los nombres a la izquierda son los de UNSW-NB15; los de la derecha, con espacios, son los de CICIDS2017.)

Un ataque deja **huellas estadísticas** en esas fichas. Un escaneo de puertos produce muchos flujos muy cortos con pocos paquetes; una inundación DoS produce muchos flujos con tasas altas; un ataque lento (*slowloris*) produce flujos largos con pocos paquetes. El modelo aprende a reconocer esas combinaciones.

::: nota
Las variables **no incluyen el contenido** de los paquetes (el texto de una página web, por ejemplo), solo estadísticas sobre ellos. Por eso el enfoque no depende de leer el contenido y el cifrado no lo bloquea por sí mismo (el proyecto no lo probó con tráfico cifrado), pero también por eso no puede detectar ataques que solo se distinguen por su contenido.
:::

::: {.figura-mediana}
![Arquitectura del prototipo: de los archivos crudos a la decisión](figuras/arquitectura.png)
:::

## A.2 Aprendizaje supervisado: aprender de ejemplos

### La idea

En el **aprendizaje supervisado** se le da al modelo muchos ejemplos con la respuesta correcta y se le pide que aprenda la regla. Cada ejemplo tiene:

- **Variables de entrada** $X$: la ficha del flujo (en UNSW-NB15, 42 variables; en CICIDS2017, {{cic.clean.n_features}} tras la limpieza).
- **Etiqueta** $y$: la respuesta que se quiere predecir.

El modelo aprende una función $f$ tal que $f(X) \approx y$ para los ejemplos de entrenamiento, **con la esperanza de que también funcione con ejemplos nuevos**.

### Binaria o multiclase

- **Clasificación binaria**: dos respuestas posibles. En el proyecto, `label` vale 0 (tráfico normal) o 1 (intrusión). **Es el objetivo del modelo.**
- **Clasificación multiclase**: más de dos respuestas. El dataset también conserva la familia de ataque en `attack_type` (por ejemplo, *Exploits*, *DoS*, *PortScan*), pero **no se entrena para predecirla**: se usa para repartir los datos de forma justa (estratificación) y para informar qué familias se detectan mejor.

La salida del modelo no es solo "ataque" o "normal": es una **probabilidad de ataque** entre 0 y 1. Convertirla en una decisión exige un **umbral** (A.6).

### Entrenar no es memorizar: generalización y sobreajuste

La pregunta clave es cuánto del aprendizaje **sirve con datos nuevos**.

::: definicion
**Generalización**: capacidad de un modelo de acertar con ejemplos que no vio al entrenar. **Sobreajuste** (*overfitting*): el modelo se aprende los ejemplos de entrenamiento (incluidos sus detalles casuales y su ruido) y falla con datos nuevos. Un modelo sobreajustado tiene un error de entrenamiento muy bajo y uno de prueba mucho más alto.
:::

Analogía exacta: un estudiante que memoriza las respuestas de un examen de práctica saca 100 en ese examen pero 40 en el oficial, porque nunca aprendió el tema. El ejemplo C.6 (la parte de la fuga de datos) lleva esa idea al extremo con un "modelo" que solo memoriza.

### Tres conjuntos con tres trabajos distintos

Para medir de verdad la generalización, los datos se reparten en tres partes que **no se mezclan**:

| Conjunto | Para qué se usa | Se mira | En este proyecto |
|---|---|---|---|
| **Entrenamiento** (*train*) | Ajustar el modelo: aprender las reglas | Constantemente | 70 %: {{unsw.split.train}} flujos en UNSW-NB15 |
| **Validación** (*validation*) | Tomar decisiones: elegir hiperparámetros, elegir los umbrales, elegir el mejor modelo | Muchas veces | 15 %: {{unsw.split.val}} flujos |
| **Prueba** (*test*) | Medir el resultado final y honesto | **Una sola vez, al final** | 15 %: {{unsw.split.test}} flujos |

::: importante
La regla de oro: **el conjunto de prueba no interviene en ninguna decisión**. Si se usara para elegir el umbral o el modelo, ya no sería "datos nuevos": el resultado quedaría optimista, porque se eligió justo lo que mejor le salía a esa prueba. Por eso en el proyecto los umbrales y la elección del modelo ganador se hacen en validación, y la prueba solo se lee al final.
:::

El reparto 70/15/15 se hace en dos pasos: primero se separa el 15 % de prueba, y del 85 % restante se separa un 15 % del total para validación (por eso se pide `val_size / (1 - test_size)` al segundo corte).

### Estratificación: que cada conjunto "se parezca" al total

Si los datos se reparten al azar sin cuidado, una familia rara puede quedar toda en un solo conjunto. CICIDS2017 tiene {{cic.fam.heartbleed}} flujos de la familia *Heartbleed* y {{cic.fam.infiltration}} de *Infiltration*: con un reparto descuidado, la prueba podría quedar sin ninguno y el modelo no se evaluaría en esa familia.

::: definicion
**Muestreo estratificado**: repartir los datos manteniendo la proporción de cada grupo en cada conjunto. El proyecto estratifica por **tipo de ataque** (`attack_type`), no solo por la etiqueta binaria, de modo que hasta las familias más raras aparecen en entrenamiento, validación y prueba.
:::

Aun así, familias con muy pocos flujos dan estimaciones muy inestables: con 2 o 3 flujos de prueba de una familia, acertar uno más o uno menos cambia la tasa de detección en 30 o 50 puntos. Por eso el proyecto reporta siempre cuántos flujos de prueba tiene cada familia.

### Validación cruzada: reutilizar los datos para evaluar

A veces se quiere evaluar un modelo (o una combinación de hiperparámetros) sin gastar un conjunto de validación fijo. La **validación cruzada de $k$ pliegues** (*k-fold cross-validation*) reparte los datos de entrenamiento en $k$ trozos y repite $k$ veces: entrena con $k-1$ trozos y evalúa con el trozo restante; al final promedia las $k$ evaluaciones.

```
Datos de entrenamiento, k = 5 pliegues

Ronda 1:  [ prueba ][ train  ][ train  ][ train  ][ train  ]
Ronda 2:  [ train  ][ prueba ][ train  ][ train  ][ train  ]
Ronda 3:  [ train  ][ train  ][ prueba ][ train  ][ train  ]
Ronda 4:  [ train  ][ train  ][ train  ][ prueba ][ train  ]
Ronda 5:  [ train  ][ train  ][ train  ][ train  ][ prueba ]
                      resultado = promedio de las 5 rondas
```

Ventajas: usa todos los datos y da una idea de cuánto varía el resultado. El Entregable 1 pide $k = 5$ para ajustar hiperparámetros, y es lo que hace el proyecto (A.8). Con la versión **estratificada** cada pliegue conserva la proporción de clases.

### Semillas y reproducibilidad

Muchos pasos usan azar: el reparto de datos, el sorteo de filas de cada árbol, el orden de pruebas de hiperparámetros. Una **semilla** (`random_state`) fija ese azar: con la misma semilla se obtiene exactamente el mismo resultado. El proyecto usa `random_state=42` en todo, de modo que cualquiera que repita los comandos obtiene las mismas cifras (se comprobó: al reentrenar la semilla 42 la diferencia con las métricas guardadas fue {{unsw.s.repro}}, es decir, error de redondeo).

La semilla también es una **fuente de variación que hay que medir**. Cambiar la semilla cambia el reparto y los modelos, y con ello cambian un poco los resultados. Por eso se repitió todo con 5 semillas (A.6 y A.8) y se reporta la media y la desviación estándar.

## A.3 Árboles de decisión

### La intuición: un cuestionario de sí o no

Un **árbol de decisión** es una cadena de preguntas de sí o no sobre las variables, que termina en una respuesta. Es lo que haría un analista con experiencia:

```
¿duración <= 0.35 s?
├── sí  → normal
└── no  → ¿paquetes > 32?
          ├── sí → ataque
          └── no → ...
```

Cada pregunta es una **división** (*split*) sobre una variable y un umbral; cada respuesta final es una **hoja**. Para clasificar un flujo se baja por el árbol contestando cada pregunta con sus valores hasta llegar a una hoja, que da la clase (o, mejor, la **fracción** de ejemplos de entrenamiento de cada clase que cayeron en esa hoja, que se usa como probabilidad).

### Cómo se elige cada pregunta: la impureza de Gini

El algoritmo no adivina las preguntas: prueba **todas** las divisiones posibles (cada variable, cada umbral intermedio) y se queda con la que deja los grupos resultantes **más puros**, es decir, más parecidos a una sola clase. Se mide con la **impureza de Gini**:

$$G = 1 - \sum_{c} p_c^2$$

donde $p_c$ es la fracción de ejemplos de la clase $c$ en el grupo. En clasificación binaria con una fracción $p$ de ataques es $G = 1 - p^2 - (1-p)^2$:

| Grupo | $p$ (fracción de ataques) | Gini $G$ | Lectura |
|---|---|---|---|
| Todos normales | 0 | 0 | Puro |
| Todos ataques | 1 | 0 | Puro |
| 90 % normales, 10 % ataques | 0.1 | 0.18 | Casi puro |
| Mitad y mitad | 0.5 | 0.5 | Lo más mezclado posible |

Para comparar divisiones se usa el Gini de los dos grupos resultantes ponderado por su tamaño. Gana la división con menor Gini ponderado. En C.2 se resuelve un ejemplo completo con todos los cortes candidatos.

Existe otra medida equivalente en espíritu, la **entropía**, $H = -\sum_c p_c \log_2 p_c$: también vale 0 en un grupo puro y es máxima cuando está mezclado. En la práctica dan árboles casi iguales. El proyecto usa el criterio por defecto de las librerías, Gini, en el Random Forest.

### Profundidad y sobreajuste

Un árbol puede seguir dividiendo hasta que cada hoja tenga **un solo ejemplo**. Eso memoriza el entrenamiento (sobreajuste). Se controla con **hiperparámetros**:

- `max_depth`: profundidad máxima (cuántas preguntas seguidas).
- `min_samples_leaf`: mínimo de ejemplos por hoja.

Un árbol **poco profundo** generaliza mejor pero puede quedarse corto (subajuste); uno **muy profundo** captura detalles de más. Un árbol solo suele ser inestable: un cambio pequeño en los datos puede cambiar mucho su forma. Esa inestabilidad es justo lo que los métodos de conjunto (A.4 y A.5) corrigen.

### Interpretabilidad

La gran ventaja de un árbol es que se **puede leer**: cada decisión es una ruta de preguntas que un humano entiende. Un Random Forest o un XGBoost combinan cientos de árboles y se pierde esa lectura directa. El proyecto cambia interpretabilidad por precisión; las variables más importantes (A.4 y A.5) dan una idea global, pero no explican un flujo concreto.

::: {.figura-pequena}
![Árbol de decisión de ejemplo sobre 8 flujos (C.2): un solo corte por duración separa las clases](figuras/ejemplo_arbol.png)
:::

## A.4 Random Forest

### La idea: muchos árboles distintos que votan

Un árbol solo es inestable. La idea de **Random Forest** (Breiman, 2001) es entrenar **muchos** árboles distintos entre sí y promediar sus respuestas. Analogía: en vez de preguntarle a un experto, se le pregunta a 100 expertos que vieron datos ligeramente distintos; los errores casuales de cada uno tienden a cancelarse.

Para que los árboles sean distintos se introduce azar de dos formas:

1. **Bagging** (*bootstrap aggregating*): cada árbol se entrena con una **muestra con reemplazo** del entrenamiento (sortea $n$ filas de $n$, con repeticiones). Cada árbol ve cerca del 63 % de las filas distintas y repite otras.
2. **Subconjunto aleatorio de variables**: en **cada división**, el árbol solo considera un grupo al azar de variables (no todas). Así evita que todos los árboles se parezcan por culpa de una variable dominante.

```
Entrenamiento (n filas)
   ├─ muestra 1 (con reemplazo) → árbol 1 ─┐
   ├─ muestra 2 (con reemplazo) → árbol 2 ─┤
   ├─ ...                                    ├→ promedio de probabilidades → probabilidad de ataque
   └─ muestra B (con reemplazo) → árbol B ─┘
```

### Cómo da una probabilidad

Cada árbol devuelve la fracción de ejemplos de ataque en la hoja donde cae el flujo. El bosque **promedia** esas fracciones sobre todos los árboles: es la probabilidad de ataque (así lo define `scikit-learn`: media de las probabilidades de los árboles). Esa probabilidad es la que se compara con el umbral.

### Hiperparámetros que aparecen en el proyecto

| Hiperparámetro | Qué controla | Base (Entregable 1) | Espacio de búsqueda de la versión mejorada |
|---|---|---|---|
| `n_estimators` | Número de árboles | 100 | 100, 200, 300 |
| `max_depth` | Profundidad máxima | sin límite | sin límite, 12, 20, 30 |
| `min_samples_leaf` | Mínimo de ejemplos por hoja | 1 | 1, 2, 4 |
| `max_features` | Variables consideradas en cada división | raíz cuadrada del total (por defecto) | `sqrt` o 0.3 (el 30 % de las variables) |

Más árboles estabilizan el resultado pero cuestan más tiempo; menos profundidad reduce el sobreajuste pero puede limitar el modelo. Los valores que eligió la búsqueda para cada dataset son:

{{>tabla_hiperparametros unsw}}

{{>tabla_hiperparametros cic}}

::: nota
En CICIDS2017 la búsqueda del Random Forest eligió una profundidad máxima limitada (12), y la versión mejorada resultó peor que la base con umbral 0.5 (Recall {{cic.m.rf_improved.default.recall}} frente a {{cic.m.rf_baseline.default.recall}}). Una explicación plausible, que **no se verificó con un experimento aparte**, es que un árbol limitado rinde bien con la muestra de ajuste (60 000 flujos) pero queda corto al entrenar con los 1.7 millones de flujos completos. Es una limitación del método de ajuste y no un error del código (se discute en A.8).
:::

### Importancia de variables

Un Random Forest permite medir qué variables usó más: la **importancia** de una variable es cuánto reduce la impureza, sumada sobre todas sus divisiones en todos los árboles. Sirve para tener una idea **global** de qué mira el modelo, pero tiene límites: favorece variables con muchos valores distintos y no dice nada sobre una decisión individual. En este proyecto la importancia que se reporta es la del XGBoost (A.5).

## A.5 Gradient boosting, XGBoost y el Mix

### La idea: árboles que corrigen a los anteriores

Random Forest entrena los árboles **en paralelo** e **independientes**. El **boosting** hace lo contrario: los entrena **en secuencia**, y cada árbol nuevo se dedica a **corregir los errores** de los anteriores.

Analogía: un estudiante resuelve un examen; un segundo revisa solo lo que el primero falló; un tercero revisa lo que aún queda mal, y así. La respuesta final es la suma de todos los aportes.

Formalmente, el modelo se construye como una suma:

$$F_m(x) = F_{m-1}(x) + \eta \cdot f_m(x)$$

donde $f_m$ es el árbol nuevo (un árbol pequeño y poco profundo), y $\eta$ (la **tasa de aprendizaje**, `learning_rate`) es un número pequeño que controla cuánto se deja corregir cada vez. El árbol $f_m$ se ajusta a la dirección en la que **más baja el error** del modelo actual (el gradiente de la función de pérdida, de ahí *gradient boosting*). Para clasificación binaria, la suma $F$ se convierte en probabilidad con la función logística:

$$P(\text{ataque}) = \frac{1}{1 + e^{-F(x)}}$$

### Qué agrega XGBoost

**XGBoost** (Chen y Guestrin, 2016) es una implementación muy eficiente de gradient boosting con árboles. Añade dos ideas importantes: usa información de segundo orden de la pérdida para decidir las divisiones, y **regulariza** el modelo (penaliza árboles demasiado complejos y pesos de hoja muy grandes) para que sobreajuste menos. En el proyecto se usa con `tree_method="hist"`: agrupa cada variable en intervalos (histogramas) para acelerar mucho el entrenamiento con millones de filas.

### Hiperparámetros que aparecen en el proyecto

| Hiperparámetro | Qué controla | Base (Entregable 1) | Espacio de búsqueda |
|---|---|---|---|
| `n_estimators` | Número de árboles (rondas de corrección) | 100 | 200, 400, 600 |
| `max_depth` | Profundidad de cada árbol | 5 | 4, 6, 8, 10 |
| `learning_rate` | Cuánto aporta cada árbol ($\eta$) | por defecto | 0.05, 0.1, 0.2 |
| `subsample` | Fracción de filas que ve cada árbol | por defecto | 0.7, 0.85, 1.0 |
| `colsample_bytree` | Fracción de variables que ve cada árbol | por defecto | 0.6, 0.8, 1.0 |
| `min_child_weight` | Peso mínimo en una hoja (evita hojas con muy pocos ejemplos) | por defecto | 1, 3, 5 |

Hay un compromiso clásico: **tasa de aprendizaje pequeña con más árboles** suele dar mejor resultado que una tasa grande con pocos, a costa de más tiempo. Por eso las búsquedas del proyecto prefieren `learning_rate` bajo y `n_estimators` alto (los valores elegidos están en las tablas de A.4).

La **importancia de variables** de XGBoost que reporta el proyecto es la **ganancia** (*gain*): cuánto mejora la función de pérdida, en promedio, cada vez que se divide por esa variable. Las más importantes del modelo ganador de UNSW-NB15 son:

{{>tabla_importancias unsw}}

::: advertencia
Importancia alta no significa causa. En UNSW-NB15, `state_INT`, `sttl` y `ct_state_ttl` pesan mucho; se sospechó que podían ser **atajos** (A.7) y se probó reentrenar sin ellas. Casi no cambió nada (A.7 y el informe final), lo que indica que el rendimiento no depende de esas variables concretas, aunque no prueba que otras variables correlacionadas no estén tomando su lugar.
:::

### Random Forest frente a XGBoost

| | Random Forest | XGBoost |
|---|---|---|
| Cómo combina árboles | En paralelo, independientes, promedio | En secuencia, cada uno corrige al anterior |
| Tipo de árbol | Profundos | Pequeños y poco profundos |
| Riesgo principal | Poco sobreajuste por promediar | Sobreajuste si hay demasiados árboles o tasa alta |
| Sensibilidad a hiperparámetros | Baja | Más alta |
| Velocidad en datos grandes | Buena | Muy buena con `hist` |

### El Mix: votación suave

El **Mix** combina el Random Forest y el XGBoost de la misma versión **promediando sus probabilidades de ataque**, flujo por flujo. Se llama **votación suave** (*soft voting*) porque se promedian las probabilidades, no los votos "ataque o normal" (eso sería votación dura). La idea es que los dos modelos se equivocan en flujos distintos y el promedio compensa. En el proyecto no se reentrena nada: el Mix usa los modelos ya ajustados, y su **propio umbral** se elige en validación sobre las probabilidades promediadas (se ve con números en C.4).

Un modelo de conjunto no garantiza ganar. El ejemplo C.4 muestra cuándo ayuda (cuando los dos discrepan) y cuándo no (cuando los dos fallan en el mismo flujo). En los resultados del proyecto, las diferencias entre el Mix y XGBoost solo son pequeñas y no van todas en el mismo sentido (se ven con las pruebas pareadas en el informe final): el Mix no es una mejora clara sobre XGBoost.

## A.6 Métricas: cómo medir un detector

### La matriz de confusión: el punto de partida

Todo parte de comparar, para cada flujo de prueba, lo que **es** con lo que el modelo **dijo**. Con "ataque" como clase positiva salen cuatro casos:

| | Modelo dice ataque | Modelo dice normal |
|---|---|---|
| **Es ataque** | **VP** (verdadero positivo): ataque detectado | **FN** (falso negativo): ataque que se escapó |
| **Es normal** | **FP** (falso positivo): falsa alarma | **VN** (verdadero negativo): normal bien clasificado |

En español se usan las siglas VP, FN, FP y VN; en inglés TP, FN, FP, TN (los reportes del proyecto usan estas últimas en las columnas `tp`, `fn`, `fp`, `tn`). **Todas las métricas son cocientes entre estos cuatro números.**

### Las métricas y cuándo sirve cada una

| Métrica | Fórmula | Pregunta que responde | Mira la fila de |
|---|---|---|---|
| **Recall** (sensibilidad, tasa de detección) | $\dfrac{VP}{VP + FN}$ | De todos los ataques reales, ¿cuántos detecté? | Ataques |
| **FPR** (tasa de falsos positivos) | $\dfrac{FP}{FP + VN}$ | De todo el tráfico normal, ¿cuánto marqué por error? | Normales |
| **Especificidad** | $\dfrac{VN}{FP + VN} = 1 - \text{FPR}$ | De todo el tráfico normal, ¿cuánto dejé pasar bien? | Normales |
| **Precisión** | $\dfrac{VP}{VP + FP}$ | Cuando suena una alarma, ¿qué tan seguro es que sea ataque? | Columna "dice ataque" |
| **F1** | $\dfrac{2 \cdot \text{Precisión} \cdot \text{Recall}}{\text{Precisión} + \text{Recall}}$ | Un solo número que equilibra precisión y recall | Ambas |
| **Accuracy** | $\dfrac{VP + VN}{\text{total}}$ | ¿Qué fracción de todo acerté? | Toda la matriz |

**Por qué el proyecto prioriza Recall y FPR.** El proyecto se pregunta por el equilibrio entre detectar ataques (Recall) y no dar falsas alarmas (FPR), y esos dos números se leen **cada uno en su propia fila**, de modo que no los distorsiona cuánto de cada clase haya. La **accuracy** mezcla todo y depende de la prevalencia: con pocos ataques, "decir siempre normal" tiene accuracy altísima (ejemplo en C.1). La **precisión** también depende de la prevalencia (C.5).

::: definicion
**Prevalencia**: la fracción de los flujos que son ataques. En UNSW-NB15 es {{unsw.clean.attack_pct}} y en CICIDS2017 {{cic.clean.attack_pct}} (tras la limpieza). En una red real suele ser mucho menor, y eso empeora la precisión (C.5).
:::

### Del puntaje a la decisión: el umbral

El modelo devuelve una probabilidad. Para decidir hay que fijar un **umbral**: si la probabilidad supera el umbral, se marca ataque. Subir el umbral hace al detector **más exigente**: detecta menos ataques (baja el Recall) pero da menos falsas alarmas (baja el FPR). Bajarlo hace lo contrario. **No hay umbral "correcto"**: cada uno es un compromiso distinto.

La figura muestra la distribución de las probabilidades que da el modelo ganador de UNSW-NB15 a los flujos normales (azul) y a los ataques (rojo), con tres umbrales. Donde las dos distribuciones se solapan, ningún umbral separa bien: cualquiera que se elija deja algunos errores.

::: {.figura-mediana}
![Probabilidad de ataque de los flujos normales y de los ataques en UNSW-NB15, con los tres umbrales del proyecto](figuras/distribucion_puntajes_unsw.png)
:::

### Los tres puntos de operación del proyecto

Un **punto de operación** es un umbral elegido con un criterio. El proyecto evalúa tres, y los tres umbrales se eligen **en validación**:

| Punto | Regla | Para qué sirve |
|---|---|---|
| **Umbral 0.5** | Fijo | Es lo que casi toda la literatura reporta; es la referencia |
| **Mínimo FPR con Recall >= 0.95** | Entre los umbrales que detectan al menos el 95 % de los ataques, el que menos falsas alarmas da | Es el criterio literal de `AGENT.md`: se elige el modelo con "mínimo FPR con Recall superior a un umbral" |
| **Máximo Recall con FPR <= 0.02** | Entre los umbrales con a lo sumo 2 % de falsas alarmas, el que más ataques detecta | Un SOC con capacidad limitada de revisar alertas: se fija el "presupuesto" de falsas alarmas |

El criterio de decisión del proyecto, en `AGENT.md`, menciona **las dos metas a la vez**: Recall >= 0.95 y FPR <= 0.02.

::: advertencia
El criterio literal "mínimo FPR con Recall >= 0.95" tiene un defecto cuando los modelos son casi perfectos: como lo que pide es **bajar el FPR todo lo posible mientras el Recall se mantenga sobre 0.95**, empuja el Recall hacia abajo hasta rozar 0.95 aunque el modelo podría dar 0.998. En CICIDS2017 eso cambia el Recall de {{cic.m.xgb_improved.default.recall}} (umbral 0.5) a {{cic.m.xgb_improved.recall_target.recall}} para bajar las falsas alarmas, y los ataques no detectados pasan de {{cic.m.xgb_improved.default.fn}} a {{cic.m.xgb_improved.recall_target.fn}}. Por eso el proyecto agrega el tercer punto y reporta los tres.
:::

### La aritmética de las falsas alarmas

Un FPR que "parece pequeño" puede ser mucho en la práctica: las falsas alarmas esperadas son $\text{FPR} \times$ (número de flujos normales). Con un millón de flujos normales, un FPR de 0.02 son 20 000 alertas. Además, la **precisión** depende de la prevalencia, no solo del FPR: el teorema de Bayes da

$$\text{precisión} = \frac{r \cdot \pi}{r \cdot \pi + f \cdot (1 - \pi)}$$

con $r$ el recall, $f$ el FPR y $\pi$ la prevalencia. Con el mismo detector (Recall 0.95, FPR 0.02), la precisión es 0.98 si la mitad del tráfico son ataques y apenas 0.32 si solo el 1 % lo es. La Parte C (C.5) lo resuelve con números, y la figura siguiente muestra las falsas alarmas esperadas por millón de flujos normales con los FPR reales del proyecto (suposición ilustrativa de un millón de flujos).

::: {.figura-mediana}
![Falsas alarmas esperadas por cada millón de flujos normales según el punto de operación](figuras/alarmas_por_millon.png)
:::

### Curva ROC y AUC

La **curva ROC** (*receiver operating characteristic*; Fawcett, 2006) resume el desempeño del modelo para **todos** los umbrales posibles: en el eje horizontal el FPR y en el vertical el Recall. Cada punto de la curva es un umbral. Un modelo inútil (que adivina al azar) traza la diagonal; uno perfecto pasa por la esquina superior izquierda (Recall 1 con FPR 0).

El **AUC** (*area under the curve*, área bajo la curva) es un número entre 0.5 y 1 que resume la curva. Tiene una interpretación concreta: **es la probabilidad de que el modelo asigne un puntaje mayor a un ataque elegido al azar que a un flujo normal elegido al azar**. Un AUC de 0.98 significa que en el 98 % de los pares (ataque, normal) el ataque tiene el puntaje más alto.

El AUC **no depende del umbral**, y por eso es igual en los tres puntos de operación de un modelo: los tres puntos son lugares distintos de la misma curva. En la figura, los tres puntos del modelo ganador sobre su curva ROC (FPR en escala logarítmica, que es donde está la zona de interés; el rectángulo verde es la meta del proyecto):

::: {.figura-mediana}
![Curva ROC del modelo ganador con los tres puntos de operación, en UNSW-NB15 y CICIDS2017](figuras/roc_puntos_operacion.png)
:::

Se lee así: en CICIDS2017 la curva entra en la zona objetivo (los modelos son casi perfectos); en UNSW-NB15 la curva **nunca** toca el rectángulo verde, por eso ningún umbral logra Recall >= 0.95 y FPR <= 0.02 a la vez.

### Curva precisión-recall y PR-AUC

La **curva precisión-recall** pone Recall en el eje horizontal y Precisión en el vertical, para todos los umbrales. Su área (**PR-AUC**, que se calcula como precisión promedio) es más informativa que la ROC cuando la clase positiva es rara, porque la precisión sí "siente" las falsas alarmas relativas al número de ataques. El proyecto reporta ambas.

### Matriz de confusión del modelo ganador con tres umbrales

Las tres matrices siguientes son del **mismo modelo** (el ganador de UNSW-NB15) con los tres umbrales. Se ve cómo cambian los cuatro números: al bajar el umbral aumentan los VP (menos ataques perdidos) y también los FP (más falsas alarmas).

::: {.figura-mediana}
![Matrices de confusión del modelo ganador de UNSW-NB15 con los tres puntos de operación](figuras/matrices_confusion_unsw.png)
:::

### Detección por familia de ataque

Las métricas globales esconden diferencias entre familias. Engelen et al. (2021) lo muestran en CICIDS2017: la métrica agregada es igual en el dataset original y en el corregido, pero por familia el resultado es muy desigual, y por eso recomiendan analizar el desempeño por clase. El proyecto lo hace: para cada familia se reporta la proporción de flujos marcados como ataque (su **tasa de detección**). Esta es la de UNSW-NB15 con el modelo ganador:

{{>tabla_familias unsw}}

Se lee: las familias con valores cercanos a 1 se detectan casi siempre; las de valores bajos son las difíciles. La fila de tráfico normal (falsas alarmas) muestra la proporción de flujos normales que se marcaron como ataque, que es el FPR. Atención a la columna de flujos de prueba: con pocos flujos, la tasa es muy inestable.

### Incertidumbre: intervalos de confianza por bootstrap

Una métrica medida con un conjunto de prueba finito tiene **ruido de muestreo**: con otra prueba habría salido un valor algo distinto. Para cuantificarlo se usa el **bootstrap** (Efron, 1979): se simula repetir la prueba muchas veces remuestreando los flujos **con reemplazo**, se recalcula la métrica en cada remuestreo y se toman los percentiles 2.5 y 97.5. Eso da un **intervalo de confianza del 95 %** (IC 95 %).

::: nota
Un IC 95 % no significa "hay 95 % de probabilidad de que el valor real esté dentro". Significa que, **si se repitiera el procedimiento muchas veces**, el 95 % de los intervalos construidos así contendrían el valor real. La lectura práctica es: el intervalo muestra cuánto puede moverse la métrica solo por el azar de la muestra de prueba.
:::

El proyecto implementa un bootstrap **exacto y rápido** usando la distribución multinomial de las cuatro casillas de la matriz de confusión (explicado en C.8), válido porque Recall y FPR solo dependen de esos conteos. Este intervalo cubre **solo el ruido de la prueba**, no la variación de entrenar con otra semilla.

### Comparar dos modelos: la prueba pareada

Para saber si el modelo A es mejor que el B no basta con mirar dos números. El **bootstrap pareado** remuestrea **los mismos flujos para los dos modelos** y calcula la diferencia (A menos B) en cada remuestreo. De esa distribución salen:

- la **diferencia puntual** (A menos B en la prueba real),
- su **intervalo de confianza del 95 %**: si no contiene el cero, la diferencia no se explica solo por el azar de la prueba,
- un **valor p bilateral**: el proyecto lo define como el doble del lado más pequeño de la distribución respecto del cero (acotado a 1). Un $p$ pequeño (por ejemplo menor de 0.05) indica que sería raro ver esa diferencia si en realidad no hubiera ninguna.

::: importante
**Por qué el pareado detecta lo que los intervalos separados ocultan.** Los intervalos de dos modelos pueden solaparse y aun así ser distintos, porque cada intervalo incluye la dificultad común de la prueba (los mismos flujos difíciles para ambos). La diferencia pareada cancela esa parte compartida. En el proyecto, los intervalos de Recall de XGBoost base y mejorado se solapaban; la prueba pareada sí detectó diferencias pequeñas pero reales entre ellos. **Solapar no demuestra igualdad.**
:::

::: advertencia
Un $p$ pequeño **no** dice que la diferencia sea **grande**: aquí son diferencias de menos de un punto porcentual. Y la prueba solo cubre el ruido de la prueba, no el de entrenar con otra semilla ni el de repetir la búsqueda de hiperparámetros. Con un conjunto de prueba grande, hasta diferencias minúsculas salen "significativas". Hay que mirar siempre el tamaño de la diferencia junto con el $p$.
:::

Los resultados de las pruebas pareadas en UNSW-NB15 (modelo A menos modelo B) están en esta tabla:

{{>tabla_pareadas unsw}}

### Repetir con varias semillas

Otra forma de medir la variación es **repetir todo** (reparto, entrenamiento y evaluación) con varias semillas y mirar la media y la desviación estándar. Para UNSW-NB15, con 5 semillas, en el punto de máximo Recall con FPR <= 0.02:

{{>tabla_semillas unsw fpr_budget}}

Se lee: cada celda es media ± desviación estándar sobre las 5 semillas. Si la desviación es del orden de las diferencias entre modelos, esas diferencias no son fiables. Limitación importante: los hiperparámetros de las versiones mejoradas **no se volvieron a buscar** en cada semilla, así que esta desviación subestima la variación real de repetir también la búsqueda.
