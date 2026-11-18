# Cómo leer este documento {.sin-salto}

Aquí está **todo lo que debe llevar cada diapositiva** para la sustentación de 10 minutos: el texto exacto, la imagen o gráfica que va, cómo se diseña y qué no poner. Ustedes arman las diapositivas; este documento es el contenido y las instrucciones.

La presentación tiene **12 diapositivas principales** y **4 de respaldo** (se muestran solo si preguntan). Cada diapositiva dice cuánto tiempo dura y quién la expone, igual que el guion.

## La historia en una frase por diapositiva

| N.º | Mensaje de la diapositiva |
|---|---|
| 1 | Los IDS por firmas no ven lo nuevo y se llenan de falsas alarmas |
| 2 | Buscamos el algoritmo que mejor equilibra detectar ataques y no molestar con falsas alarmas |
| 3 | Todo es una tubería reproducible de seis etapas |
| 4 | Dos datasets públicos, muy desbalanceados y con muchas filas repetidas |
| 5 | Quitar duplicados antes de partir evita medir lo que el modelo solo recuerda |
| 6 | Tres modelos, cada uno en versión base y mejorada |
| 7 | La decisión importante es el umbral: usamos tres puntos de operación |
| 8 | En UNSW-NB15 ningún modelo cumple la meta: las clases se solapan |
| 9 | CICIDS2017 está saturado y el criterio literal resulta degenerado |
| 10 | Los experimentos formales confirman a XGBoost y muestran que la partición pesa más que el modelo |
| 11 | Demostración: el mismo modelo con dos umbrales sobre flujos reales |
| 12 | Cuatro conclusiones y por dónde seguir |

## Sistema de diseño

**Principios.** Una idea por diapositiva. Un título que sea una **frase completa con el mensaje** (no "Resultados"). Máximo 40 palabras de texto en pantalla. Si hay una figura, ocupa al menos la mitad de la diapositiva.

| Elemento | Indicación |
|---|---|
| Formato | 16:9 (1920 x 1080 px) |
| Fondo | Blanco o gris muy claro (`#F7F9FD`); sin imágenes de fondo ni plantillas recargadas |
| Tipografía | Inter (o Calibri/Arial si no la tienen): títulos en negrita de 32 a 36 pt, texto de 20 a 24 pt, pie y fuentes de 12 pt. Nada por debajo de 18 pt salvo el pie |
| Colores | Azul `#2A78D6` (principal), naranja `#EB6834` (énfasis), verde `#1BAF7A`, amarillo `#EDA100`, rojo `#D03B3B` (ataque o error), gris `#898781` (secundario), tinta `#1F2430` (texto) |
| Significado de color | **Azul = tráfico normal, rojo = ataque**, igual que en las figuras. No lo cambien entre diapositivas |
| Márgenes | 80 px a cada lado; alinear todo a la misma cuadrícula |
| Figuras | Usar los PNG de `docs/entrega/figuras/` tal cual (ya están en la paleta). Dejar aire alrededor; no estirar |
| Números | Una cifra grande (60 a 80 pt) con una etiqueta corta vale más que una tabla |
| Animación | Solo aparición simple, una cosa por clic. Nada de transiciones llamativas |
| Fuente de datos | Pie de 12 pt: "Fuente: reports/unsw_nb15, conjunto de prueba" donde haya cifras |

::: advertencia
**Qué evitar siempre:** tablas con más de 5 filas, párrafos, viñetas de más de una línea, gráficas sin título, ejes sin unidades, clip art, y cifras con cuatro decimales (redondeen a 2 o 3 en pantalla).
:::

## Figuras ya generadas

Todas están en `docs/entrega/figuras/` y salen de datos reales (se regeneran con `python docs/entrega/make_figures.py`). Las del proyecto están en `reports/<dataset>/figures/`.

| Archivo | Qué muestra | Se usa en |
|---|---|---|
| `ids_en_la_red.png` | Dónde actúa un IDS (esquema) | 1 |
| `arquitectura.png` | Las seis etapas del prototipo | 3 |
| `desbalance_familias.png` | Flujos por familia, ambos datasets | 4 |
| `embudo_limpieza.png` | Qué se elimina en la limpieza | 5 (o respaldo) |
| `fuga_de_datos.png` | Cuánto inflan los duplicados las métricas | 5 |
| `base_vs_mejorada.png` | Las dos versiones de cada modelo | 6 |
| `matrices_confusion_unsw.png` | Un modelo, tres umbrales | 7 y respaldo |
| `distribucion_puntajes_unsw.png` | Solapamiento normales y ataques, con umbrales | 8 |
| `roc_puntos_operacion.png` | ROC con los tres puntos, ambos datasets | 9 |
| `flujo_a_variables.png` | Un flujo real convertido en variables y decisión | 11 |
| `alarmas_por_millon.png` | Aritmética de las falsas alarmas | 12 y respaldo |

# Diapositivas principales {.sin-salto}

## Diapositiva 1: portada y problema {.nueva-pagina}
<span class="tiempo">0:45</span> Fabian

**Título:** Los IDS por firmas no ven lo nuevo y se llenan de falsas alarmas

**Texto en pantalla** (3 viñetas, una línea cada una):

- No detectan ataques que nunca vieron
- Marcan como ataque tráfico legítimo pero raro
- Demasiadas falsas alarmas: el analista deja de creer

**Pie:** Sistema inteligente de detección de intrusiones de red · Silvana, Fabian, Raul · Seguridad Informática · Universidad de Pamplona

**Imagen:** `figuras/ids_en_la_red.png`, a la derecha, ocupando la mitad de la diapositiva.

::: {.figura-mediana}
![Vista previa: dónde actúa un IDS de red.](figuras/ids_en_la_red.png)
:::

**Diseño:** el título arriba a la izquierda, las tres viñetas debajo, el esquema a la derecha. Una franja fina azul bajo el título. Sin logos grandes.

**Alternativa:** si quieren un gancho visual, una captura de una alerta de un SIEM con "3 218 alertas sin revisar" como imagen de fondo muy atenuada (solo si la consiguen con licencia libre).

## Diapositiva 2: pregunta y alcance {.nueva-pagina}
<span class="tiempo">0:45</span> Fabian

**Título:** ¿Qué algoritmo equilibra mejor detectar ataques y no dar falsas alarmas?

**Texto en pantalla:**

- **Recall**: de todos los ataques, ¿cuántos detectamos?
- **FPR**: de todo el tráfico normal, ¿cuánto marcamos por error?
- Meta: **Recall >= 0.95** y **FPR <= 0.02**

**Visual (la dibujan ustedes):** dos tarjetas grandes lado a lado, una verde con "Recall >= 0.95" y otra naranja con "FPR <= 0.02", y debajo una fila de cinco "chips" redondeados: Random Forest, XGBoost, Mix, UNSW-NB15, CICIDS2017.

**Diseño:** las dos tarjetas ocupan el centro, con la cifra a 60 pt. Los chips en gris claro, 20 pt.

**Qué no poner:** las fórmulas. Se explican en la diapositiva 7 y en el respaldo B1.

## Diapositiva 3: arquitectura {.nueva-pagina}
<span class="tiempo">0:45</span> Fabian

**Título:** Una tubería reproducible de seis etapas

**Texto en pantalla:** ninguno aparte del título y un pie: "Un comando por etapa · semillas fijas · pruebas automáticas · integración continua".

**Imagen:** `figuras/arquitectura.png`, a todo el ancho.

::: {.figura-mediana}
![Vista previa de la arquitectura.](figuras/arquitectura.png)
:::

**Diseño:** la figura es la diapositiva. Si quieren dar ritmo, hagan que cada caja aparezca con un clic (de izquierda a derecha) mientras Fabian las nombra.

## Diapositiva 4: los datos {.nueva-pagina}
<span class="tiempo">0:50</span> Silvana

**Título:** Dos datasets públicos, muy desbalanceados y con muchas filas repetidas

**Texto en pantalla:** dos tarjetas con cifras grandes:

- **UNSW-NB15**: {{unsw.clean.rows_raw}} flujos · 9 familias de ataque
- **CICIDS2017**: {{cic.clean.rows_raw}} flujos · 14 familias de ataque

**Imagen:** `figuras/desbalance_familias.png` debajo de las tarjetas.

::: {.figura-mediana}
![Vista previa: flujos por familia.](figuras/desbalance_familias.png)
:::

**Diseño:** las tarjetas arriba (altura de un tercio), la gráfica abajo. Resalten con un círculo rojo la barra de Heartbleed (11 flujos) y escriban "11 flujos" al lado.

**Si les falta espacio:** quiten la barra de CICIDS2017 y dejen solo UNSW-NB15.

## Diapositiva 5: limpieza sin fuga y partición {.nueva-pagina}
<span class="tiempo">0:55</span> Silvana

**Título:** Quitar duplicados antes de partir evita medir lo que el modelo solo recuerda

**Texto en pantalla:**

- UNSW-NB15: {{unsw.clean.dup_pct}} de los flujos eran duplicados
- Prueba ya vista (protocolo ingenuo): **{{unsw.l.naive.leaked_test_share_pct}}**
- Partición 70 / 15 / 15, la prueba no se toca hasta el final

**Imagen:** `figuras/fuga_de_datos.png` (panel izquierdo y central son los importantes).

::: {.figura-mediana}
![Vista previa: efecto de los duplicados.](figuras/fuga_de_datos.png)
:::

**Diseño:** a la izquierda, un diagrama de tres cajas que dibujan ustedes: "Entrenamiento 70 %" (azul), "Validación 15 %" (amarillo), "Prueba 15 %" (rojo, con un candado). A la derecha, la figura. Un cartel naranja: "Recall ingenuo {{unsw.l.naive.recall}} frente a Recall real {{unsw.l.full.recall}}".

**Alternativa:** si prefieren mostrar el proceso de limpieza, usen `figuras/embudo_limpieza.png` en lugar de la figura de fuga y pasen la de fuga al respaldo.

## Diapositiva 6: los modelos {.nueva-pagina}
<span class="tiempo">0:45</span> Silvana

**Título:** Tres modelos, cada uno en versión base y mejorada

**Texto en pantalla:**

- **Random Forest**: muchos árboles votan
- **XGBoost**: árboles en secuencia, cada uno corrige al anterior
- **Mix**: promedio de los dos

**Imagen:** `figuras/base_vs_mejorada.png` en la parte inferior.

::: {.figura-mediana}
![Vista previa: base y mejorada.](figuras/base_vs_mejorada.png)
:::

**Diagrama opcional (lo dibujan ustedes), para la mitad superior:** tres iconos sencillos. A la izquierda, un grupo de 5 árboles pequeños con flechas hacia una urna ("votación"). En el centro, una cadena de 4 árboles que van de grande a pequeño ("corrige errores"). A la derecha, los dos anteriores con una flecha hacia un signo de promedio.

**Diseño:** iconos arriba, diagrama de versiones abajo. Nada de fórmulas ni de nombres de hiperparámetros.

## Diapositiva 7: métricas y puntos de operación {.nueva-pagina}
<span class="tiempo">0:50</span> Raul

**Título:** El umbral es una decisión de negocio: usamos tres puntos de operación

**Texto en pantalla:**

| Punto | Regla |
|---|---|
| Umbral 0.5 | El valor por defecto |
| Criterio del proyecto | Mínimo FPR con Recall >= 0.95 |
| Presupuesto de alertas | Máximo Recall con FPR <= 0.02 |

**Imagen:** `figuras/matrices_confusion_unsw.png`.

::: {.figura-mediana}
![Vista previa: un modelo, tres umbrales.](figuras/matrices_confusion_unsw.png)
:::

**Diseño:** la tabla pequeña a la izquierda y la figura a la derecha. Si la figura queda muy cargada, recorten solo la matriz central y la de la derecha, y dejen la de umbral 0.5 para el respaldo.

**Idea para el expositor:** "bajar el umbral = más detección, más falsas alarmas".

## Diapositiva 8: resultados en UNSW-NB15 {.nueva-pagina}
<span class="tiempo">0:55</span> Raul

**Título:** En UNSW-NB15 ningún modelo cumple la meta: normales y ataques se solapan

**Texto en pantalla:** tres cifras grandes en una fila, cada una con su etiqueta:

| Umbral 0.5 | Recall >= 0.95 | FPR <= 0.02 |
|---|---|---|
| Recall {{unsw.m.xgb_improved.default.recall_pct}} | Recall {{unsw.m.xgb_improved.recall_target.recall_pct}} | Recall {{unsw.m.xgb_improved.fpr_budget.recall_pct}} |
| FPR {{unsw.m.xgb_improved.default.fpr_pct}} | FPR {{unsw.m.xgb_improved.recall_target.fpr_pct}} | FPR {{unsw.m.xgb_improved.fpr_budget.fpr_pct}} |

**Imagen:** `figuras/distribucion_puntajes_unsw.png`.

::: {.figura-mediana}
![Vista previa: distribución de puntajes.](figuras/distribucion_puntajes_unsw.png)
:::

**Diseño:** la figura grande arriba, las tres columnas de cifras debajo, **alineadas bajo la línea de umbral que les corresponde**. Pinten de rojo la fila de FPR del centro (12 %).

**Pie:** Modelo: {{unsw.best}} · Conjunto de prueba · Fuente: reports/unsw_nb15.

## Diapositiva 9: resultados en CICIDS2017 {.nueva-pagina}
<span class="tiempo">0:40</span> Raul

**Título:** CICIDS2017 está saturado y el criterio literal resulta degenerado

**Texto en pantalla:** dos cifras grandes enfrentadas:

- Con umbral 0.5: **{{cic.m.xgb_improved.default.fn}}** ataques no detectados
- Con el criterio literal: **{{cic.m.xgb_improved.recall_target.fn}}** ataques no detectados

**Imagen:** `figuras/roc_puntos_operacion.png`, mostrando el panel derecho (CICIDS2017).

::: {.figura-mediana}
![Vista previa: curva ROC con los tres puntos.](figuras/roc_puntos_operacion.png)
:::

**Diseño:** las dos cifras a la izquierda, con una flecha roja hacia arriba entre ellas; la curva a la derecha. Texto pequeño: "Por eso reportamos tres puntos de operación".

## Diapositiva 10: experimentos formales {.nueva-pagina}
<span class="tiempo">0:55</span> Raul

**Título:** XGBoost mejorado gana de forma consistente; la partición pesa más que el modelo

**Texto en pantalla:** tres tarjetas:

1. **{{unsw.sd.xgb.recall_target.fpr.better}} de {{unsw.sd.n}} semillas**: XGBoost mejorado supera a su base
2. **FPR {{unsw.o.A_oficial_ingenuo.xgb_baseline.fpr}}** con la partición oficial de prueba (con partición aleatoria: {{unsw.m.xgb_improved.default.fpr}})
3. **Sin atajos**: quitar TTL y `state` casi no cambia el resultado

**Imagen:** a la derecha, `reports/unsw_nb15/figures/pairwise.png` (diferencias pareadas) recortada.

::: {.figura-mediana}
![Vista previa: pruebas pareadas.](../../reports/unsw_nb15/figures/pairwise.png)
:::

**Diseño:** tres tarjetas en columna, la figura a la derecha. Las tarjetas con un número de 48 pt y una línea de texto.

## Diapositiva 11: demostración {.nueva-pagina}
<span class="tiempo">0:50</span> Fabian

**Título:** Un flujo real, el mismo modelo y dos umbrales

**Texto en pantalla:** ninguno; la demostración manda.

**Imagen:** a la izquierda, `figuras/flujo_a_variables.png`; a la derecha, la terminal en vivo (o la captura de la salida guardada).

::: {.figura-mediana}
![Vista previa: un flujo real y la decisión del modelo.](figuras/flujo_a_variables.png)
:::

**Diseño:** dejar la mitad derecha libre para pegar o proyectar la terminal. Resalten con un recuadro amarillo, en la captura, la fila 8 (falsa alarma) y la fila 9 (ataque que se escapa).

**Captura de respaldo:** tomen una captura de pantalla de la salida de `--operating-point recall_target` y pónganla como imagen en esta diapositiva, para no depender del computador.

## Diapositiva 12: conclusiones {.nueva-pagina}
<span class="tiempo">0:50</span> Raul

**Título:** Cuatro conclusiones y por dónde seguir

**Texto en pantalla:**

1. **XGBoost mejorado** equilibra mejor; el Mix no aporta
2. En UNSW-NB15 **ningún modelo cumple la meta**: es un límite de los datos
3. **El protocolo pesa más que el algoritmo**: duplicados, partición, umbral
4. **El umbral es una decisión de negocio**

**Pie:** Trabajo futuro: repetir la búsqueda por semilla · tráfico real · robustez ante evasión

**Imagen:** opcional, `figuras/alarmas_por_millon.png` pequeña, a la derecha, como "por qué importa".

::: {.figura-mediana}
![Vista previa: aritmética de las falsas alarmas.](figuras/alarmas_por_millon.png)
:::

**Diseño:** las cuatro conclusiones con números grandes de colores (azul, naranja, verde, amarillo). Cerrar con "Gracias" y los tres nombres.

# Diapositivas de respaldo {.sin-salto}

Solo se muestran si preguntan. Ténganlas al final, detrás de una diapositiva gris que diga "Respaldo".

## Respaldo B1: de la matriz de confusión a cada métrica {.nueva-pagina}
**Para qué:** si preguntan qué es Recall, FPR o precisión.

**Contenido:** la matriz de confusión de `figuras/matrices_confusion_unsw.png` (la del umbral 0.5) con las cuatro celdas rotuladas VP, FP, VN y FN, y al lado las fórmulas:

$$\mathrm{Recall}=\frac{VP}{VP+FN}\qquad \mathrm{FPR}=\frac{FP}{FP+VN}\qquad \mathrm{Precisi\acute{o}n}=\frac{VP}{VP+FP}$$

**Ejemplo con números** (UNSW-NB15, umbral 0.5, prueba): VP = {{unsw.m.xgb_improved.default.tp}}, FN = {{unsw.m.xgb_improved.default.fn}}, FP = {{unsw.m.xgb_improved.default.fp}}, VN = {{unsw.m.xgb_improved.default.tn}}; por tanto Recall = {{unsw.m.xgb_improved.default.recall}} y FPR = {{unsw.m.xgb_improved.default.fpr}}.

## Respaldo B2: semillas y pruebas pareadas {.nueva-pagina}
**Para qué:** si preguntan cómo se sabe que la mejora es real, o por qué una sola semilla no basta.

**Contenido:** la tabla de diferencias por semilla (mejorada menos base), recortada a las filas de XGBoost:

{{>tabla_diferencias_semillas unsw}}

**Frase clave:** "Comparar dos intervalos sueltos puede ocultar una diferencia real; la prueba pareada y las semillas no."

## Respaldo B3: particiones oficiales y el 0.97 de Alkhater {.nueva-pagina}
**Para qué:** si preguntan por qué no obtuvieron el 0.97 de la literatura.

**Contenido:** la tabla de particiones oficiales:

{{>tabla_oficial}}

**Frase clave:** "Los duplicados explican una parte de la distancia, pero no toda. No conocemos el preprocesamiento de ese estudio: solo verificamos su resumen."

## Respaldo B4: limitaciones y correcciones al Entregable 1 {.nueva-pagina}
**Para qué:** si preguntan por los límites del trabajo, o por qué los números no coinciden con el primer entregable.

**Limitaciones (viñetas):**

- La búsqueda de hiperparámetros no se repitió por semilla
- Dos datasets de laboratorio, con errores de etiquetado documentados
- Archivos de flujos históricos: sin tráfico en vivo ni medición de latencia
- Sin evaluación de resistencia a ataques que intenten engañar al modelo

**Correcciones al Entregable 1:**

- El Entregable 1 cita 2 540 044 registros de UNSW-NB15: es el dataset completo. Los archivos usados tienen {{unsw.clean.rows_raw}} flujos
- Las nueve categorías reales de UNSW-NB15 son Fuzzers, Analysis, Backdoor, DoS, Exploits, Generic, Reconnaissance, Shellcode y Worms
- No se aplicó SMOTE: el umbral elegido en validación ya controla el compromiso

# Imágenes y diagramas que deben crear ustedes {.sin-salto}

Las figuras de datos ya existen. Estos son los elementos que conviene dibujar para que la presentación no sea solo gráficas. Todos se pueden hacer con formas básicas en PowerPoint, Canva o Google Slides.

| Elemento | Diapositiva | Cómo hacerlo |
|---|---|---|
| Tarjetas de meta | 2 | Dos rectángulos redondeados de 600 x 300 px, verde y naranja, con el texto a 60 pt en blanco |
| Chips de modelos y datasets | 2 | Cinco rectángulos redondeados pequeños, gris claro, texto de 20 pt |
| Esquema de partición 70/15/15 | 5 | Una barra horizontal dividida en tres tramos proporcionales (azul, amarillo, rojo) con un candado sobre el rojo |
| Iconos de árboles | 6 | Un triángulo verde sobre un rectángulo marrón corto; repetirlo 5 veces para el bosque y en tamaños decrecientes para el boosting |
| Deslizador de umbral | 7 | Una barra horizontal con un círculo naranja; a la izquierda "más detección, más falsas alarmas", a la derecha lo contrario |
| Tarjetas de cifras | 8, 9, 10 | Rectángulo con la cifra a 48 a 60 pt y una etiqueta de 18 pt debajo |
| Captura de terminal | 11 | Captura de `salida_esperada_recall_target.txt` abierto en una terminal con letra grande |

# Lista de verificación antes de entregar las diapositivas {.sin-salto}

- [ ] Cada título es una frase con mensaje, no una etiqueta.
- [ ] Ninguna diapositiva tiene más de 40 palabras (sin contar el pie).
- [ ] Todo texto es de al menos 18 pt.
- [ ] Azul significa normal y rojo significa ataque en todas las figuras.
- [ ] Cada cifra tiene su punto de operación y su fuente en el pie.
- [ ] Ninguna cifra tiene cuatro decimales en pantalla.
- [ ] Las figuras no están estiradas ni borrosas (usar los PNG originales).
- [ ] Hay una captura de respaldo de la demostración dentro de la diapositiva 11.
- [ ] El archivo se exportó también a PDF.
- [ ] Se ensayó con cronómetro y no pasa de 10 minutos.
