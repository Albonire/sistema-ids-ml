# Sistema Inteligente de Detección de Intrusiones de Red (IDS)

Prototipo de software basado en aprendizaje automático para la identificación y clasificación de tráfico de red legítimo y malicioso, enfocado en el equilibrio óptimo entre cobertura de detección y reducción de la tasa de falsos positivos.

Proyecto desarrollado para la asignatura **Seguridad Informática**.

---

## Integrantes del Equipo

- **Fabian** (Coordinación, Arquitectura de Software y Pipeline)
- **Silvana** (GitHub: [inana20](https://github.com/inana20)) (Investigación, Preprocesamiento y Modelos)
- **Raul** (GitHub: [Raul-2112](https://github.com/Raul-2112)) (Métricas, Evaluación de Resultados y Documentación)

---

## Pregunta de Investigación

> *¿Qué algoritmo de aprendizaje automático proporciona el mejor equilibrio entre capacidad de detección y tasa de falsos positivos para un IDS basado en un dataset de tráfico de red?*

---

## Modelos Evaluados

1. **Random Forest**: Ensamble basado en árboles para datos tabulares.
2. **XGBoost**: Gradient boosting, referencia en datos tabulares.
3. **Mix (RF + XGBoost)**: Votación suave de ambos.

Cada uno en versión **base** (configuración típica de la literatura) y **mejorada** (filtro de correlación, hiperparámetros por validación cruzada de 5 folds y umbral calibrado en validación).

---

## Datasets

- **UNSW-NB15**: Dataset principal (Entregable 1). 9 familias de ataque más tráfico normal.
- **CICIDS2017**: Dataset de contraste. Flujos con 69 variables útiles y 14 familias de ataque.

*Nota: Los archivos de datos crudos no se almacenan en este repositorio. Ver [data/README.md](data/README.md).*

---

## Estructura del Repositorio

```
proyecto/
|-- data/                  # Datos locales (ignorados en Git, salvo data/README.md)
|   |-- raw/<dataset>/     # CSV descargados
|   `-- processed/         # Parquet limpios y reportes de limpieza
|-- docs/                  # Documentacion tecnica y antecedentes
|-- models/<dataset>/      # Mejor modelo y puntajes (ignorado en Git)
|-- notebooks/             # EDA (Jupyter)
|-- reports/<dataset>/     # Metricas, figuras y resultados.md
|-- src/                   # Codigo fuente modular del prototipo
|   |-- config.py          # Rutas, constantes y fuentes de datos
|   |-- download_data.py   # Descarga verificada (SHA256)
|   |-- preprocess.py      # Limpieza
|   |-- data_loader.py     # Carga y particion 70/15/15 estratificada
|   |-- features.py        # Filtro de correlacion y codificacion
|   |-- models.py          # Modelos base, mejorados y mix
|   |-- metrics.py         # Metricas, umbral calibrado e intervalos bootstrap
|   |-- train.py           # Entrenamiento multimodelo
|   |-- predict.py         # Inferencia por lotes o flujo individual
|   `-- evaluate.py        # Figuras, ROC y resultados.md
|-- tests/                 # Pruebas unitarias (pytest)
|-- AGENT.md               # Directivas maestras para agentes y desarrollo
`-- requirements.txt       # Dependencias de Python
```

---

## Uso

```bash
pip install -r requirements-dev.txt
python -m src.download_data --dataset all            # descarga y verifica los CSV
python -m src.preprocess --dataset all               # limpieza a data/processed/
python -m src.train --dataset unsw_nb15              # entrena y elige el mejor modelo
python -m src.evaluate --dataset unsw_nb15           # figuras y reports/unsw_nb15/resultados.md
python -m src.predict --dataset unsw_nb15 --input flujos.csv
pytest -q                                            # pruebas unitarias
```

Reemplazar `unsw_nb15` por `cicids2017` para el segundo dataset. Detalles en [docs/fase1_pipeline_datos.md](docs/fase1_pipeline_datos.md), [docs/fase2_modelos.md](docs/fase2_modelos.md) y [data/README.md](data/README.md).

---

## Instalación y Requisitos

Requisitos previos:
- Python 3.10 o superior
- Administrador de paquetes `pip` o entorno virtual `venv`

Configuración del entorno:

```bash
# Crear entorno virtual
python3 -m venv .venv

# Activar entorno virtual
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## Directivas para Contribuidores

Consultar el archivo [AGENT.md](AGENT.md) para detalles sobre el protocolo de trabajo, convenciones de código y criterios de evaluación académica.
