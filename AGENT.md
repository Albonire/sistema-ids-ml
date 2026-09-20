# AGENT.md: Directiva Maestra del Proyecto IDS con Machine Learning

## 1. Identidad y Contexto del Proyecto

- **Proyecto**: Sistema Inteligente de Detección de Intrusiones de Red (IDS) basado en Machine Learning.
- **Asignatura**: Seguridad Informática (Programa académico de 16 semanas).
- **Equipo de trabajo**:
  - Fabian (Coordinación, Arquitectura de Software y Pipeline)
  - Silvana - GitHub: `inana20` (Investigación, Preprocesamiento y Modelos)
  - Raul - GitHub: `Raul-2112` (Métricas, Evaluación de Resultados y Documentación)
- **Fase actual**: Fase de Análisis y Planificación (Preparación del Entregable 1, Semana 6).

---

## 2. Definición del Problema y Pregunta de Investigación

### 2.1 El Problema en los IDS Tradicionales
Los sistemas tradicionales de detección de intrusiones de red (como Snort o Suricata en sus configuraciones estándar) se fundamentan en la coincidencia de firmas predefinidas y reglas estáticas. Este paradigma enfrenta dos limitaciones críticas en entornos modernos:

1. **Incapacidad ante amenazas desconocidas (Zero-Day)**: Cualquier variante de malware, técnica de evasión o nuevo vector de ataque que no cuente con una regla idéntica previa pasa desapercibido.
2. **Fatiga por falsas alarmas (Falsos Positivos)**: La rigidez de las reglas suele clasificar tráfico legítimo pero atípico como malicioso, saturando a los analistas del Centro de Operaciones de Seguridad (SOC) y degradando la operatividad.

### 2.2 Justificación del Aprendizaje Automático
El aprendizaje automático permite modelar las relaciones estadísticas multivariadas de los flujos de red (tasas de transferencia, duración, frecuencias de paquetes, entropía de puertos y distribución de banderas TCP). En lugar de buscar una cadena de bytes exacta, el modelo aprende la distribución de normalidad y los patrones distintivos de agresión, ofreciendo capacidad de generalización y detección adaptativa.

### 2.3 Pregunta de Investigación Central
> *¿Qué algoritmo de aprendizaje automático proporciona el mejor equilibrio entre capacidad de detección y tasa de falsos positivos para un IDS basado en un dataset de tráfico de red?*

---

## 3. Objetivos del Proyecto

### 3.1 Objetivo General
Desarrollar un prototipo basado en aprendizaje automático capaz de identificar y clasificar tráfico de red normal y malicioso.

### 3.2 Objetivos Específicos
1. Descargar, limpiar y normalizar un dataset público de tráfico de red representativo (CICIDS2017 como fuente principal, UNSW-NB15 como alternativa de contraste), seleccionando las características más discriminatorias.
2. Entrenar y comparar cuatro algoritmos de clasificación de diversa naturaleza: Random Forest, Support Vector Machines (SVM), Árboles de Decisión (CART) y Multi-Layer Perceptron (MLP).
3. Evaluar cuantitativamente el rendimiento de cada modelo mediante métricas formales (Accuracy, Precision, Recall, F1-score y False Positive Rate), analizando de forma rigurosa la frontera entre detección efectiva y falsas alarmas.
4. Construir un prototipo funcional en Python (`train.py`, `predict.py`, `evaluate.py`) estructurado para operar tanto por lotes como en inferencia sobre flujos individuales.

---

## 4. Datasets y Estrategia de Datos

### 4.1 Datasets de Referencia
- **CICIDS2017 (Canadian Institute for Cybersecurity)**:
  - Generado mediante la herramienta CICFlowMeter a partir de capturas de red reales (archivos PCAP).
  - Incluye más de 80 características estadísticas de flujos de red bidireccionales.
  - Cubre tráfico benigno y múltiples familias de agresión: DoS/DDoS, PortScan, Brute Force (SSH/FTP), Web Attacks (XSS, SQL Injection), Botnet e Infiltration.
- **UNSW-NB15 (Universidad de Nueva Gales del Sur)**:
  - Dataset complementario con ataques modernos sintéticos y tráfico de fondo contemporáneo.
  - Utilizado como referencia secundaria para verificar estabilidad y evitar sesgos de captura.

### 4.2 Protocolo de Manejo de Datos
- **Aislamiento en Git**: Los archivos de datos crudos (`.pcap`, `.csv`, `.parquet`) están excluidos del control de versiones mediante `.gitignore` para preservar la ligereza del repositorio.
- **Reproducibilidad**: Se mantendrán scripts de descarga y limpieza deterministas en la carpeta `data/` con semillas fijas (`random_state=42`).
- **Limpieza rigurosa**: Tratamiento de valores infinitos, eliminación de valores faltantes (NaN), normalización numérica (StandardScaler o MinMaxScaler) y codificación de etiquetas (0 para normal, 1 para intrusión).

---

## 5. Modelos de Machine Learning a Evaluar

| Algoritmo | Categoría | Justificación Técnica | Desafío Previsto |
|---|---|---|---|
| **Random Forest** | Ensamble (Bagging) | Alta estabilidad en datos tabulares, resistente al sobreajuste y proporciona ranking de importancia de características. | Tamaño del modelo serializado en memoria. |
| **Support Vector Machines (SVM)** | Margen Máximo | Efectivo en fronteras de decisión complejas mediante funciones de kernel (RBF / Lineal). | Alto costo computacional durante el entrenamiento en datasets masivos. |
| **Árboles de Decisión (CART)** | Basado en Reglas | Máxima interpretabilidad: permite auditar exactamente qué umbrales determinan una alerta. | Tendencia a sobreajustar sin poda adecuada. |
| **Multi-Layer Perceptron (MLP)** | Red Neuronal Artificial | Capaz de modelar interacciones no lineales complejas entre flujos de tráfico. | Requiere ajuste cuidadoso de hiperparámetros y normalización estricta. |

---

## 6. Métricas y Criterios de Decisión

Para responder a la pregunta de investigación, se adoptan las siguientes definiciones:

- **True Positives (TP)**: Ataques reales correctamente clasificados como intrusión.
- **True Negatives (TN)**: Tráfico benigno correctamente clasificado como normal.
- **False Positives (FP)**: Tráfico benigno clasificado erróneamente como intrusión (falsa alarma).
- **False Negatives (FN)**: Ataques no detectados clasificados como tráfico normal (omisión crítica).

### Fórmulas de Evaluación
1. **Accuracy**: $(TP + TN) / (TP + TN + FP + FN)$ (referencial, sujeta a desbalance).
2. **Precision**: $TP / (TP + FP)$ (relevancia: cuán confiable es una alerta).
3. **Recall (Sensibilidad)**: $TP / (TP + FN)$ (cobertura: qué porcentaje de ataques se detectó).
4. **F1-Score**: $2 \times (\text{Precision} \times \text{Recall}) / (\text{Precision} + \text{Recall})$ (balance armónico).
5. **False Positive Rate (FPR)**: $FP / (FP + TN)$ (tasa de falsas alarmas, indicador central del proyecto).

> **Criterio de Decisión**: El algoritmo óptimo no será necesariamente el de mayor Accuracy global, sino aquel que minimice el FPR mientras mantiene un Recall superior a un umbral predefinido (ej. Recall >= 0.95 y FPR <= 0.02).

---

## 7. Arquitectura Conceptual del Prototipo

```
proyecto/
|-- data/                  # Directorio local de datos (ignorado por Git)
|   |-- raw/               # Archivos CSV descargados sin modificar
|   `-- processed/         # Datasets limpios y preprocesados
|-- docs/                  # Documentacion academica, diagramas y referencias
|-- models/                # Modelos exportados (.joblib, ignorado por Git)
|-- notebooks/             # Cuadernos Jupyter para analisis exploratorio (EDA)
|-- src/                   # Codigo fuente modular del prototipo
|   |-- __init__.py
|   |-- data_loader.py     # Carga y particionado determinista
|   |-- train.py           # Pipeline de entrenamiento multimodelo
|   |-- predict.py         # Motor de inferencia en tiempo real o batch
|   |-- evaluate.py        # Generacion de metricas, matrices y graficos
|   `-- utils/             # Funciones auxiliares y transformaciones
|-- .gitignore             # Exclusion estricta de datos, venv y modelos pesados
|-- AGENT.md               # Este archivo maestro de directivas
|-- README.md              # Presentacion publica del repositorio
`-- requirements.txt       # Dependencias verificadas de Python
```

### Funciones de los Módulos Principales
- **`src/train.py`**:
  - Carga el dataset procesado y realiza la partición train/test (70/30).
  - Entrena concurrentemente o secuencialmente los 4 algoritmos configurados.
  - Calcula las métricas sobre el conjunto de prueba y genera la tabla comparativa.
  - Guarda el modelo con el mejor balance en `models/best_model.joblib`.
- **`src/predict.py`**:
  - Carga `models/best_model.joblib`.
  - Recibe un archivo de flujos o un vector individual de características.
  - Emite la clasificación: `"Trafico Normal"` o `"Ataque Detectado"`, junto con la probabilidad calculada.
- **`src/evaluate.py`**:
  - Produce las matrices de confusión normalizadas.
  - Genera las curvas ROC (Receiver Operating Characteristic) y Precision-Recall.
  - Grafica la comparativa de FPR entre algoritmos para el informe final.

---

## 8. Cronograma de 16 Semanas y Entregables

```
Semana 01 - 02: Planteamiento del problema y revision bibliografica (Entregable 1)
Semana 03 - 04: Estado del arte y seleccion de datasets (Entregable 1)
Semana 05 - 06: Diseno de arquitectura, repositorio y metodologia (Entregable 1 - Cierre)
Semana 07 - 09: Desarrollo del prototipo base y limpieza de datos (Entregable 2)
Semana 10 - 12: Entrenamiento de modelos y pruebas iniciales (Entregable 2 - Demo en clase)
Semana 13 - 14: Experimentacion formal y evaluacion de metricas (Entregable 3)
Semana 15 - 16: Informe final, conclusiones y sustentacion (Entregable 3 - Cierre)
```

### Distribución de Criterios de Calificación
- Problema de ciberseguridad y justificación: 10%
- Revisión de literatura científica: 15%
- Diseño y metodología: 10%
- Implementación de IA: 35%
- Experimentación y métricas: 10%
- Análisis crítico de resultados: 10%
- Documentación, presentación y trabajo en equipo: 10%

---

## 9. Directrices de Trabajo para Agentes y Desarrolladores

Cualquier agente de IA o desarrollador humano que contribuya a este repositorio debe acatar las siguientes reglas sin excepción:

1. **Prohibición de Emojis**: Queda estrictamente prohibido el uso de emojis o emoticonos en cualquier archivo de código, documentación, comentarios, logs o mensajes de commit.
2. **Prohibición de Em Dashes**: Nunca utilizar guiones largos (em dash U+2014) ni guiones medios (en dash U+2013). Emplear guiones estándar (`-`), dos puntos (`:`), comas (`,`) o paréntesis.
3. **Idioma**:
   - Código fuente, nombres de variables, funciones, clases, comentarios en línea y mensajes de commit deben redactarse en **inglés**.
   - La documentación formal de entrega y reportes académicos para la universidad se redacta en **español** técnico o inglés según la plantilla oficial.
4. **Seguridad de Datos**:
   - Nunca incluir credenciales, tokens ni rutas absolutas locales en el código.
   - No añadir archivos de datos masivos (`.pcap`, `.csv`) al historial de Git.
5. **Calidad de Código**:
   - Todo cambio debe ser reproducible, modular y contener tipado estático cuando sea aplicable.
   - Soluciones completas: no dejar funciones vacías con `pass` ni `TODO: implement`.
