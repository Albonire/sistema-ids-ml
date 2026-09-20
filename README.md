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

1. **Random Forest**: Ensamble basado en árboles para datos tabulares de alta dimensionalidad.
2. **Support Vector Machines (SVM)**: Clasificación de margen máximo con funciones de kernel.
3. **Árboles de Decisión (CART)**: Modelo base interpretable para extracción de reglas.
4. **Multi-Layer Perceptron (MLP)**: Red neuronal artificial para relaciones no lineales complejas.

---

## Datasets

- **CICIDS2017**: Tráfico de red con flujos bidireccionales y vectores de ataque modernos (DoS/DDoS, PortScan, Brute Force, Web Attacks, Botnets).
- **UNSW-NB15**: Dataset complementario de validación.

*Nota: Los archivos de datos crudos no se almacenan en este repositorio por restricciones de tamaño y buenas prácticas. Consultar la documentación en `data/` para instrucciones de descarga y procesamiento.*

---

## Estructura del Repositorio

```
proyecto/
|-- data/                  # Almacenamiento local de datasets (ignorado en Git)
|   |-- raw/               # Datos crudos (.csv, .pcap)
|   `-- processed/         # Datos limpios y normalizados
|-- docs/                  # Documentacion academica y diagramas
|-- models/                # Modelos exportados (.joblib, ignorado en Git)
|-- notebooks/             # Cuadernos Jupyter para EDA y pruebas preliminares
|-- src/                   # Codigo fuente modular del prototipo
|   |-- train.py           # Pipeline de entrenamiento multimodelo
|   |-- predict.py         # Motor de inferencia para flujos nuevos
|   `-- evaluate.py        # Generacion de graficos, ROC y matrices
|-- .gitignore             # Filtros de exclusion para Git
|-- AGENT.md               # Directivas maestras para agentes y desarrollo
|-- README.md              # Descripcion general del repositorio
`-- requirements.txt       # Dependencias de Python
```

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
