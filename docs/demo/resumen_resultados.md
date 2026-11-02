# Resumen de resultados (una página)

Sistema de detección de intrusiones con aprendizaje automático. Cifras en el conjunto de prueba (15 % de los datos, no usado para ajustar nada). Detalle en `docs/fase2_modelos.md` y `reports/<dataset>/resultados.md`.

## Qué se hizo

- Datos: UNSW-NB15 (257.673 flujos crudos, 153.270 tras depurar) y CICIDS2017 (2.830.743 crudos, 2.496.544 tras depurar). Se eliminaron infinitos, duplicados y vectores contradictorios antes de partir los datos.
- Modelos: Random Forest, XGBoost y su mezcla por votación suave, cada uno en versión base y mejorada (filtro de correlación, hiperparámetros por validación cruzada de 5 folds, umbral elegido en validación).
- Partición 70/15/15 estratificada, `random_state=42`. Intervalos de confianza bootstrap en las tablas.

## Resultado principal

| Dataset | Mejor modelo | Umbral 0.5 (Recall / FPR) | Mínimo FPR con Recall >= 0.95 | Máximo Recall con FPR <= 0.02 |
|---|---|---|---|---|
| UNSW-NB15 | XGBoost mejorado | 0.8998 / 0.0612 | 0.9515 / 0.1222 | 0.8238 / 0.0205 |
| CICIDS2017 | XGBoost mejorado | 0.9985 / 0.0003 | 0.9505 / 0.00004 | 1.0000 / 0.0031 |

Cada celda es Recall / FPR del mismo modelo en un punto de operación distinto.

## Conclusiones

1. XGBoost (base o mejorado) ofrece el mejor equilibrio entre detección y falsas alarmas en ambos datasets; la mezcla con Random Forest no aporta una ventaja demostrable.
2. En UNSW-NB15 **ningún modelo cumple Recall >= 0.95 y FPR <= 0.02**. Subir el Recall de 0.82 a 0.95 multiplica las falsas alarmas por seis. Los errores se concentran en las familias Fuzzers y Analysis.
3. CICIDS2017 está saturado (todos los modelos superan el criterio con umbral 0.5), por lo que discrimina poco entre algoritmos.
4. Evaluar sin fuga de datos cambia las cifras: con un protocolo ingenuo, el 44,5 % de la prueba de UNSW-NB15 son vectores repetidos de entrenamiento y el Recall se sobrestima en 5,6 puntos (0.950 frente a 0.894).

## Advertencias

- La versión "mejorada" no supera de forma demostrable a la base en UNSW-NB15 (intervalos solapados) ni en CICIDS2017 (saturación).
- Una sola semilla y una sola partición; la búsqueda de hiperparámetros es acotada.
- El criterio literal "mínimo FPR con Recall >= 0.95" es degenerado cuando el modelo es casi perfecto: en CICIDS2017 sacrifica Recall de 0.9985 a 0.9505 (los ataques no detectados pasan de 97 a 3.158). Por eso se reportan tres puntos de operación.
- CICIDS2017 tiene errores de etiquetado y de construcción de flujos documentados (Engelen et al., 2021), no corregidos aquí.
