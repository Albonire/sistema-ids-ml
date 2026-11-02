# Guion de demo en clase (Entregable 2)

Duración prevista: 10 minutos más preguntas. Ajustar el orden y el tiempo a lo que pida la docente. Todas las cifras salen de `reports/<dataset>/resultados.md` y `docs/fase2_modelos.md`.

## 0. Antes de la clase (no hacer en vivo)

Con Python 3.10 o superior, desde la raíz del repositorio:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m src.download_data --dataset all     # unos 890 MB, varios minutos según la red
python -m src.preprocess --dataset all        # entre 3 y 4 minutos
python -m src.train --dataset unsw_nb15       # unos 7 minutos con 4 CPU
python -m src.train --dataset cicids2017      # entre 15 y 25 minutos con 4 CPU
python -m src.evaluate --dataset unsw_nb15
python -m src.evaluate --dataset cicids2017
python -m pytest -q                                     # 40 pruebas
```

Se usa `python -m pytest` y no `pytest` a secas: el shell puede tener en caché un `pytest` de fuera del entorno virtual (por ejemplo en `~/.local/bin`), que no ve `xgboost` y falla al importar. Si se prefiere el comando corto, ejecutar `hash -r` tras activar el entorno.

Los datos y los modelos no están en Git, así que hay que generarlos en cada computador. Las figuras y tablas que se muestran ya vienen en `reports/` (sí están en Git).

Verificación rápida antes de entrar al salón:

```bash
python -m src.predict --dataset unsw_nb15 --input docs/demo/flujos_ejemplo.csv
```

Si se prefiere reentrenar en vivo, existe una versión rápida de unos 45 segundos (no reproduce las cifras del informe, porque busca hiperparámetros con 1 candidato):

```bash
python -m src.train --dataset unsw_nb15 --n-iter 1 --tune-sample 20000 --cv-folds 3
```

Ojo: ese comando **sobrescribe** `models/unsw_nb15/` y `reports/unsw_nb15/`. Después de usarlo hay que volver a las cifras reales con `git checkout -- reports` y reentrenando completo.

## 1. Problema y pregunta (1 minuto)

- Los IDS por firmas no detectan amenazas nuevas y generan falsas alarmas que saturan a los analistas.
- Pregunta: ¿qué algoritmo da el mejor equilibrio entre detección y falsas alarmas?
- Criterio del proyecto: Recall >= 0.95 y FPR <= 0.02.

## 2. Qué se comparó (1 minuto)

- Datasets: UNSW-NB15 (principal, el del Entregable 1) y CICIDS2017 (contraste).
- Modelos: Random Forest, XGBoost y su mezcla por votación suave, cada uno en versión **base** (configuración típica de la literatura) y **mejorada** (filtro de correlación, hiperparámetros por validación cruzada de 5 folds, umbral elegido en validación).
- Partición 70/15/15 estratificada. La prueba no se usa para decidir nada.
- Alcance acotado a pocos modelos por indicación de la docente.

## 3. Los datos primero (1,5 minutos)

```bash
python -m json.tool data/processed/unsw_nb15_cleaning_report.json | head -12
```

Mensaje: de 257.673 flujos, 103.575 son duplicados y 828 son contradictorios (el mismo vector con etiqueta normal y de ataque). Quedan 153.270. Es decir, **más del 40 % del dataset crudo es redundante**.

## 4. Demostración en vivo: clasificar flujos (2,5 minutos)

El archivo `docs/demo/flujos_ejemplo.csv` tiene 10 flujos del conjunto de **prueba** de UNSW-NB15: 4 normales y 4 ataques tomados al azar, más dos casos elegidos a propósito para mostrar errores (la columna `nota` lo indica; el modelo la ignora).

```bash
python -m src.predict --dataset unsw_nb15 --input docs/demo/flujos_ejemplo.csv --operating-point default
python -m src.predict --dataset unsw_nb15 --input docs/demo/flujos_ejemplo.csv --operating-point recall_target
python -m src.predict --dataset unsw_nb15 --input docs/demo/flujos_ejemplo.csv --operating-point fpr_budget
```

Qué se ve con el modelo ganador (XGBoost mejorado, umbrales 0.5, 0.3383 y 0.7252):

| Fila | Tipo real | Umbral 0.5 | Recall 0.95 | FPR 0.02 | Probabilidad de ataque |
|---|---|---|---|---|---|
| 0 a 3 | Normal | normal | normal | normal | casi 0 |
| 4 | Exploits | ataque | ataque | ataque | 0.9986 |
| 5 | Generic | ataque | ataque | ataque | 0.9999 |
| 6 | Reconnaissance | ataque | ataque | ataque | 0.9583 |
| 7 | Fuzzers | ataque | ataque | ataque | 0.8954 |
| 8 | Normal (elegido) | normal | **ataque** | normal | 0.4406 |
| 9 | Analysis (elegido) | **normal** | **normal** | **normal** | 0.1269 |

Mensajes:

- La fila 8 es una **falsa alarma** que aparece solo cuando se baja el umbral para exigir Recall 0.95.
- La fila 9 es un **ataque que se escapa** en los tres puntos: la familia Analysis es la más difícil.
- Un solo flujo, en JSON:

```bash
python -m src.predict --dataset unsw_nb15 --json "$(cat docs/demo/flujo_ejemplo.json)"
```

## 5. Resultados (2 minutos)

Abrir `reports/unsw_nb15/resultados.md` y las figuras `figures/roc.png`, `figures/fpr_recall_comparison.png` y `figures/detection_by_attack_type.png`.

Modelo ganador en UNSW-NB15 (prueba: 10.195 ataques y 12.796 flujos normales):

| Punto de operación | Recall | FPR | Ataques perdidos | Falsas alarmas |
|---|---|---|---|---|
| Umbral 0.5 | 0.8998 | 0.0612 | 1.022 | 783 |
| Mínimo FPR con Recall >= 0.95 | 0.9515 | 0.1222 | 494 | 1.564 |
| Máximo Recall con FPR <= 0.02 | 0.8238 | 0.0205 | 1.796 | 262 |

- **Ningún modelo cumple Recall >= 0.95 y FPR <= 0.02 en UNSW-NB15.** Pasar de FPR 2 % a Recall 95 % multiplica las falsas alarmas por seis.
- Las familias difíciles son Fuzzers (detección 0.70 con umbral 0.5) y Analysis (0.55).
- CICIDS2017 está saturado: con umbral 0.5, XGBoost tiene Recall 0.9985 y FPR 0.0003, y los seis modelos cumplen el criterio. Por eso no discrimina entre modelos.
- Respuesta a la pregunta de investigación: XGBoost (base o mejorado) da el mejor equilibrio en ambos datasets; la mezcla con RF no aporta una ventaja demostrable.

## 6. Qué aporta el trabajo: evaluar sin fuga de datos (1 minuto)

```bash
python -m json.tool reports/unsw_nb15/leakage_ablation.json | head -30
```

Con un protocolo ingenuo (sin quitar duplicados), el 44,5 % de la prueba de UNSW-NB15 son vectores que el modelo ya vio en entrenamiento. La accuracy sube de 0.919 a 0.945 y el Recall de 0.894 a 0.950: **el protocolo ingenuo sobrestima la detección en 5,6 puntos**. En CICIDS2017 el efecto es despreciable porque el dataset ya está saturado.

## 7. Cierre y trabajo siguiente (1 minuto)

Dicho con honestidad:

- La versión "mejorada" no supera a la base de forma demostrable en UNSW-NB15 (los intervalos de confianza se solapan). Lo defendible es el protocolo sin fuga y el análisis por punto de operación.
- Limitaciones: una sola semilla y partición; búsqueda de hiperparámetros acotada.
- Siguiente: repetir con varias semillas, ablación de variables sospechosas de atajos (`sttl`, `state_INT`, `Destination Port`) e informe final.

## Preguntas probables

**¿Por qué no SVM ni redes neuronales?** El Entregable 1 los dejaba como complementarios y la docente pidió pocos modelos mejorados. `AGENT.md` ya anticipaba su alto costo computacional en datasets masivos, y no se probó en este proyecto.

**¿Por qué el FPR es de 12 % para tener Recall 0.95?** Porque las clases se solapan: Fuzzers y Analysis se parecen al tráfico normal. La curva ROC (`roc.png`) lo muestra: ningún algoritmo comparado la mejora de forma apreciable.

**¿Por qué la versión mejorada no es mejor?** En UNSW-NB15 las diferencias están dentro del ruido de muestreo. En CICIDS2017 el dataset está saturado. En RF incluso empeora con umbral 0.5 en CICIDS2017, porque la búsqueda sobre una muestra de 60.000 flujos eligió profundidad 12.

**¿Qué significa que el criterio sea "degenerado"?** "Mínimo FPR con Recall >= 0.95" empuja el Recall hasta 0.95 aunque el modelo pueda dar 0.998. En CICIDS2017 baja las falsas alarmas de 102 a 13, pero los ataques no detectados pasan de 97 a 3.158. Por eso se reportan tres puntos de operación.

**¿Los resultados valen para tráfico real?** No necesariamente. Los datasets son de laboratorio, CICIDS2017 tiene errores de etiquetado documentados (Engelen et al., 2021) y la evaluación es sobre archivos de flujos, no captura en vivo.

**¿Por qué no se usó SMOTE?** El desbalance de UNSW-NB15 es moderado (56 % normal) y el umbral elegido en validación ya controla el compromiso entre falsas alarmas y detección. Si se aplicara, sería solo sobre el entrenamiento.

**¿Se puede reproducir?** Sí: descarga con SHA256, `random_state=42` y 40 pruebas. Los comandos están en la sección 0.
