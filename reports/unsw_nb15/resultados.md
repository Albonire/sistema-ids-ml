# Resultados: UNSW-NB15

Generado por `python -m src.evaluate`. Todas las cifras son del conjunto de prueba (15 % de los datos), que no se usó para ajustar nada: ni hiperparámetros, ni filtro de correlación, ni umbrales, ni la elección del modelo (todo eso se decidió con entrenamiento y validación).

Partición: entrenamiento 107,288, validación 22,991, prueba 22,991 (estratificada por tipo de ataque, `random_state=42`).

Los intervalos de confianza (IC 95 %) son bootstrap exacto sobre la matriz de confusión y reflejan solo el ruido de muestreo del conjunto de prueba. Dos modelos con intervalos solapados no deben considerarse distintos.

## 1. Umbral fijo 0.5 (forma habitual en la literatura)

| Modelo | Accuracy | Precisión | Recall | F1 | FPR | FPR IC 95 % | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|
| Random Forest (base) | 0.9180 | 0.9105 | 0.9039 | 0.9072 | 0.0708 | [0.0663, 0.0754] | 0.9808 | 0.9762 |
| Random Forest (mejorado) | 0.9158 | 0.9126 | 0.8960 | 0.9042 | 0.0684 | [0.0641, 0.0730] | 0.9806 | 0.9768 |
| XGBoost (base) | 0.9190 | 0.9214 | 0.8936 | 0.9073 | 0.0607 | [0.0566, 0.0649] | 0.9812 | 0.9775 |
| XGBoost (mejorado) | 0.9215 | 0.9214 | 0.8998 | 0.9104 | 0.0612 | [0.0570, 0.0655] | 0.9823 | 0.9789 |
| Mix RF + XGB (base) | 0.9195 | 0.9184 | 0.8983 | 0.9082 | 0.0636 | [0.0595, 0.0679] | 0.9821 | 0.9787 |
| Mix RF + XGB (mejorado) | 0.9208 | 0.9199 | 0.8999 | 0.9098 | 0.0624 | [0.0582, 0.0668] | 0.9820 | 0.9786 |

## 2. Mínimo FPR con Recall >= 0.95 (criterio de AGENT.md)

El umbral se eligió en validación. Las columnas FP y FN son conteos en prueba.

| Modelo | Umbral | Recall | Recall IC 95 % | FPR | FPR IC 95 % | Precisión | F1 | FP | FN |
|---|---|---|---|---|---|---|---|---|---|
| Random Forest (base) | 0.3400 | 0.9573 | [0.9536, 0.9611] | 0.1382 | [0.1324, 0.1441] | 0.8466 | 0.8986 | 1768 | 435 |
| Random Forest (mejorado) | 0.3510 | 0.9526 | [0.9487, 0.9567] | 0.1323 | [0.1265, 0.1382] | 0.8516 | 0.8993 | 1693 | 483 |
| XGBoost (base) | 0.3354 | 0.9507 | [0.9467, 0.9548] | 0.1290 | [0.1234, 0.1346] | 0.8544 | 0.9000 | 1651 | 503 |
| XGBoost (mejorado) * | 0.3383 | 0.9515 | [0.9476, 0.9557] | 0.1222 | [0.1167, 0.1278] | 0.8612 | 0.9041 | 1564 | 494 |
| Mix RF + XGB (base) | 0.3501 | 0.9538 | [0.9499, 0.9578] | 0.1277 | [0.1221, 0.1336] | 0.8561 | 0.9023 | 1634 | 471 |
| Mix RF + XGB (mejorado) | 0.3495 | 0.9515 | [0.9476, 0.9556] | 0.1261 | [0.1205, 0.1319] | 0.8574 | 0.9020 | 1614 | 494 |

## 3. Máximo Recall con FPR <= 0.02 (presupuesto de falsas alarmas)

El umbral se eligió en validación. Las columnas FP y FN son conteos en prueba.

| Modelo | Umbral | Recall | Recall IC 95 % | FPR | FPR IC 95 % | Precisión | F1 | FP | FN |
|---|---|---|---|---|---|---|---|---|---|
| Random Forest (base) | 0.7500 | 0.8027 | [0.7948, 0.8104] | 0.0183 | [0.0161, 0.0205] | 0.9722 | 0.8794 | 234 | 2011 |
| Random Forest (mejorado) | 0.7239 | 0.8035 | [0.7957, 0.8112] | 0.0180 | [0.0158, 0.0202] | 0.9727 | 0.8801 | 230 | 2003 |
| XGBoost (base) | 0.7288 | 0.8161 | [0.8083, 0.8233] | 0.0180 | [0.0158, 0.0202] | 0.9731 | 0.8877 | 230 | 1875 |
| XGBoost (mejorado) † | 0.7252 | 0.8238 | [0.8163, 0.8311] | 0.0205 | [0.0181, 0.0229] | 0.9697 | 0.8909 | 262 | 1796 |
| Mix RF + XGB (base) | 0.7161 | 0.8198 | [0.8121, 0.8272] | 0.0182 | [0.0161, 0.0204] | 0.9729 | 0.8898 | 233 | 1837 |
| Mix RF + XGB (mejorado) | 0.7193 | 0.8179 | [0.8101, 0.8251] | 0.0181 | [0.0160, 0.0204] | 0.9729 | 0.8887 | 232 | 1857 |

`*` = modelo elegido en validación con el criterio de AGENT.md. `†` = modelo con mayor Recall en validación bajo el presupuesto de FPR.

## Modelo seleccionado

Modelo (criterio AGENT.md): XGBoost (mejorado).

| Punto de operación | Recall | FPR | Cumple Recall >= 0.95 y FPR <= 0.02 |
|---|---|---|---|
| umbral 0.5 | 0.8998 | 0.0612 | no |
| mínimo FPR con Recall >= 0.95 | 0.9515 | 0.1222 | no |
| máximo Recall con FPR <= 0.02 | 0.8238 | 0.0205 | no |

## Detección por tipo de ataque (XGBoost (mejorado), prueba)

Proporción de flujos marcados como ataque. En BENIGN es la tasa de falsas alarmas. Las familias con pocos flujos de prueba (columna n) tienen estimaciones muy inestables.

| Tipo | n | umbral 0.5 | Recall >= objetivo | FPR <= presupuesto |
|---|---|---|---|---|
| Worms | 25 | 1.0000 | 1.0000 | 1.0000 |
| Backdoor | 87 | 1.0000 | 1.0000 | 0.9770 |
| Reconnaissance | 1297 | 0.9954 | 0.9985 | 0.9915 |
| Generic | 1096 | 0.9954 | 0.9973 | 0.9918 |
| DoS | 629 | 0.9809 | 0.9952 | 0.9300 |
| Exploits | 3871 | 0.9791 | 0.9915 | 0.9594 |
| Shellcode | 218 | 0.9541 | 0.9771 | 0.8899 |
| Fuzzers | 2847 | 0.7007 | 0.8581 | 0.4787 |
| Analysis | 125 | 0.5520 | 0.6480 | 0.4800 |
| BENIGN (falsas alarmas) | 12796 | 0.0612 | 0.1222 | 0.0205 |

## Figuras

- `figures/confusion_matrices.png`
- `figures/roc.png`
- `figures/precision_recall.png`
- `figures/fpr_recall_comparison.png`
- `figures/detection_by_attack_type.png`
- `figures/feature_importances.png`
