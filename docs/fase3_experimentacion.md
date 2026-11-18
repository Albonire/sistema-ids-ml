# Fase 3: Experimentación formal

Resume qué experimentos se hicieron para cerrar el proyecto, cómo repetirlos y cómo leerlos. Las cifras no se copian aquí: están en `reports/<dataset>/experimentos.md`, que se genera automáticamente, y se interpretan en el informe final (`docs/entrega/`).

## Por qué hizo falta

Las fases 1 y 2 dejaron cuatro dudas abiertas: todo salía de una sola semilla; las diferencias entre modelos se juzgaban comparando intervalos de confianza sueltos; no se había probado la partición oficial de UNSW-NB15; y se sospechaba que algunas variables (TTL, `state`, `Destination Port`) actuaban como atajos.

## Experimentos

| Tarea | Comando | Salida en `reports/<dataset>/` |
|---|---|---|
| Cinco semillas | `python -m src.experiments --dataset <d> --task seeds` | `multiseed.csv`, `multiseed_summary.csv`, `multiseed_summary.json`, `multiseed_differences.csv` |
| Diferencias por semilla | `... --task differences` | `multiseed_differences.csv` |
| Pruebas pareadas | `... --task pairwise` | `pairwise_tests.csv` |
| Particiones oficiales (solo UNSW-NB15) | `... --task official` | `official_partitions.csv` |
| Ablación de variables | `... --task features` | `feature_ablation.csv` |
| Todo | `... --task all` | todos los anteriores |
| Reporte en español | `python -m src.experiments_report --dataset <d>` | `experimentos.md` y figuras |

La tarea de semillas guarda cada semilla al terminarla (`multiseed.partial.csv`) y, si se interrumpe, la siguiente ejecución continúa donde quedó.

## Cómo leerlos

- **Semillas.** Cada celda es media ± desviación estándar sobre las semillas. Las versiones mejoradas reutilizan los hiperparámetros de la búsqueda con la semilla 42, de modo que la desviación **no incluye** la variación de repetir la búsqueda, y los datos de ajuste de la semilla 42 se solapan con las pruebas de las otras semillas.
- **Diferencias por semilla.** Mejorada menos base, emparejada por semilla; una semilla "gana" si la métrica que define el punto de operación mejora.
- **Pruebas pareadas.** Bootstrap sobre las mismas filas de prueba, cada modelo con su umbral. Detecta diferencias que dos intervalos separados ocultan. Solo mide el ruido de muestreo de la prueba.
- **Particiones oficiales.** Protocolo A (archivos tal cual), B (depurados y sin vectores repetidos entre entrenamiento y prueba) y C (validación cruzada de 5 folds sobre el entrenamiento oficial, sin depurar y depurada). El espejo de datos intercambia los nombres de los archivos: la partición de entrenamiento es la de mayor tamaño.
- **Ablación.** Si el rendimiento no baja al quitar un grupo de variables, no depende de él; no prueba que el modelo no use atajos, porque variables correlacionadas pueden ocupar su lugar.

## Correcciones a lo dicho en la fase 2

La fase 2 concluyó, con una semilla y comparando intervalos separados, que la mejora de la versión mejorada no era demostrable. Las pruebas pareadas y las cinco semillas de esta fase la corrigen: para XGBoost la mejora es pequeña pero consistente; para Random Forest y el Mix no.

También se reformularon varias frases de documentos anteriores que presentaban como "típico de la literatura" configuraciones que en realidad vienen del Entregable 1 o de los valores por defecto de las bibliotecas, porque el proyecto no verificó qué hace la literatura.
