# Cómo usar este guion {.sin-salto}

Este guion es para una sustentación de **10 minutos** con **12 diapositivas** (más 4 de respaldo) y tres expositores, repartidos según los roles del proyecto. El texto en recuadro azul es **lo que se dice**; el resto son indicaciones. Está escrito para hablarse, no para leerse: frases cortas, un dato por frase. Practiquen con cronómetro: el texto hablado suma unas 1 100 palabras, es decir, unos 8 minutos a 140 palabras por minuto; el resto de los 10 minutos son la demostración, las pausas y los relevos.

## Reparto y tiempos

| Diapositiva | Tema | Expositor | Tiempo | Acumulado |
|---|---|---|---|---|
| 1 | Problema | Fabian | 0:45 | 0:45 |
| 2 | Pregunta y alcance | Fabian | 0:45 | 1:30 |
| 3 | Arquitectura | Fabian | 0:45 | 2:15 |
| 4 | Los datos | Silvana | 0:50 | 3:05 |
| 5 | Limpieza sin fuga y partición | Silvana | 0:55 | 4:00 |
| 6 | Los modelos | Silvana | 0:45 | 4:45 |
| 7 | Métricas y puntos de operación | Raul | 0:50 | 5:35 |
| 8 | Resultados en UNSW-NB15 | Raul | 0:55 | 6:30 |
| 9 | Resultados en CICIDS2017 | Raul | 0:40 | 7:10 |
| 10 | Experimentos formales | Raul | 0:55 | 8:05 |
| 11 | Demostración | Fabian | 0:50 | 8:55 |
| 12 | Conclusiones | Raul | 0:50 | 9:45 |

Quedan 15 segundos de margen para los cambios de expositor. Si la docente interrumpe con una pregunta, respondan en una frase y retomen.

::: nota
**Números hablados.** Las cifras del texto salen de los reportes del proyecto. Al decirlas, redondeen: "0.9515" se dice "noventa y cinco por ciento", "0.1222" se dice "doce por ciento". Nadie se acuerda de cuatro decimales.
:::

## Reglas para los tres

1. **Una idea por diapositiva.** Si la diapositiva tiene una figura, la figura es la protagonista: señálenla.
2. **No lean la diapositiva.** El guion complementa lo que se ve.
3. **Mirar al público, no a la pantalla.**
4. **Nombrar siempre el punto de operación** cuando den un Recall o un FPR: sin eso la cifra no significa nada.
5. **Reconocer los límites sin disculparse.** "No pudimos reproducir ese número" es una frase de rigor, no de debilidad.

# Guion diapositiva por diapositiva {.sin-salto}

## Diapositiva 1: el problema

<span class="tiempo">0:45</span> **Fabian**

::: decir
Buenos días. Somos Silvana, Raul y Fabian, y vamos a presentarles nuestro sistema de detección de intrusiones de red con aprendizaje automático.

Un sistema de detección de intrusiones vigila el tráfico de una red y avisa cuando algo parece un ataque. Los tradicionales funcionan con firmas: reglas escritas de antemano. Y eso tiene dos problemas.

Primero: no ven lo que nunca han visto. Un ataque nuevo pasa sin que suene ninguna alarma.

Segundo: marcan como ataque tráfico legítimo pero raro. Y cuando hay demasiadas falsas alarmas, los analistas dejan de creerles.

El aprendizaje automático propone otra idea: aprender, a partir de ejemplos, cómo se ve el tráfico normal y cómo se ven los ataques.
:::

::: relevo
**Relevo a la diapositiva 2:** "Con esa idea, nuestra pregunta es la siguiente."
:::

## Diapositiva 2: la pregunta y el alcance

<span class="tiempo">0:45</span> **Fabian**

::: decir
Nuestra pregunta de investigación: ¿qué algoritmo ofrece el mejor equilibrio entre detectar ataques y no dar falsas alarmas?

Medimos esas dos cosas con dos números. El Recall: de todos los ataques, ¿cuántos detectamos? Y el FPR: de todo el tráfico normal, ¿cuánto marcamos por error?

La meta del proyecto es Recall de al menos 0.95 con FPR de como máximo 0.02.

Comparamos Random Forest, XGBoost y la combinación de ambos, que llamamos Mix. Cada uno en una versión base y una mejorada. Y lo hicimos en dos datasets públicos: UNSW-NB15 y CICIDS2017.
:::

::: relevo
**Relevo:** "Para que todo esto fuera reproducible, construimos esta arquitectura."
:::

## Diapositiva 3: la arquitectura

<span class="tiempo">0:45</span> **Fabian**

::: decir
El prototipo es una tubería de seis etapas, y cada una se ejecuta con un solo comando.

Descargamos los datos con verificación de integridad. Los limpiamos. Los partimos en entrenamiento, validación y prueba. Entrenamos los modelos. Elegimos los umbrales en validación. Y solo al final evaluamos en prueba.

Todo tiene semillas fijas, pruebas automáticas y corre en integración continua, de modo que cualquiera puede repetir nuestros resultados.

Silvana les cuenta qué hicimos con los datos.
:::

::: relevo
**Relevo a Silvana.**
:::

## Diapositiva 4: los datos

<span class="tiempo">0:50</span> **Silvana**

::: decir
UNSW-NB15 tiene {{unsw.clean.rows_raw}} flujos con nueve familias de ataque. CICIDS2017 tiene {{cic.clean.rows_raw}}. Un flujo es el resumen de una conversación entre dos equipos: cuánto duró, cuántos paquetes, cuántos bytes.

Antes de entrenar, encontramos algo importante. En UNSW-NB15, {{unsw.clean.dup_pct}} de los flujos eran duplicados, y otros eran contradictorios: el mismo flujo marcado a la vez como normal y como ataque. En CICIDS2017, los duplicados eran {{cic.clean.dup_pct}}.

Además, los datos están muy desbalanceados. En CICIDS2017 hay familias de ataque con solo once flujos.
:::

::: relevo
**Relevo:** "Y esto nos lleva a una pregunta: ¿importa que haya duplicados?"
:::

## Diapositiva 5: limpieza sin fuga y partición

<span class="tiempo">0:55</span> **Silvana**

::: decir
Importa muchísimo. Si el mismo flujo queda en entrenamiento y en prueba, el modelo no está generalizando: está recordando. A eso se le llama fuga de datos, y infla los resultados.

Lo medimos. En UNSW-NB15, con un protocolo ingenuo, {{unsw.l.naive.leaked_test_share_pct}} de la prueba eran flujos que el modelo ya había visto, y el Recall parecía {{unsw.l.naive.recall}}. El verdadero es {{unsw.l.full.recall}}.

Por eso limpiamos antes de partir. Partimos en setenta, quince y quince por ciento, estratificado por tipo de ataque. Y el conjunto de prueba no se toca hasta el final: ni para los hiperparámetros, ni para los umbrales, ni para elegir el modelo.
:::

::: relevo
**Relevo:** "Con los datos limpios, entrenamos estos modelos."
:::

## Diapositiva 6: los modelos

<span class="tiempo">0:45</span> **Silvana**

::: decir
Entrenamos tres modelos. Random Forest vota con muchos árboles independientes. XGBoost construye árboles en secuencia, y cada uno corrige los errores del anterior. Y el Mix promedia a los dos.

Cada modelo tiene una versión base, con la configuración del primer entregable, y una versión mejorada. La mejorada hace tres cosas: elimina variables redundantes, ajusta los hiperparámetros con validación cruzada de cinco folds, y elige el umbral de decisión en validación.

Ahora Raul les explica cómo medimos si funcionan.
:::

::: relevo
**Relevo a Raul.**
:::

## Diapositiva 7: métricas y puntos de operación

<span class="tiempo">0:50</span> **Raul**

::: decir
Un modelo no dice "ataque" o "normal". Da una probabilidad, y nosotros decidimos desde qué probabilidad lanzar la alerta. Ese umbral es una decisión de negocio: si lo bajamos, detectamos más ataques pero damos más falsas alarmas; si lo subimos, pasa lo contrario.

Por eso evaluamos tres puntos de operación. El umbral cero punto cinco. El criterio del proyecto: el mínimo FPR que mantenga un Recall de al menos 0.95. Y un presupuesto de falsas alarmas: el máximo Recall con un FPR de como máximo 0.02.

Los umbrales se eligen siempre en validación. Y todas las cifras llevan intervalos de confianza.
:::

::: relevo
**Relevo:** "Veamos qué pasó."
:::

## Diapositiva 8: resultados en UNSW-NB15

<span class="tiempo">0:55</span> **Raul**

::: decir
En UNSW-NB15 el mejor modelo es {{unsw.best}}.

Con el umbral cero punto cinco, detecta {{unsw.m.xgb_improved.default.recall_pct}} de los ataques, con {{unsw.m.xgb_improved.default.fpr_pct}} de falsas alarmas. Para llegar a un Recall de 0.95, el FPR sube a {{unsw.m.xgb_improved.recall_target.fpr_pct}}. Y si exigimos un FPR de 0.02, el Recall cae a {{unsw.m.xgb_improved.fpr_budget.recall_pct}}.

Ningún modelo cumple la meta completa. La razón se ve en esta gráfica: los normales, en azul, y los ataques, en rojo, se solapan en la franja media, sobre todo en las familias Fuzzers y Analysis. Mover el umbral no separa mejor los grupos: solo decide qué error aceptamos.
:::

::: relevo
**Relevo:** "El otro dataset cuenta una historia distinta."
:::

## Diapositiva 9: resultados en CICIDS2017

<span class="tiempo">0:40</span> **Raul**

::: decir
CICIDS2017 es lo contrario: está saturado. Con el umbral cero punto cinco, todos los modelos cumplen la meta, con un Recall de {{cic.m.xgb_improved.default.recall}} y un FPR de {{cic.m.xgb_improved.default.fpr5}}.

Y aquí descubrimos algo: el criterio literal del proyecto, mínimo FPR con Recall de 0.95, es degenerado. Cuando el modelo es casi perfecto, sacrifica detección hasta 0.95 solo para ahorrar unas pocas falsas alarmas. Los ataques no detectados pasan de {{cic.m.xgb_improved.default.fn}} a {{cic.m.xgb_improved.recall_target.fn}}. Por eso reportamos los tres puntos de operación.
:::

::: relevo
**Relevo:** "Para no quedarnos con una sola partición afortunada, hicimos experimentos formales."
:::

## Diapositiva 10: experimentos formales

<span class="tiempo">0:55</span> **Raul**

::: decir
Repetimos todo con cinco semillas, hicimos pruebas estadísticas pareadas, y probamos las particiones oficiales de UNSW-NB15.

Resultado uno: XGBoost mejorado supera a su versión base en {{unsw.sd.xgb.recall_target.fpr.better}} de {{unsw.sd.n}} semillas. Es una mejora pequeña, pero consistente. En Random Forest y en el Mix, no.

Resultado dos: con la partición oficial de prueba, el FPR sube a {{unsw.o.A_oficial_ingenuo.xgb_baseline.fpr}}. La forma de partir los datos cambia el resultado más que cambiar de modelo.

Resultado tres: quitar las variables sospechosas de ser atajos casi no afecta el rendimiento.
:::

::: relevo
**Relevo a Fabian para la demostración.**
:::

## Diapositiva 11: demostración

<span class="tiempo">0:50</span> **Fabian**

::: decir
Les mostramos el prototipo. Tomamos diez flujos del conjunto de prueba: ocho al azar y dos elegidos a propósito para mostrar errores.

Con el umbral cero punto cinco, el modelo detecta cuatro ataques y deja pasar el tráfico normal. Si bajamos el umbral al del Recall 0.95, aparece una falsa alarma: el flujo ocho. Y hay un ataque de la familia Analysis que ningún umbral detecta.

Esto es lo que vería un analista: una probabilidad y una decisión por cada flujo.
:::

**Pasos de la demostración** (detalle más abajo): ejecutar `predict` con `--operating-point default`, luego con `recall_target`, y señalar el flujo 8 y el flujo 9.

::: relevo
**Relevo a Raul para cerrar.**
:::

## Diapositiva 12: conclusiones

<span class="tiempo">0:50</span> **Raul**

::: decir
Conclusiones.

Uno: XGBoost mejorado ofrece el mejor equilibrio en los dos datasets, y el Mix no aporta ventaja.

Dos: en UNSW-NB15 ningún modelo cumple la meta. Es un límite de los datos, no solo del algoritmo.

Tres: el protocolo de evaluación pesa más que el algoritmo. Duplicados, tipo de partición y punto de operación cambian las cifras más que cambiar de modelo.

Cuatro: el umbral es una decisión de negocio, no de aprendizaje automático.

Como trabajo futuro: repetir la búsqueda de hiperparámetros por semilla, probar con tráfico real y medir la robustez frente a ataques que intenten engañar al modelo.

Gracias. Quedamos atentos a sus preguntas.
:::

# La demostración paso a paso {.sin-salto}

## Antes de entrar al salón

```bash
source .venv/bin/activate
python -m src.predict --dataset unsw_nb15 --input docs/demo/flujos_ejemplo.csv --operating-point default
```

Si imprime una tabla de diez filas, todo funciona. Tengan esa terminal abierta, con letra grande (al menos 18 puntos) y fondo claro u oscuro de alto contraste.

## En vivo

```bash
python -m src.predict --dataset unsw_nb15 --input docs/demo/flujos_ejemplo.csv --operating-point default
python -m src.predict --dataset unsw_nb15 --input docs/demo/flujos_ejemplo.csv --operating-point recall_target
```

Qué señalar, y qué debe verse:

| Qué | Dónde | Debe verse |
|---|---|---|
| Tráfico normal bien clasificado | Filas 0 a 3 | Probabilidades casi cero, "Trafico Normal" |
| Ataques detectados | Filas 4 a 7 | "Ataque Detectado" con probabilidades altas |
| Falsa alarma | Fila 8, solo con `recall_target` | Probabilidad 0.4406 con umbral 0.3383: pasa a "Ataque Detectado" aunque es normal |
| Ataque que se escapa | Fila 9 en ambos | Probabilidad 0.1269: "Trafico Normal" aunque es de la familia Analysis |

La columna `nota` del archivo de ejemplo indica cuáles dos filas se eligieron a propósito; el modelo ignora esa columna.

## Alternativa con interfaz gráfica

```bash
streamlit run app/demo_app.py
```

Pestaña **2. Clasificar en vivo** para los flujos, y pestaña **3. Umbral interactivo** para mover el umbral y ver cómo cambian Recall, FPR y la matriz de confusión.

## Plan B si la demostración falla

No intenten arreglar nada delante del público. Digan: "Les muestro la salida que habíamos guardado" y abran los archivos de `docs/demo/`:

- `salida_esperada_default.txt`
- `salida_esperada_recall_target.txt`
- `salida_esperada_fpr_budget.txt`
- `salida_esperada_json.txt` (un solo flujo)

Contienen exactamente lo que debe imprimir el programa.

# Preguntas probables {.sin-salto}

Respuestas cortas de unos 15 segundos. Las respuestas completas, con argumentos, están en la Guía de estudio, Parte D.

## Para Fabian

**¿Por qué no usaron aprendizaje profundo ni SVM?** El primer entregable los dejaba como complementarios y la docente pidió pocos modelos mejorados. Quisimos profundidad en pocos modelos antes que amplitud.

**¿Es reproducible?** Sí. Descarga con verificación de integridad, semillas fijas, pruebas automáticas y un comando por etapa.

**¿Serviría en producción?** No lo afirmamos. Evaluamos sobre archivos de flujos de laboratorio, no sobre tráfico real ni en vivo, y no medimos resistencia a ataques que intenten evadir al modelo.

## Para Silvana

**¿Por qué quitaron los duplicados?** Porque el mismo flujo en entrenamiento y en prueba hace que el modelo recuerde en vez de generalizar. Lo medimos: en UNSW-NB15 inflaba el Recall.

**¿Perdieron información al eliminar tantos flujos?** Se elimina {{unsw.clean.removed_pct}} de UNSW-NB15, pero son filas repetidas o contradictorias: no aportan información nueva.

**¿Por qué estratificar?** Porque hay familias con muy pocos flujos; sin estratificar podrían quedar solo en entrenamiento o solo en prueba.

## Para Raul

**¿Por qué el FPR de {{unsw.m.xgb_improved.recall_target.fpr_pct}} para llegar a Recall 0.95?** Porque normales y ataques se solapan en UNSW-NB15, sobre todo en Fuzzers y Analysis. Ningún algoritmo comparado lo evita.

**¿Es buena una accuracy de {{unsw.m.xgb_improved.default.accuracy}}?** Depende del costo de cada error. Por eso no la usamos como criterio: reportamos Recall y FPR en tres puntos.

**¿Por qué la versión mejorada no gana siempre?** Gana de forma consistente en XGBoost, pero no en Random Forest ni en el Mix. Y su mejora es pequeña.

**¿Qué significa un p-valor aquí?** Que, si no hubiera diferencia entre dos modelos, sería raro ver una diferencia así solo por el azar del conjunto de prueba. No mide la variación por cambiar de semilla.

**¿Por qué no reprodujeron el 0.97 de Alkhater?** Solo pudimos verificar su resumen, no su preprocesamiento. Medimos que los duplicados explican una parte de la distancia, pero no toda.

# Lista de verificación antes de presentar {.sin-salto}

- [ ] El proyecto funciona en el computador que se va a usar (`python -m pytest` pasa).
- [ ] La terminal está lista, con letra grande, y `source .venv/bin/activate` ya hecho.
- [ ] Los modelos existen (`models/unsw_nb15/best_model.joblib`); si no, entrenar con `python -m src.train --dataset unsw_nb15` (unos 7 minutos) **antes** de la clase.
- [ ] Las diapositivas están exportadas a PDF por si falla el programa de presentación.
- [ ] Los cuatro archivos `salida_esperada_*.txt` están abiertos o a un clic.
- [ ] Cada uno ensayó su parte con cronómetro, y el total no pasa de 10 minutos.
- [ ] Saben quién contesta qué pregunta (sección anterior).
