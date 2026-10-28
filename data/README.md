# Datos

Los archivos de datos no se versionan en Git (ver `.gitignore`). Se generan localmente.

## Obtención y limpieza

```bash
python -m src.download_data    # descarga y verifica los 8 CSV en data/raw/ (unos 844 MB)
python -m src.preprocess       # genera data/processed/cicids2017_clean.parquet y cleaning_report.json
```

La descarga es idempotente: los archivos ya presentes y con SHA256 correcto se omiten. Use `--force` para repetirla.

## Fuente

El enlace oficial del Canadian Institute for Cybersecurity (UNB) ahora exige un formulario de registro, por lo que no se puede automatizar. El script descarga los mismos ocho archivos `MachineLearningCSV` desde el espejo de Hugging Face `c01dsnap/CIC-IDS2017`, fijado a una revisión concreta y con verificación SHA256 (las sumas están en `src/config.py`).

Alternativa manual: descargar `MachineLearningCSV.zip` desde https://www.unb.ca/cic/datasets/ids-2017.html y extraer los CSV en `data/raw/`.

## Cita obligatoria

Iman Sharafaldin, Arash Habibi Lashkari y Ali A. Ghorbani, "Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization", 4th International Conference on Information Systems Security and Privacy (ICISSP), Portugal, enero de 2018.

## Esquema del dataset procesado

- 69 variables numéricas (`float32`), nombres originales sin espacios laterales.
- `label` (`int8`): 0 tráfico normal, 1 intrusión.
- `attack_type` (`str`): `BENIGN` o la familia de ataque (15 valores).
