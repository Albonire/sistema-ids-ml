# Antecedentes verificados y protocolo de comparación

Este documento reúne los antecedentes que se pueden comparar con los resultados del proyecto, qué se verificó de cada uno y cómo. Las cifras de la literatura son de otros protocolos, por lo que se usan como contexto y no como una tabla de posiciones.

## 1. Qué se verificó y cómo

| Referencia | Qué se usa | Cómo se verificó |
|---|---|---|
| Alkhater, N. (2026). A rigorous comparative study of supervised machine learning techniques for network anomaly detection: Empirical insights from the UNSW-NB15 dataset. *Computers*, 15(5), 285. DOI 10.3390/computers15050285 | Compara Decision Tree, Random Forest, SVM y XGBoost en UNSW-NB15 con validación cruzada estratificada de 5 folds. XGBoost fue el mejor (accuracy 0.97, AUC 0.98). Variables más influyentes: `sttl`, `sload` y `dload`. | Resumen obtenido de la API de Crossref. El texto completo no fue accesible (el editor bloquea el acceso automático), por lo que no se citan cifras por modelo ni detalles del preprocesamiento. |
| Engelen, G., Rimmer, V. y Joosen, W. (2021). Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study. *2021 IEEE Security and Privacy Workshops (SPW)*, pp. 7-12. DOI 10.1109/SPW53761.2021.00009 | Errores en CICIDS2017 y desempeño de Random Forest por clase. | PDF leído completo. Las cifras de abajo se copiaron de su Tabla I y Tabla II. |
| Lanvin, M., Gimenez, P.-F., Han, Y., Majorczyk, F., Mé, L. y Totel, E. (2023). Errors in the CICIDS2017 dataset and the significant differences in detection performances it makes. CRiSIS 2022, *Lecture Notes in Computer Science*, Springer, pp. 18-33. HAL hal-03775466 | Fallos de etiquetado y de captura (paquetes desordenados, duplicados, ataques ejecutados pero mal etiquetados). | Solo resumen indexado (HAL y portal de IP Paris). No se citan cifras. |
| Moustafa, N. y Slay, J. (2015). UNSW-NB15: a comprehensive data set for network intrusion detection systems. *2015 Military Communications and Information Systems Conference (MilCIS)*. DOI 10.1109/MilCIS.2015.7348942 | Origen del dataset. | Metadatos verificados en Crossref. |
| Sharafaldin, I., Habibi Lashkari, A. y Ghorbani, A. A. (2018). Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization. ICISSP 2018. | Origen de CICIDS2017. | Cita indicada por los autores del dataset. |

## 2. Lo que dice Engelen et al. (2021) sobre CICIDS2017 (verificado)

- Más del 20 % de las trazas originales se reconstruyen o reetiquetan al corregir el proceso de generación de flujos.
- Los "apéndices TCP" (flujos espurios de ACK y FIN al final de una conexión) son el 25.9 % del dataset.
- Con Random Forest y partición 75/25, la métrica agregada es igual en el dataset original y en el corregido (accuracy 0.99, F1 ponderado 0.99), pero por clase el resultado original es muy desigual. Ejemplos del dataset original (F1): Bot 0.60, Web Attack XSS 0.18, Web Attack SQL 0.11, Infiltration 0.81, Heartbleed 0.77, Web Brute Force 0.77. Los propios autores advierten que las clases XSS, SQL, Infiltration y Heartbleed tienen conjuntos de prueba extremadamente pequeños.
- Detectan aprendizaje por atajos (*shortcut learning*): el modelo usa variables sin relación semántica con el ataque (`Fwd Header Len`, `Total Fwd Pkt`, `Min Seg Size Fwd`, `Init Win bytes Fwd`, `SYN Flag Count`, `Bwd Pkt Len Mean`).
- Conclusión directa para este proyecto: las métricas agregadas sobre datasets desbalanceados son inadecuadas para juzgar un IDS, por lo que se reporta además la detección por familia de ataque y el FPR con intervalos de confianza.

## 3. Qué hace distinto este proyecto frente a los antecedentes

Se compara cada algoritmo en una versión **base** (la configuración del Entregable 1, sección 8.4: Random Forest con 100 árboles, XGBoost con 100 árboles y profundidad 5, umbral 0.5) y una **mejorada**:

1. **Evaluación sin fuga de datos**: se eliminan duplicados y vectores con etiquetas contradictorias antes de partir; filtro de correlación, codificador, hiperparámetros y umbrales se ajustan solo con entrenamiento y validación; el conjunto de prueba (15 %) no interviene en ninguna decisión.
2. **Filtro de correlación** (|r| > 0.95) para quitar variables redundantes.
3. **Hiperparámetros por validación cruzada estratificada de 5 folds** (búsqueda aleatoria, métrica: precisión promedio).
4. **Umbral de decisión elegido en validación** según el criterio del proyecto, en lugar del 0.5 fijo, y un segundo punto de operación con presupuesto de falsas alarmas.
5. **Intervalos de confianza bootstrap** para el FPR y el Recall, de modo que no se interprete como mejora una diferencia que es ruido.

La sección 4 cuantifica el efecto de (1) con una ablación reproducible (`python -m src.leakage_ablation`).

## 4. Resultados del proyecto y lectura crítica

Ver `reports/<dataset>/resultados.md`, `reports/<dataset>/leakage_ablation.json` y `docs/fase2_modelos.md`.
