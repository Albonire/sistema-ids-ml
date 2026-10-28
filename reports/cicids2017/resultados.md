# Resultados: CICIDS2017

Generado por `python -m src.evaluate`. Todas las cifras son del conjunto de prueba (15 % de los datos), que no se usó para ajustar nada: ni hiperparámetros, ni filtro de correlación, ni umbrales, ni la elección del modelo (todo eso se decidió con entrenamiento y validación).

Partición: entrenamiento 1,747,580, validación 374,482, prueba 374,482 (estratificada por tipo de ataque, `random_state=42`).

Los intervalos de confianza (IC 95 %) son bootstrap exacto sobre la matriz de confusión y reflejan solo el ruido de muestreo del conjunto de prueba. Dos modelos con intervalos solapados no deben considerarse distintos.

## 1. Umbral fijo 0.5 (forma habitual en la literatura)

| Modelo | Accuracy | Precisión | Recall | F1 | FPR | FPR IC 95 % | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|
| Random Forest (base) | 0.9991 | 0.9980 | 0.9969 | 0.9975 | 0.0004 | [0.0003, 0.0005] | 0.9999 | 0.9992 |
| Random Forest (mejorado) | 0.9979 | 0.9990 | 0.9884 | 0.9937 | 0.0002 | [0.0002, 0.0003] | 0.9999 | 0.9998 |
| XGBoost (base) | 0.9994 | 0.9984 | 0.9983 | 0.9984 | 0.0003 | [0.0003, 0.0004] | 1.0000 | 0.9999 |
| XGBoost (mejorado) | 0.9995 | 0.9984 | 0.9985 | 0.9984 | 0.0003 | [0.0003, 0.0004] | 1.0000 | 0.9999 |
| Mix RF + XGB (base) | 0.9994 | 0.9984 | 0.9984 | 0.9984 | 0.0003 | [0.0003, 0.0004] | 1.0000 | 1.0000 |
| Mix RF + XGB (mejorado) | 0.9993 | 0.9989 | 0.9971 | 0.9980 | 0.0002 | [0.0002, 0.0003] | 1.0000 | 0.9999 |

## 2. Mínimo FPR con Recall >= 0.95 (criterio de AGENT.md)

El umbral se eligió en validación. Las columnas FP y FN son conteos en prueba.

| Modelo | Umbral | Recall | Recall IC 95 % | FPR | FPR IC 95 % | Precisión | F1 | FP | FN |
|---|---|---|---|---|---|---|---|---|---|
| Random Forest (base) | 1.0000 | 0.9719 | [0.9706, 0.9731] | 0.0001 | [0.0001, 0.0002] | 0.9993 | 0.9854 | 43 | 1793 |
| Random Forest (mejorado) | 0.9484 | 0.9531 | [0.9515, 0.9547] | 0.0002 | [0.0001, 0.0002] | 0.9991 | 0.9756 | 52 | 2993 |
| XGBoost (base) | 0.9912 | 0.9516 | [0.9499, 0.9532] | 0.0000 | [0.0000, 0.0001] | 0.9998 | 0.9751 | 12 | 3085 |
| XGBoost (mejorado) * | 0.9909 | 0.9505 | [0.9488, 0.9522] | 0.0000 | [0.0000, 0.0001] | 0.9998 | 0.9745 | 13 | 3158 |
| Mix RF + XGB (base) | 0.9941 | 0.9510 | [0.9493, 0.9526] | 0.0000 | [0.0000, 0.0001] | 0.9998 | 0.9748 | 12 | 3126 |
| Mix RF + XGB (mejorado) | 0.9693 | 0.9519 | [0.9502, 0.9536] | 0.0001 | [0.0001, 0.0002] | 0.9993 | 0.9750 | 45 | 3066 |

## 3. Máximo Recall con FPR <= 0.02 (presupuesto de falsas alarmas)

El umbral se eligió en validación. Las columnas FP y FN son conteos en prueba.

| Modelo | Umbral | Recall | Recall IC 95 % | FPR | FPR IC 95 % | Precisión | F1 | FP | FN |
|---|---|---|---|---|---|---|---|---|---|
| Random Forest (base) | 0.0100 | 0.9999 | [0.9998, 1.0000] | 0.0133 | [0.0129, 0.0137] | 0.9392 | 0.9686 | 4127 | 5 |
| Random Forest (mejorado) | 0.0293 | 0.9997 | [0.9996, 0.9999] | 0.0197 | [0.0192, 0.0202] | 0.9122 | 0.9540 | 6136 | 16 |
| XGBoost (base) | 0.0064 | 0.9999 | [0.9999, 1.0000] | 0.0033 | [0.0031, 0.0035] | 0.9843 | 0.9920 | 1018 | 4 |
| XGBoost (mejorado) † | 0.0082 | 1.0000 | [0.9999, 1.0000] | 0.0031 | [0.0029, 0.0033] | 0.9849 | 0.9924 | 977 | 3 |
| Mix RF + XGB (base) | 0.0132 | 1.0000 | [0.9999, 1.0000] | 0.0057 | [0.0055, 0.0060] | 0.9728 | 0.9862 | 1781 | 3 |
| Mix RF + XGB (mejorado) | 0.0345 | 1.0000 | [0.9999, 1.0000] | 0.0069 | [0.0066, 0.0072] | 0.9673 | 0.9834 | 2155 | 3 |

`*` = modelo elegido en validación con el criterio de AGENT.md. `†` = modelo con mayor Recall en validación bajo el presupuesto de FPR.

## Modelo seleccionado

Modelo (criterio AGENT.md): XGBoost (mejorado).

| Punto de operación | Recall | FPR | Cumple Recall >= 0.95 y FPR <= 0.02 |
|---|---|---|---|
| umbral 0.5 | 0.9985 | 0.0003 | sí |
| mínimo FPR con Recall >= 0.95 | 0.9505 | 0.0000 | sí |
| máximo Recall con FPR <= 0.02 | 1.0000 | 0.0031 | sí |

## Detección por tipo de ataque (XGBoost (mejorado), prueba)

Proporción de flujos marcados como ataque. En BENIGN es la tasa de falsas alarmas. Las familias con pocos flujos de prueba (columna n) tienen estimaciones muy inestables.

| Tipo | n | umbral 0.5 | Recall >= objetivo | FPR <= presupuesto |
|---|---|---|---|---|
| DDoS | 19202 | 0.9995 | 0.9983 | 0.9999 |
| DoS Hulk | 25905 | 0.9999 | 0.9891 | 1.0000 |
| FTP - Patator | 890 | 0.9989 | 0.9843 | 1.0000 |
| DoS slowloris | 806 | 0.9975 | 0.9826 | 1.0000 |
| SSH - Patator | 483 | 0.9979 | 0.9482 | 1.0000 |
| Web Attack - XSS | 98 | 0.9796 | 0.9184 | 1.0000 |
| DoS GoldenEye | 1542 | 0.9987 | 0.9118 | 1.0000 |
| Web Attack - Brute Force | 220 | 0.9955 | 0.8909 | 1.0000 |
| PortScan | 13519 | 0.9999 | 0.8543 | 1.0000 |
| DoS Slowhttptest | 784 | 1.0000 | 0.4337 | 1.0000 |
| Bot | 292 | 0.7432 | 0.3219 | 0.9966 |
| BENIGN (falsas alarmas) | 310731 | 0.0003 | 0.0000 | 0.0031 |
| Web Attack - Sql Injection | 3 | 1.0000 | 0.0000 | 1.0000 |
| Heartbleed | 2 | 1.0000 | 0.0000 | 1.0000 |
| Infiltration | 5 | 0.8000 | 0.0000 | 0.8000 |

## Figuras

- `figures/confusion_matrices.png`
- `figures/roc.png`
- `figures/precision_recall.png`
- `figures/fpr_recall_comparison.png`
- `figures/detection_by_attack_type.png`
- `figures/feature_importances.png`
