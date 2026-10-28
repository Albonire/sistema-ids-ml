# Fase 2: Modelos, evaluación e inferencia

Documento técnico de la fase de entrenamiento (Entregable 2). Resume qué se decidió, qué se midió y qué se puede y no se puede concluir. Las tablas completas están en `reports/<dataset>/resultados.md` y todo se reproduce con los comandos de la sección 8.

## 1. Alcance y decisiones

El Entregable 1 presentado a la docente y `AGENT.md` diferían en dataset, modelos y partición. Se resolvió así:

| Tema | Entregable 1 | AGENT.md (antes) | Decisión |
|---|---|---|---|
| Dataset | UNSW-NB15 (principal) | CICIDS2017 | Ambos: UNSW-NB15 como principal y CICIDS2017 como contraste. |
| Modelos | RF y XGBoost (núcleo), SVM y red neuronal (complementarios) | RF, SVM, CART, MLP | RF, XGBoost y su mezcla (votación suave). La docente pidió pocos modelos y que lo distintivo sea mejorar lo reportado en los antecedentes. |
| Partición | 70/15/15 y validación cruzada de 5 folds | 70/30 | 70/15/15 estratificada y validación cruzada de 5 folds para hiperparámetros. |

Cada modelo se entrena en dos versiones sobre la misma partición:

- **Base**: la configuración del Entregable 1, sección 8.4 (RF con 100 árboles; XGBoost con 100 árboles y profundidad 5) y umbral 0.5.
- **Mejorada**: filtro de correlación (|r| > 0.95) y búsqueda aleatoria de hiperparámetros con validación cruzada estratificada de 5 folds (8 candidatos, sobre una muestra estratificada de 60.000 flujos de entrenamiento; el modelo final se reentrena con todo el entrenamiento).

El **mix** promedia las probabilidades de ataque de RF y XGBoost de la misma versión, sin reentrenar.

## 2. Protocolo (qué evita la fuga de datos)

1. Limpieza antes de partir: se quitan infinitos y NaN, duplicados (por características y etiqueta binaria, tras convertir a `float32`) y vectores con etiqueta normal y de ataque a la vez.
2. Partición estratificada por tipo de ataque, `random_state=42`. El conjunto de prueba no interviene en ninguna decisión.
3. Todo lo que aprende de los datos se ajusta sin la prueba: filtro de correlación y codificador (solo entrenamiento), hiperparámetros (validación cruzada dentro del entrenamiento), umbrales y elección del modelo (validación).
4. Los intervalos de confianza de las tablas son bootstrap exacto sobre la matriz de confusión: reflejan el ruido de muestreo de la prueba, no la variación por azar del entrenamiento (una sola semilla).

Tres **puntos de operación**, con el umbral siempre elegido en validación:

| Punto | Regla | Para qué sirve |
|---|---|---|
| Umbral 0.5 | Fijo | Es lo que reporta casi toda la literatura. |
| Mínimo FPR con Recall >= 0.95 | Criterio literal de `AGENT.md` | Selección oficial del modelo. |
| Máximo Recall con FPR <= 0.02 | Presupuesto de falsas alarmas | Complementa el criterio: modela un SOC con capacidad limitada de revisar alertas. |

El tercero se agregó porque el criterio literal se comporta mal en los extremos (sección 5).

## 3. Resultados en UNSW-NB15 (prueba: 10.195 ataques y 12.796 flujos normales)

Mejor modelo por el criterio de `AGENT.md`: **XGBoost mejorado**. Su desempeño en los tres puntos:

| Punto de operación | Recall | FPR | Precisión | Ataques no detectados | Falsas alarmas |
|---|---|---|---|---|---|
| Umbral 0.5 | 0.8998 | 0.0612 | 0.9214 | 1.022 | 783 |
| Mínimo FPR con Recall >= 0.95 | 0.9515 | 0.1222 [0.1167, 0.1278] | 0.8612 | 494 | 1.564 |
| Máximo Recall con FPR <= 0.02 | 0.8238 | 0.0205 | 0.9698 | 1.796 | 262 |

Con umbral 0.5 la accuracy de XGBoost mejorado es 0.9215 y el ROC-AUC 0.9823.

Comparación entre los seis modelos (prueba):

- Con umbral 0.5, las seis accuracy están entre 0.9158 y 0.9215 y los ROC-AUC entre 0.9806 y 0.9823. Las diferencias son del orden del ruido de muestreo.
- Con Recall >= 0.95, el FPR va de 0.1222 (XGBoost mejorado) a 0.1382 (RF base). Los intervalos de confianza se solapan en casi todos los pares, por lo que **no se puede afirmar** que la versión mejorada supere a la base en UNSW-NB15.
- Con FPR <= 0.02, el mejor Recall es 0.8238 (XGBoost mejorado) y el peor 0.8027 (RF base). El umbral se fija en validación, por lo que en prueba el FPR de XGBoost mejorado es 0.0205 (IC 95 %: 0.0181 a 0.0229), ligeramente sobre el presupuesto pero compatible con él.
- **Ningún modelo cumple Recall >= 0.95 y FPR <= 0.02 en ningún punto de operación.** Pasar de FPR 2 % a Recall 95 % cuesta multiplicar las falsas alarmas por seis.
- Por familia (XGBoost mejorado, umbral del criterio): Worms, Backdoor, Reconnaissance, Generic, DoS y Exploits se detectan por encima de 0.99. **Fuzzers (0.86) y Analysis (0.65)** concentran los errores, y con el presupuesto de FPR de 2 % bajan a 0.48 cada una. Las variables más importantes son `state_INT` (0.41), `sttl` (0.19) y `ct_state_ttl` (0.14); que `sttl` sea decisiva coincide con lo que reporta Alkhater (2026).

## 4. Resultados en CICIDS2017 (prueba: 63.751 ataques y 310.731 flujos normales)

Mejor modelo por el criterio de `AGENT.md`: **XGBoost mejorado** (también el mejor con el presupuesto de FPR).

| Punto de operación | Recall | FPR | Ataques no detectados | Falsas alarmas |
|---|---|---|---|---|
| Umbral 0.5 | 0.9985 | 0.0003 | 97 | 102 |
| Mínimo FPR con Recall >= 0.95 | 0.9505 | 0.00004 | 3.158 | 13 |
| Máximo Recall con FPR <= 0.02 | 1.0000 | 0.0031 | 3 | 977 |

- Con umbral 0.5 los seis modelos tienen accuracy entre 0.9979 y 0.9995 y ROC-AUC entre 0.9999 y 1.0000. El dataset está **saturado**: las diferencias entre modelos son de decenas de flujos sobre 374.482.
- Todos los modelos cumplen Recall >= 0.95 y FPR <= 0.02 con umbral 0.5.
- La versión mejorada de RF es **peor** que la base con umbral 0.5 (Recall 0.9884 contra 0.9969): la búsqueda sobre una muestra de 60.000 flujos eligió profundidad máxima 12, que limita el modelo al entrenar con 1,7 millones. Es un límite del método (ajustar en una muestra) y no se corrigió.
- Por familia con umbral 0.5, el punto débil es Bot (0.74); con el umbral del criterio literal, además Slowhttptest (0.43), PortScan (0.85) y Bot (0.32). Heartbleed (2 flujos de prueba), Infiltration (5) y SQL Injection (3) tienen soporte demasiado pequeño para sacar conclusiones.

## 5. Lectura crítica

**Sobre la pregunta de investigación.** XGBoost (base o mejorado) ofrece el mejor equilibrio entre detección y falsas alarmas en ambos datasets: bajo la misma restricción (mismo Recall mínimo o mismo presupuesto de FPR) iguala o supera a RF. El mix no aporta una ventaja demostrable sobre XGBoost solo. La mejora es pequeña o inexistente dentro del ruido (UNSW-NB15) o irrelevante por saturación (CICIDS2017). La conclusión defendible no es "nuestro modelo mejorado es mejor", sino que **con evaluación sin fuga, en UNSW-NB15 ningún algoritmo de los comparados alcanza el objetivo del proyecto** y que la elección del algoritmo importa menos que el punto de operación y la calidad de los datos.

**El criterio literal de AGENT.md es degenerado en los extremos.** "Mínimo FPR con Recall >= 0.95" empuja el Recall hasta 0.95 aunque el modelo pueda dar 0.998: en CICIDS2017 baja las falsas alarmas de 102 a 13 pero multiplica por 33 los ataques no detectados (de 97 a 3.158). En UNSW-NB15 el criterio es inalcanzable junto con FPR <= 0.02. Se recomienda que el informe final use el criterio completo (Recall >= 0.95 **y** FPR <= 0.02) y reporte la curva ROC, no un solo umbral.

**Qué hace distinto este trabajo respecto a los antecedentes.** Ver `docs/antecedentes_resultados.md`. Alkhater (2026) reporta accuracy 0.97 y AUC 0.98 con XGBoost en UNSW-NB15; aquí XGBoost obtiene accuracy 0.92 y AUC 0.98 con el protocolo sin fuga. El AUC coincide; la accuracy no. No se puede atribuir la diferencia a un solo factor, porque no se tuvo acceso al detalle del preprocesamiento de ese estudio; lo que sí se midió es el efecto de los duplicados (sección 6).

## 6. Ablación: cuánto inflan los duplicados las métricas

`python -m src.leakage_ablation --dataset <dataset>` entrena el XGBoost base bajo tres protocolos y mide qué parte de la prueba tiene un vector idéntico en entrenamiento.

| Dataset | Protocolo | Filas | Prueba con vector repetido en entrenamiento | Accuracy | Recall | FPR |
|---|---|---|---|---|---|---|
| UNSW-NB15 | Ingenuo (solo inf/NaN) | 257.673 | 44,5 % | 0.9450 | 0.9500 | 0.0639 |
| UNSW-NB15 | Sin duplicados | 154.098 | 0,3 % | 0.9179 | 0.8908 | 0.0605 |
| UNSW-NB15 | Completo (proyecto) | 153.270 | 0 % | 0.9190 | 0.8936 | 0.0607 |
| CICIDS2017 | Ingenuo | 2.827.876 | 13,9 % | 0.99927 | 0.99883 | 0.00062 |
| CICIDS2017 | Sin duplicados | 2.497.980 | 0,04 % | 0.99919 | 0.99851 | 0.00067 |
| CICIDS2017 | Completo (proyecto) | 2.496.544 | 0 % | 0.99944 | 0.99827 | 0.00032 |

En UNSW-NB15 el protocolo ingenuo sobrestima la accuracy en 2,6 puntos y el Recall en 5,6 puntos, porque casi la mitad de la prueba son vectores ya vistos. En CICIDS2017 el efecto es despreciable porque el dataset ya está saturado. El FPR más bajo del protocolo completo en CICIDS2017 se debe a que se eliminan los vectores contradictorios.

Limitación: es una sola semilla y un solo modelo, por lo que sirve como evidencia de magnitud, no como prueba estadística.

## 7. Limitaciones

- Una sola partición y una sola semilla: los intervalos cubren el muestreo de la prueba, no la varianza del entrenamiento.
- La búsqueda de hiperparámetros es acotada (8 candidatos, muestra de 60.000 flujos) por tiempo de cómputo.
- Los problemas de etiquetado y construcción de flujos de CICIDS2017 (Engelen et al., 2021; Lanvin et al., 2023) no se corrigen aquí.
- Las variables con mayor importancia en UNSW-NB15 (`state_INT`, `sttl`, `ct_state_ttl`) pueden reflejar el montaje del laboratorio y no el comportamiento del ataque; no se hizo ablación de variables.
- La evaluación es sobre archivos históricos de flujos, no sobre captura de tráfico en vivo (fuera de alcance según el Entregable 1).

## 8. Discrepancias detectadas en el Entregable 1

Se detectaron al contrastarlo con los datos; el documento ya fue entregado, pero conviene corregirlo en el informe final:

- Sección 5.3 y 7.1 citan 2.540.044 registros de UNSW-NB15. Esa cifra es del dataset completo (cuatro CSV). Los archivos usados por el proyecto son las particiones oficiales de entrenamiento y prueba: 175.341 y 82.332 flujos, 257.673 en total (la página oficial del dataset da las tres cifras).
- Sección 5.3 enumera las categorías de ataque de UNSW-NB15 como "backdoor, DoS, exploits, análisis de reconocimiento, shellcode, desbordamiento de buffer, phishing, fuerza bruta y XSS". Las nueve categorías reales, tanto en la página oficial como en los datos, son Fuzzers, Analysis, Backdoor, DoS, Exploits, Generic, Reconnaissance, Shellcode y Worms.
- Las secciones 4.2 y 8.2 proponen balanceo de clases con SMOTE. No se aplicó: el desbalance de UNSW-NB15 es moderado (56 % normal) y el umbral elegido en validación ya controla el compromiso entre falsas alarmas y detección. Si se aplicara, tendría que ser solo sobre el entrenamiento, nunca antes de partir.

## 9. Reproducción

```bash
pip install -r requirements-dev.txt
python -m src.download_data --dataset all
python -m src.preprocess --dataset all
python -m src.train --dataset unsw_nb15        # unos 7 minutos con 4 CPU
python -m src.train --dataset cicids2017       # unos 25 minutos con 4 CPU
python -m src.leakage_ablation --dataset unsw_nb15
python -m src.leakage_ablation --dataset cicids2017
python -m src.evaluate --dataset unsw_nb15
python -m src.evaluate --dataset cicids2017
python -m src.predict --dataset unsw_nb15 --input flujos.csv --operating-point fpr_budget
pytest -q
```

`python -m src.train --dataset <dataset> --rescore` recalcula umbrales, métricas y modelo elegido a partir de los puntajes guardados, sin reentrenar, si cambian los criterios de decisión.
