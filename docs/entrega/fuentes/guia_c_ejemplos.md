# Parte C: Ejemplos resueltos a mano

Esta parte sirve para **practicar con la mano**. Cada ejemplo toma una idea de la Parte A y la resuelve paso a paso con números pequeños que se pueden verificar con calculadora. Los ejemplos marcados como didácticos usan datos inventados para enseñar; **no son datos del proyecto**. Todos los resultados aritméticos de esos ejemplos se calcularon también con Python (y, cuando existe, con la función real del repositorio) para comprobar que no haya errores. Las cifras del proyecto real (UNSW-NB15, CICIDS2017) salen de los reportes y se escriben a partir de ellos.

::: nota
Cómo usar esta parte: tapar la solución, resolver el ejercicio con papel y lápiz y comparar. Si en la sustentación preguntan "¿cómo se calcula X?", el ejemplo correspondiente es la respuesta.
:::

## C.1 De la matriz de confusión a todas las métricas

**Ejemplo didáctico, no son datos del proyecto.** Un detector clasificó 10 flujos. Los 4 primeros son ataques reales y los 6 últimos son tráfico normal.

| Flujo | Real | Predicho | Resultado |
|---|---|---|---|
| 1 | ataque | ataque | VP (verdadero positivo) |
| 2 | ataque | ataque | VP |
| 3 | ataque | ataque | VP |
| 4 | ataque | normal | FN (ataque no detectado) |
| 5 | normal | ataque | FP (falsa alarma) |
| 6 | normal | normal | VN (verdadero negativo) |
| 7 | normal | normal | VN |
| 8 | normal | normal | VN |
| 9 | normal | normal | VN |
| 10 | normal | normal | VN |

Se cuenta cada resultado y se arma la matriz de confusión:

| | Predicho ataque | Predicho normal | Total |
|---|---|---|---|
| **Real ataque** | VP = 3 | FN = 1 | 4 |
| **Real normal** | FP = 1 | VN = 5 | 6 |

Con esos cuatro números salen todas las métricas:

- **Accuracy** $= \dfrac{VP + VN}{VP + VN + FP + FN} = \dfrac{3 + 5}{10} = 0.8$
- **Precisión** $= \dfrac{VP}{VP + FP} = \dfrac{3}{3 + 1} = 0.75$ (de las 4 alertas, 3 eran ataques reales)
- **Recall** $= \dfrac{VP}{VP + FN} = \dfrac{3}{3 + 1} = 0.75$ (de los 4 ataques, se detectaron 3)
- **F1** $= \dfrac{2 \cdot VP}{2 \cdot VP + FP + FN} = \dfrac{6}{6 + 1 + 1} = 0.75$
- **FPR** $= \dfrac{FP}{FP + VN} = \dfrac{1}{1 + 5} = 0.1667$ (de 6 flujos normales, 1 se marcó como ataque)
- **Especificidad** $= 1 - \text{FPR} = \dfrac{VN}{FP + VN} = \dfrac{5}{6} = 0.8333$

::: importante
Recall y FPR miran **filas distintas** de la matriz. Recall mira la fila de los ataques reales; FPR mira la fila de los flujos normales. Por eso mejorar uno no mejora automáticamente el otro, y por eso el proyecto los reporta juntos.
:::

### Por qué la accuracy engaña cuando hay pocos ataques

**Ejemplo didáctico.** Una red tiene 1000 flujos: 20 son ataques y 980 son normales.

| Clasificador | VP | FN | FP | VN | Accuracy | Recall | FPR |
|---|---|---|---|---|---|---|---|
| "Todo es normal" | 0 | 20 | 0 | 980 | 0.98 | 0 | 0 |
| Detector real | 16 | 4 | 49 | 931 | 0.947 | 0.80 | 0.05 |

El clasificador que **nunca detecta nada** tiene accuracy 0.98, mayor que la del detector que sí funciona (0.947). Además la precisión del detector real es $16 / (16 + 49) = 0.246$: de cada 4 alertas solo 1 es real, porque los ataques son raros. Es la razón por la que el proyecto no se juzga con la accuracy sino con Recall y FPR, y por la que la sección C.5 estudia cómo la prevalencia afecta la precisión.

::: ejemplo
En el proyecto real, la prevalencia de ataques tras la limpieza es {{unsw.clean.attack_pct}} en UNSW-NB15 y {{cic.clean.attack_pct}} en CICIDS2017. Un clasificador que siempre dijera "normal" tendría una accuracy de {{unsw.clean.normal_pct}} en el primero y {{cic.clean.normal_pct}} en el segundo, sin detectar un solo ataque.
:::

## C.2 Gini y la mejor división de un árbol

**Ejemplo didáctico, no son datos del proyecto.** Ocho flujos descritos por dos variables: el número de paquetes y la duración en segundos. Es el mismo conjunto que dibuja la figura de abajo, generada con `sklearn`.

| Flujo | Paquetes | Duración (s) | Clase |
|---|---|---|---|
| 1 | 2 | 0.1 | normal |
| 2 | 3 | 0.2 | normal |
| 3 | 4 | 0.3 | normal |
| 4 | 5 | 0.2 | normal |
| 5 | 60 | 0.5 | ataque |
| 6 | 80 | 0.4 | ataque |
| 7 | 120 | 0.6 | ataque |
| 8 | 4 | 2.5 | ataque |

El flujo 8 es un ataque "lento": pocos paquetes pero muy largo (como un *slowloris*). Ese flujo hace que mirar solo los paquetes no baste.

**Impureza de Gini.** Para un grupo donde una fracción $p$ de los flujos son ataques:

$$G = 1 - p^2 - (1-p)^2$$

Vale 0 si el grupo es puro (todos de una clase) y 0.5 si está mezclado 50 y 50. En la raíz hay 4 ataques de 8, así que $p = 0.5$ y $G = 1 - 0.25 - 0.25 = 0.5$.

**Cómo se elige un corte.** El árbol prueba cada umbral posible (el punto medio entre dos valores consecutivos de una variable), separa los flujos en izquierda ($\le$ umbral) y derecha ($>$ umbral), y calcula el Gini ponderado por tamaño:

$$G_{\text{corte}} = \frac{n_{\text{izq}}}{n}\, G_{\text{izq}} + \frac{n_{\text{der}}}{n}\, G_{\text{der}}$$

Gana el corte con menor $G_{\text{corte}}$. Todos los candidatos de este ejemplo:

| Variable | Umbral | Izquierda (n, ataques) | Derecha (n, ataques) | Gini ponderado |
|---|---|---|---|---|
| paquetes | 2.5 | 1, 0 | 7, 4 | 0.4286 |
| paquetes | 3.5 | 2, 0 | 6, 4 | 0.3333 |
| paquetes | 4.5 | 4, 1 | 4, 3 | 0.3750 |
| paquetes | 32.5 | 5, 1 | 3, 3 | 0.2000 |
| paquetes | 70 | 6, 2 | 2, 2 | 0.3333 |
| paquetes | 100 | 7, 3 | 1, 1 | 0.4286 |
| duración | 0.15 | 1, 0 | 7, 4 | 0.4286 |
| duración | 0.25 | 3, 0 | 5, 4 | 0.2000 |
| **duración** | **0.35** | **4, 0** | **4, 4** | **0.0000** |
| duración | 0.45 | 5, 1 | 3, 3 | 0.2000 |
| duración | 0.55 | 6, 2 | 2, 2 | 0.3333 |
| duración | 1.55 | 7, 3 | 1, 1 | 0.4286 |

**Ejemplo de una fila.** Corte "paquetes $\le$ 32.5": a la izquierda quedan los flujos 1 a 4 y el 8 (5 flujos, 1 ataque, $p = 0.2$, $G = 1 - 0.04 - 0.64 = 0.32$); a la derecha los flujos 5 a 7 (3 flujos, todos ataques, $G = 0$). Ponderado: $\frac{5}{8}\cdot 0.32 + \frac{3}{8}\cdot 0 = 0.2$.

**Resultado.** El mejor corte es `duracion <= 0.35` con Gini ponderado 0: deja 4 flujos normales a la izquierda y 4 ataques a la derecha, todo puro. Como las dos hojas ya son puras, el árbol **se detiene** aunque se le permitió profundidad 2. Eso es exactamente lo que devuelve `DecisionTreeClassifier(max_depth=2, criterion="gini", random_state=0)`: un solo corte en `duracion` (sklearn lo muestra como 0.35000001 por trabajar en `float32`) y dos hojas, una con 4 normales y otra con 4 ataques.

::: {.figura-pequena}
![Árbol de decisión del ejemplo: un solo corte por duración separa las dos clases](figuras/ejemplo_arbol.png)
:::

::: nota
Lección: **la mejor variable no es la que "parece" más importante**. Mirando solo los paquetes, el mejor corte (32.5) deja un ataque mal clasificado. La duración, que a primera vista parecía secundaria, resuelve el caso del ataque lento. Un árbol grande (y por tanto un Random Forest o XGBoost) hace esto miles de veces con decenas de variables.
:::

## C.3 Elegir el umbral a mano

**Ejemplo didáctico, no son datos del proyecto.** Un modelo puntuó 12 flujos de validación con una probabilidad de ataque. Hay 5 ataques reales y 7 normales, y hay un **empate** en 0.60 (un normal y un ataque con el mismo puntaje). Se ordenan de mayor a menor puntaje y se acumulan los ataques detectados (VP) y las falsas alarmas (FP) si el umbral se pusiera justo en ese puntaje:

| Flujo | Real | Puntaje | VP acumulado | FP acumulado | Recall | FPR |
|---|---|---|---|---|---|---|
| A | ataque | 0.95 | 1 | 0 | 0.2 | 0.0000 |
| B | ataque | 0.90 | 2 | 0 | 0.4 | 0.0000 |
| C | normal | 0.85 | 2 | 1 | 0.4 | 0.1429 |
| D | ataque | 0.80 | 3 | 1 | 0.6 | 0.1429 |
| E | normal | 0.60 | 3 | 2 | 0.6 | 0.2857 |
| F | ataque | 0.60 | 4 | 2 | 0.8 | 0.2857 |
| G | normal | 0.40 | 4 | 3 | 0.8 | 0.4286 |
| H | normal | 0.35 | 4 | 4 | 0.8 | 0.5714 |
| I | ataque | 0.30 | 5 | 4 | 1.0 | 0.5714 |
| J | normal | 0.20 | 5 | 5 | 1.0 | 0.7143 |
| K | normal | 0.10 | 5 | 6 | 1.0 | 0.8571 |
| L | normal | 0.05 | 5 | 7 | 1.0 | 1.0000 |

(Recall $= VP / 5$; FPR $= FP / 7$.)

**El empate.** Los flujos E y F tienen el mismo puntaje 0.60, así que ningún umbral puede incluir uno sin incluir el otro. Por eso la tabla solo vale en los puntos donde el puntaje **cambia**: después de D (0.80), después de F (0.60) y así sucesivamente. Un umbral de 0.60 marca E y F juntos (VP = 4, FP = 2); un umbral de 0.61 no marca ninguno de los dos (VP = 3, FP = 1). La función `select_threshold` evalúa solo esos puntos de corte, justamente para no partir un empate.

**Regla 1: mínimo FPR con Recall >= objetivo** (el criterio de AGENT.md, `select_threshold`).

- Objetivo Recall >= 0.8: los puntos que cumplen son los de la fila F en adelante. El de menor FPR es el de la fila F (0.2857). Umbral elegido: **0.60**, con VP = 4, FP = 2.
- Objetivo Recall >= 1.0: hace falta llegar al ataque I. Umbral **0.30**, con FP = 4 y FPR 0.5714. Pedir todo el recall cuesta más de la mitad de las falsas alarmas posibles.
- Objetivo Recall >= 0.6: el de menor FPR es la fila D. Umbral **0.80**, con VP = 3, FP = 1.

**Regla 2: máximo Recall con FPR <= presupuesto** (`select_threshold_for_fpr`).

- Presupuesto FPR <= 0.15: los puntos con FPR hasta 0.1429 son las filas A a D. El de mayor recall es D. Umbral **0.80**, Recall 0.6.
- Presupuesto FPR <= 0.0: solo valen A y B. Umbral **0.90**, Recall 0.4, ninguna falsa alarma.
- Presupuesto FPR <= 0.30: llega hasta la fila F. Umbral **0.60**, Recall 0.8, FPR 0.2857.

**Regla 0: umbral fijo 0.5.** Marca como ataque todo lo que tenga puntaje $\ge 0.5$: A a F. Resultado: VP = 4, FP = 2, Recall 0.8, FPR 0.2857, precisión 0.667, accuracy 0.75. Aquí coincide con la regla 1 de objetivo 0.8, pero **por casualidad**: nada obliga a que 0.5 sea un buen umbral.

::: importante
Las tres reglas leen la **misma** lista de puntajes y solo cambian el punto de corte. Por eso en el proyecto los tres puntos de operación de un modelo tienen la misma ROC-AUC: el modelo no cambió, cambió qué error se acepta. Todo esto se hace con la validación; el conjunto de prueba solo se mira después.
:::

::: ejemplo
En el proyecto real, el modelo ganador de UNSW-NB15 ({{unsw.best}}) usa los umbrales {{unsw.thr.xgb_improved.default}} (fijo), {{unsw.thr.xgb_improved.recall_target}} (mínimo FPR con Recall >= 0.95) y {{unsw.thr.xgb_improved.fpr_budget}} (máximo Recall con FPR <= 0.02). El umbral del Recall alto es menor que 0.5 porque para detectar más ataques hay que aceptar flujos con puntaje más bajo.
:::

## C.4 Votación suave: cómo se construye el Mix

**Ejemplo didáctico, no son datos del proyecto.** Un Random Forest y un XGBoost puntuaron los mismos 10 flujos de validación (4 ataques y 6 normales). El Mix promedia las dos probabilidades de ataque, flujo por flujo (`SoftVotingEnsemble` hace exactamente eso):

| Flujo | Real | RF | XGBoost | Mix = (RF + XGBoost) / 2 |
|---|---|---|---|---|
| 1 | ataque | 0.90 | 0.95 | 0.925 |
| 2 | ataque | 0.70 | 0.60 | 0.650 |
| 3 | ataque | 0.40 | 0.70 | 0.550 |
| 4 | ataque | 0.35 | 0.20 | 0.275 |
| 5 | normal | 0.50 | 0.10 | 0.300 |
| 6 | normal | 0.30 | 0.45 | 0.375 |
| 7 | normal | 0.20 | 0.25 | 0.225 |
| 8 | normal | 0.15 | 0.10 | 0.125 |
| 9 | normal | 0.10 | 0.05 | 0.075 |
| 10 | normal | 0.05 | 0.02 | 0.035 |

Dónde se nota que los dos modelos **discrepan**:

- Flujo 3 (ataque): el RF duda (0.40) y XGBoost lo ve claro (0.70). El Mix queda en 0.55, por encima de 0.5.
- Flujo 5 (normal): el RF casi lo marca (0.50) y XGBoost lo descarta (0.10). El Mix lo deja en 0.30, claramente bajo.
- Flujo 4 (ataque): ambos lo puntúan bajo (0.35 y 0.20). Ningún modelo ni el Mix lo detecta: promediar no crea información que ninguno tiene.

Se elige el umbral de cada modelo en validación con la regla "mínimo FPR con Recall >= 0.75" (en el proyecto sería 0.95):

| Modelo | Umbral elegido | Recall | FPR | Con umbral 0.5: Recall | Con umbral 0.5: FPR |
|---|---|---|---|---|---|
| RF | 0.40 | 0.75 | 0.1667 | 0.50 | 0.1667 |
| XGBoost | 0.60 | 0.75 | 0.0000 | 0.75 | 0.0000 |
| Mix | 0.55 | 0.75 | 0.0000 | 0.75 | 0.0000 |

Cómo se lee: el RF solo necesita bajar el umbral a 0.40 para detectar 3 de 4 ataques y paga con una falsa alarma (el flujo 5, que tiene 0.50). El Mix consigue el mismo recall sin ninguna falsa alarma, porque XGBoost "corrige" el 0.50 del RF en el flujo 5.

::: importante
El umbral del Mix **se elige sobre los puntajes del Mix** en validación; no es el promedio de los umbrales de sus miembros. Por eso el Mix tiene su propia fila de umbrales en los reportes, y por eso un Mix puede ganar con una regla y perder con otra.
:::

::: ejemplo
En UNSW-NB15 los umbrales del Mix mejorado son {{unsw.thr.mix_improved.default}}, {{unsw.thr.mix_improved.recall_target}} y {{unsw.thr.mix_improved.fpr_budget}}, distintos de los de XGBoost ({{unsw.thr.xgb_improved.default}}, {{unsw.thr.xgb_improved.recall_target}} y {{unsw.thr.xgb_improved.fpr_budget}}) y de los del Random Forest mejorado ({{unsw.thr.rf_improved.default}}, {{unsw.thr.rf_improved.recall_target}} y {{unsw.thr.rf_improved.fpr_budget}}).
:::

## C.5 La aritmética de las falsas alarmas

### Parte 1: FPR por número de flujos normales

Una falsa alarma es un flujo normal marcado como ataque. Si en un día pasan $N$ flujos normales y el detector tiene una tasa de falsos positivos FPR, el número esperado de falsas alarmas es

$$\text{falsas alarmas} = \text{FPR} \times N$$

**Ejemplo didáctico, no son datos del proyecto.** Con $N = 1\,000\,000$ flujos normales:

| FPR | Falsas alarmas por millón de flujos normales |
|---|---|
| 0.001 | 1 000 |
| 0.02 | 20 000 |
| 0.1 | 100 000 |

Un FPR que "parece pequeño" (2 %) son 20 000 alertas que un analista debe revisar. Ese es el mecanismo de la **fatiga de alertas** del SOC (A.1). La figura siguiente hace esta misma cuenta con los FPR reales de los modelos ganadores del proyecto, suponiendo un millón de flujos normales (suposición ilustrativa, no un dato del proyecto):

::: {.figura-mediana}
![Falsas alarmas esperadas por cada millón de flujos normales, con el FPR real del modelo ganador en cada punto de operación](figuras/alarmas_por_millon.png)
:::

### Parte 2: la precisión depende de cuántos ataques hay (teorema de Bayes)

La **precisión** responde "si suena la alarma, ¿qué tan probable es que sea un ataque real?". Depende de tres cosas: el recall $r$, el FPR $f$ y la **prevalencia** $\pi$ (qué fracción de los flujos son ataques):

$$\text{precisión} = \frac{r \cdot \pi}{r \cdot \pi + f \cdot (1 - \pi)}$$

El numerador es la fracción de flujos que son ataques **y** se detectan; el denominador suma las falsas alarmas.

**Ejemplo didáctico, no son datos del proyecto.** Un detector con Recall 0.95 y FPR 0.02, en redes con distinta prevalencia. Se calcula sobre 1000 flujos:

| Prevalencia $\pi$ | Ataques detectados | Falsas alarmas | Precisión |
|---|---|---|---|
| 50 % | 475 | 10.0 | 0.9794 |
| 10 % | 95 | 18.0 | 0.8407 |
| 1 % | 9.5 | 19.8 | 0.3242 |
| 0.1 % | 0.95 | 19.98 | 0.0454 |

Cuenta de la fila de 1 %: ataques detectados $= 0.95 \times 0.01 \times 1000 = 9.5$; falsas alarmas $= 0.02 \times 0.99 \times 1000 = 19.8$; precisión $= 9.5 / (9.5 + 19.8) = 0.3242$.

El **mismo** detector pasa de precisión 0.98 a 0.05 solo porque los ataques se vuelven más raros: las falsas alarmas (que dependen de los flujos normales, casi todos) se quedan en unas 20 por cada 1000, mientras los ataques detectados se desploman.

::: advertencia
Los datasets del proyecto están **mucho más balanceados** que una red real (casi la mitad del tráfico de UNSW-NB15 son ataques). En una red real con pocos ataques, la precisión sería mucho menor que la de las tablas de este proyecto. Es una limitación honesta que conviene decir en la sustentación.
:::

### Parte 3: las cifras reales del proyecto

El modelo ganador de cada dataset en sus tres puntos de operación (prueba):

| Dataset | Punto de operación | Recall | FPR | Precisión |
|---|---|---|---|---|
| UNSW-NB15 | umbral 0.5 | {{unsw.m.xgb_improved.default.recall}} | {{unsw.m.xgb_improved.default.fpr}} | {{unsw.m.xgb_improved.default.precision}} |
| UNSW-NB15 | mínimo FPR con Recall >= 0.95 | {{unsw.m.xgb_improved.recall_target.recall}} | {{unsw.m.xgb_improved.recall_target.fpr}} | {{unsw.m.xgb_improved.recall_target.precision}} |
| UNSW-NB15 | máximo Recall con FPR <= 0.02 | {{unsw.m.xgb_improved.fpr_budget.recall}} | {{unsw.m.xgb_improved.fpr_budget.fpr}} | {{unsw.m.xgb_improved.fpr_budget.precision}} |
| CICIDS2017 | umbral 0.5 | {{cic.m.xgb_improved.default.recall}} | {{cic.m.xgb_improved.default.fpr5}} | {{cic.m.xgb_improved.default.precision}} |
| CICIDS2017 | mínimo FPR con Recall >= 0.95 | {{cic.m.xgb_improved.recall_target.recall}} | {{cic.m.xgb_improved.recall_target.fpr5}} | {{cic.m.xgb_improved.recall_target.precision}} |
| CICIDS2017 | máximo Recall con FPR <= 0.02 | {{cic.m.xgb_improved.fpr_budget.recall}} | {{cic.m.xgb_improved.fpr_budget.fpr5}} | {{cic.m.xgb_improved.fpr_budget.precision}} |

Para comprobar la fórmula con el proyecto: en UNSW-NB15 la prevalencia es {{unsw.clean.attack_pct}}, el recall del segundo renglón es {{unsw.m.xgb_improved.recall_target.recall}} y el FPR {{unsw.m.xgb_improved.recall_target.fpr}}. La precisión que da la fórmula es $r\pi / (r\pi + f(1-\pi))$ y coincide con la de la tabla (la de la tabla es medida directamente sobre el conjunto de prueba, cuya prevalencia es muy parecida a la del dataset).

## C.6 La fuga de datos con un ejemplo de juguete

**Ejemplo didáctico, no son datos del proyecto.** Un "modelo" extremo, que solo memoriza: si ve en prueba un vector que ya vio en entrenamiento, devuelve la etiqueta memorizada; si no lo conoce, dice "normal". Es el caso límite del sobreajuste (un árbol sin límite de profundidad casi se comporta así).

Entrenamiento (8 flujos; $f_1$ y $f_2$ son dos variables):

| $f_1$ | $f_2$ | Clase |
|---|---|---|
| 1 | 1 | normal |
| 1 | 1 | normal (copia) |
| 2 | 2 | normal |
| 2 | 3 | normal |
| 5 | 5 | ataque |
| 5 | 6 | ataque |
| 6 | 6 | ataque |
| 7 | 7 | ataque |

Prueba **sin depurar** (10 flujos): 6 son copias exactas de filas del entrenamiento y 4 son vectores nuevos.

| $f_1$ | $f_2$ | Clase real | ¿Visto en entrenamiento? | Predicción del memorizador |
|---|---|---|---|---|
| 5 | 5 | ataque | sí | ataque |
| 5 | 6 | ataque | sí | ataque |
| 6 | 6 | ataque | sí | ataque |
| 7 | 7 | ataque | sí | ataque |
| 1 | 1 | normal | sí | normal |
| 2 | 2 | normal | sí | normal |
| 9 | 9 | ataque | no | normal (no lo conoce) |
| 8 | 8 | ataque | no | normal (no lo conoce) |
| 1 | 9 | normal | no | normal |
| 3 | 9 | normal | no | normal |

| Medición | Prueba con duplicados (10 flujos) | Prueba depurada (solo los 4 nuevos) |
|---|---|---|
| Parte de la prueba ya vista | 6 de 10 (60 %) | 0 de 4 (0 %) |
| Ataques detectados | 4 de 6 | 0 de 2 |
| **Recall** | **0.667** | **0.0** |
| Accuracy | 0.8 | 0.5 |

Con los duplicados el memorizador parece detectar dos de cada tres ataques; sin ellos no detecta **ninguno**, que es lo que realmente sabe hacer con flujos que no ha visto. La fuga no "rompe" el modelo: lo hace parecer mejor de lo que es.

::: importante
Regla práctica: **cualquier vector que aparezca a la vez en entrenamiento y prueba es una pista regalada**. Por eso el proyecto quita los duplicados *antes* de partir los datos, y ajusta todo lo demás solo con entrenamiento y validación.
:::

::: ejemplo
En el proyecto real, con el protocolo ingenuo (sin depurar) {{unsw.l.naive.leaked_test_share_pct}} de la prueba de UNSW-NB15 eran vectores ya vistos, y el Recall medido era {{unsw.l.naive.recall}} frente a {{unsw.l.full.recall}} con el protocolo del proyecto, que no tiene ningún vector repetido ({{unsw.l.full.leaked_test_share_pct}}). En CICIDS2017 el protocolo ingenuo dejaba {{cic.l.naive.leaked_test_share_pct}} de la prueba ya vista, pero el Recall medido apenas cambia ({{cic.l.naive.recall}} frente a {{cic.l.full.recall}}) porque el dataset está casi saturado: hasta con los duplicados la clasificación es muy fácil.
:::

{{>tabla_fuga unsw}}

## C.7 Un flujo real de principio a fin

Este ejemplo **sí usa datos reales**: el flujo del archivo `docs/demo/flujo_ejemplo.json`, un flujo del conjunto de prueba de UNSW-NB15. Se sabe que es un ataque de la familia *Exploits* porque el mismo flujo aparece, con su etiqueta, en `docs/demo/flujos_ejemplo.csv`. El modelo **no ve esa etiqueta**: recibe solo las 42 variables.

### Paso 1: qué dicen las variables

Valores tomados del archivo JSON (las descripciones vienen de la documentación oficial del dataset, el archivo `NUSW-NB15_features.csv`):

| Grupo | Variable | Valor | Qué significa |
|---|---|---|---|
| Identidad | `proto` | tcp | Protocolo de la transacción |
| Identidad | `service` | pop3 | Servicio de aplicación |
| Identidad | `state` | FIN | Estado del flujo y su protocolo |
| Duración y volumen | `dur` | 1.096 | Duración total del registro |
| Duración y volumen | `spkts`, `dpkts` | 22, 38 | Paquetes origen a destino y destino a origen |
| Duración y volumen | `sbytes`, `dbytes` | 1042, 28456 | Bytes origen a destino y destino a origen |
| Duración y volumen | `smean`, `dmean` | 47, 749 | Tamaño medio de paquete de cada lado |
| Tasas | `sload`, `dload` | 7261.6, 202216.1 | Bits por segundo de cada lado |
| TTL | `sttl`, `dttl` | 62, 252 | Valor de *time to live* de cada lado |
| Pérdidas | `sloss`, `dloss` | 7, 17 | Paquetes retransmitidos o descartados |
| Tiempos | `sinpkt`, `dinpkt` | 52.2, 28.1 | Tiempo entre paquetes de cada lado (ms) |
| Tiempos | `sjit`, `djit` | 2742.3, 2041.1 | Jitter de cada lado (ms) |
| Apretón TCP | `synack`, `ackdat`, `tcprtt` | 0.0275, 0.0345, 0.0620 | Tiempos de establecimiento; `tcprtt` es la suma de los otros dos (0.0275 + 0.0345 = 0.0620) |
| Contadores | `ct_*` (10 variables) | 1 en ocho de ellas y 0 en `ct_ftp_cmd` y `ct_flw_http_mthd` | Cuántas conexiones recientes comparten servicio, origen, destino o puertos |
| Banderas | `is_ftp_login`, `is_sm_ips_ports`, ... | 0 | Marcas de FTP, HTTP e iguales IP y puerto |

Lectura en palabras: una conexión TCP corta (algo más de un segundo), POP3, donde el lado destino envía unos 28 KB y el lado origen solo 1 KB, con varios paquetes retransmitidos o perdidos. **No hace falta conocer el ataque** para entender lo que el modelo recibe: un vector de 42 números y 3 textos.

::: advertencia
Las variables que más pesan **en general** en el modelo ({{unsw.imp.1.name}}, {{unsw.imp.2.name}} y {{unsw.imp.3.name}}) no explican **esta** decisión en particular. La importancia global dice qué variables usa el modelo en promedio; explicar un flujo concreto exigiría otra técnica (por ejemplo, explicaciones locales), que el proyecto no implementa.
:::

### Paso 2: qué hace `predict` con el flujo

1. **Validar** (`prepare_features`): comprueba que estén las 42 columnas, convierte las numéricas a `float32`, limpia espacios en los textos y rechaza el flujo si hay valores faltantes o infinitos.
2. **Codificar** (`build_preprocessor`): las 39 variables numéricas pasan tal cual; `proto`, `service` y `state` se convierten en columnas 0/1 (una por categoría frecuente, más una columna "infrecuente" para categorías raras o nunca vistas).
3. **Filtrar** (`CorrelationFilter`): el modelo ganador descarta {{unsw.filter.dropped}} columnas redundantes aprendidas con el entrenamiento.
4. **Puntuar** (XGBoost): suma las salidas de sus árboles y las convierte en una probabilidad de ataque. Los hiperparámetros del modelo ganador:

{{>tabla_hiperparametros unsw}}

5. **Decidir**: compara la probabilidad con el umbral del punto de operación elegido.

### Paso 3: la salida real

Con el modelo entrenado, el comando

```bash
python -m src.predict --dataset unsw_nb15 --json "$(cat docs/demo/flujo_ejemplo.json)"
```

imprime (salida copiada de una ejecución real):

```json
{
  "classification": "Ataque Detectado",
  "attack_probability": 0.998622,
  "operating_point": "recall_target",
  "threshold": 0.338346,
  "model": "xgb_improved"
}
```

La probabilidad (0.998622) supera los tres umbrales, así que la decisión es la misma en cada punto de operación:

| Punto de operación | Umbral del modelo ganador | ¿0.998622 es mayor? | Decisión |
|---|---|---|---|
| umbral 0.5 | {{unsw.thr.xgb_improved.default}} | sí | Ataque Detectado |
| mínimo FPR con Recall >= 0.95 | {{unsw.thr.xgb_improved.recall_target}} | sí | Ataque Detectado |
| máximo Recall con FPR <= 0.02 | {{unsw.thr.xgb_improved.fpr_budget}} | sí | Ataque Detectado |

::: nota
Este es un flujo **fácil**: el modelo está casi seguro. Los flujos donde el umbral importa son los de probabilidad intermedia, entre {{unsw.thr.xgb_improved.recall_target}} y {{unsw.thr.xgb_improved.fpr_budget}}. En `docs/demo/flujos_ejemplo.csv` hay dos casos elegidos a propósito (las filas 8 y 9, contando desde 0) que muestran una falsa alarma que aparece solo con el umbral más bajo y un ataque de la familia Analysis que se escapa en los tres puntos.
:::

## C.8 Cómo se construye un intervalo bootstrap y una prueba pareada

### Bootstrap de una métrica

**Ejemplo didáctico, no son datos del proyecto.** El conjunto de prueba tiene solo 20 flujos: 8 ataques y 12 normales. Dos modelos, A y B, decidieron sobre los mismos 20 flujos:

| | Ataques detectados (de 8) | Recall | Falsas alarmas (de 12) | FPR |
|---|---|---|---|---|
| Modelo A | 6 | 0.750 | 2 | 0.1667 |
| Modelo B | 5 | 0.625 | 1 | 0.0833 |

Con una sola prueba de 20 flujos, ¿cuánto confiar en que A tiene más recall que B? El **bootstrap** responde simulando "otras pruebas posibles":

1. Se sortean 20 flujos **con reemplazo** de los 20 (un flujo puede salir varias veces y otros ninguna).
2. Se recalculan las métricas sobre esa muestra.
3. Se repite muchas veces y se miran los percentiles 2.5 y 97.5 de los resultados.

Cinco remuestreos de ejemplo (se ve cuánto varía todo; cada fila usa los mismos flujos remuestreados para los dos modelos):

| Remuestreo | Ataques en la muestra | Recall A | FPR A | Recall B | FPR B | Recall A menos Recall B |
|---|---|---|---|---|---|---|
| 1 | 7 | 0.857 | 0.154 | 0.714 | 0.000 | 0.143 |
| 2 | 5 | 0.400 | 0.133 | 0.000 | 0.067 | 0.400 |
| 3 | 6 | 1.000 | 0.286 | 1.000 | 0.143 | 0.000 |
| 4 | 10 | 0.800 | 0.200 | 0.700 | 0.000 | 0.100 |
| 5 | 5 | 1.000 | 0.067 | 0.800 | 0.000 | 0.200 |

(Muestras generadas con `np.random.default_rng(7)`.) Fíjese en el remuestreo 2: salieron solo 5 ataques y el Recall de B cayó a 0: con pocos flujos, una muestra "mala" cambia mucho el resultado.

Con 20 000 remuestreos:

- El Recall de A tiene un intervalo del 95 % de [0.4, 1.0] y el de B [0.25, 1.0]. Se solapan casi por completo.
- La **diferencia pareada** (Recall A menos Recall B, calculada dentro de cada remuestreo) tiene un intervalo del 95 % de [0.0, 0.4] y un p bilateral de alrededor de 0.72. El intervalo toca el cero y el p es alto: **con 20 flujos no se puede afirmar que A sea mejor que B**, aunque A saque 0.125 más de recall en esta muestra.

### El truco que usa el proyecto (multinomial)

Remuestrear 374 000 flujos de prueba 2000 veces fila por fila sería lento. Pero para medir Recall y FPR solo importa **cuántos flujos caen en cada casilla** de la matriz de confusión (VP, FN, FP, VN). Remuestrear $n$ flujos con reemplazo equivale a sortear esas cuatro cantidades de una distribución multinomial con las proporciones observadas. En la prueba pareada se usan 8 casillas (clase real, decisión de A, decisión de B). Es matemáticamente equivalente y casi instantáneo: se verificó con este mismo ejemplo de 20 flujos (la función del repositorio da un intervalo de [0.0, 0.4] y un p de 0.72, igual que el remuestreo fila a fila) y la tarea de pruebas pareadas de CICIDS2017 termina en un segundo.

### Por qué "pareado" cambia la conclusión

El bootstrap pareado remuestrea **los mismos flujos para los dos modelos**, así que la dificultad compartida (flujos que ambos fallan o aciertan) se cancela en la diferencia. Dos intervalos separados pueden solaparse aunque la diferencia sea real, porque cada uno incluye esa dificultad común. Eso pasó en el proyecto: los intervalos de Recall de XGBoost base y mejorado se solapaban, pero la prueba pareada sí detecta diferencias:

| Comparación (UNSW-NB15, prueba) | Diferencia | IC 95 % | p |
|---|---|---|---|
| XGBoost mejorado menos base: Recall con FPR <= 0.02 | {{unsw.p.xgb_improved__xgb_baseline.fpr_budget.recall.diff}} | [{{unsw.p.xgb_improved__xgb_baseline.fpr_budget.recall.low}}, {{unsw.p.xgb_improved__xgb_baseline.fpr_budget.recall.high}}] | {{unsw.p.xgb_improved__xgb_baseline.fpr_budget.recall.p}} |
| XGBoost mejorado menos base: FPR con Recall >= 0.95 | {{unsw.p.xgb_improved__xgb_baseline.recall_target.fpr.diff}} | [{{unsw.p.xgb_improved__xgb_baseline.recall_target.fpr.low}}, {{unsw.p.xgb_improved__xgb_baseline.recall_target.fpr.high}}] | {{unsw.p.xgb_improved__xgb_baseline.recall_target.fpr.p}} |

::: importante
Cómo leerlo sin exagerar: un p pequeño dice que la diferencia **no es ruido de muestreo de la prueba**, pero no dice que sea grande. Aquí son diferencias de menos de un punto porcentual. Además, este intervalo solo cubre el ruido de la prueba y no la variación de entrenar con otra semilla ni la de repetir la búsqueda de hiperparámetros.
:::

## C.9 One-hot y filtro de correlación en miniatura

### One-hot con categorías infrecuentes

Los modelos de árboles necesitan números, así que `proto`, `service` y `state` se codifican en columnas 0/1. El codificador del proyecto agrupa en una columna "infrecuente" cualquier categoría que aparezca en menos del 1 % de las filas de entrenamiento (`min_frequency=0.01`) y también las categorías **nunca vistas**, de modo que un flujo nuevo no hace fallar la predicción.

**Ejemplo didáctico, no son datos del proyecto.** Entrenamiento de 300 flujos donde `proto` es `tcp` (150), `udp` (148), `sctp` (1) y `gre` (1). El 1 % de 300 es 3, así que `sctp` y `gre` son infrecuentes. Código (con las clases reales del proyecto):

```python
import numpy as np
import pandas as pd
from src.features import build_preprocessor

rng = np.random.default_rng(0)
proto = ["tcp"] * 150 + ["udp"] * 148 + ["sctp"] + ["gre"]
train = pd.DataFrame({"dur": rng.random(300).round(3), "proto": proto})
prep = build_preprocessor(["dur"], ["proto"]).fit(train)

new = pd.DataFrame({"dur": [0.5, 0.7, 0.2], "proto": ["tcp", "sctp", "never-seen"]})
print(prep.transform(new))
```

Salida:

| | dur | proto_tcp | proto_udp | proto_infrequent_sklearn |
|---|---|---|---|---|
| tcp | 0.5 | 1 | 0 | 0 |
| sctp (raro) | 0.7 | 0 | 0 | 1 |
| never-seen | 0.2 | 0 | 0 | 1 |

`sctp` y un protocolo jamás visto caen en la misma columna "infrecuente"; `tcp` activa su propia columna. En UNSW-NB15 `proto` tiene 133 valores distintos, la mayoría rarísimos, y esto evita crear más de cien columnas casi vacías.

### Filtro de correlación

El filtro recorre las variables en orden, conserva la primera y descarta cualquiera que correlacione más de 0.95 (en valor absoluto) con una ya conservada.

**Ejemplo didáctico, no son datos del proyecto.** Cuatro variables: `sbytes`, `sbytes_x2` (casi exactamente el doble de la anterior, más un ruido mínimo), `dur` y `dpkts`:

```python
import numpy as np
import pandas as pd
from src.features import CorrelationFilter

rng = np.random.default_rng(0)
a = rng.normal(size=200)
mini = pd.DataFrame(
    {
        "sbytes": a * 100 + 500,
        "sbytes_x2": a * 200 + 1000 + rng.normal(scale=1, size=200),
        "dur": rng.random(200),
        "dpkts": rng.integers(0, 50, 200).astype(float),
    }
)
print(mini.corr().round(3))
selector = CorrelationFilter(threshold=0.95).fit(mini)
print(list(selector.get_feature_names_out(list(mini.columns))))
```

Matriz de correlación obtenida:

| | sbytes | sbytes_x2 | dur | dpkts |
|---|---|---|---|---|
| sbytes | 1.000 | 1.000 | 0.117 | -0.095 |
| sbytes_x2 | 1.000 | 1.000 | 0.117 | -0.094 |
| dur | 0.117 | 0.117 | 1.000 | -0.056 |
| dpkts | -0.095 | -0.094 | -0.056 | 1.000 |

Resultado: se conservan `['sbytes', 'dur', 'dpkts']`. `sbytes_x2` se descarta porque su correlación con `sbytes` (ya conservada) es 1.000, mayor que 0.95. Las demás correlaciones están muy por debajo del umbral y no se tocan.

::: ejemplo
En el proyecto, el filtro se ajusta **solo con el entrenamiento** y descarta {{unsw.filter.dropped}} columnas en el modelo ganador de UNSW-NB15 y {{cic.filter.dropped}} en el de CICIDS2017. Dos columnas muy correlacionadas llevan la misma información, así que quitar una simplifica el modelo sin perder señal. Si se calculara con todos los datos (incluida la prueba), sería otra forma de fuga, aunque leve.
:::
