# Datos

Los archivos de datos no se versionan en Git (ver `.gitignore`). Se generan localmente.

## Obtención y limpieza

```bash
python -m src.download_data --dataset all   # descarga y verifica los CSV en data/raw/<dataset>/
python -m src.preprocess --dataset all      # genera data/processed/<dataset>_clean.parquet y su reporte JSON
```

La descarga es idempotente: los archivos ya presentes y con SHA256 correcto se omiten. Use `--force` para repetirla y `--dataset unsw_nb15` o `--dataset cicids2017` para uno solo.

## Fuentes

| Dataset | Origen del script | Tamaño |
|---|---|---|
| UNSW-NB15 | Espejo de Hugging Face `Mireu-Lab/UNSW-NB15` (revisión fijada, SHA256 en `src/config.py`) | 2 CSV, unos 48 MB |
| CICIDS2017 | Espejo de Hugging Face `c01dsnap/CIC-IDS2017` (revisión fijada, SHA256 en `src/config.py`) | 8 CSV, unos 844 MB |

Nota sobre UNSW-NB15: en ese espejo los nombres están intercambiados (`test.csv` contiene la partición oficial de entrenamiento con 175,341 filas y `train.csv` la de prueba con 82,332). El proyecto las une y las reparte de nuevo en 70/15/15, por lo que el intercambio no afecta.

Nota sobre CICIDS2017: el enlace oficial del Canadian Institute for Cybersecurity (UNB) ahora exige un formulario de registro y no se puede automatizar.

Alternativa manual: descargar los archivos desde las páginas oficiales de [CICIDS2017](https://www.unb.ca/cic/datasets/ids-2017.html) o [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset) y colocarlos en `data/raw/<dataset>/` con los mismos nombres de archivo. El script verifica el SHA256, por lo que una copia distinta se rechaza.

## Citas obligatorias

- Sharafaldin, I., Habibi Lashkari, A. y Ghorbani, A. A. (2018). "Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization". 4th International Conference on Information Systems Security and Privacy (ICISSP), Portugal.
- Moustafa, N. y Slay, J. (2015). "UNSW-NB15: a comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set)". 2015 Military Communications and Information Systems Conference (MilCIS). DOI 10.1109/MilCIS.2015.7348942.

## Esquema de los datasets procesados

- Variables numéricas en `float32` y, en UNSW-NB15, tres categóricas (`proto`, `service`, `state`) como texto.
- `label` (`int8`): 0 tráfico normal, 1 intrusión.
- `attack_type` (`str`): `BENIGN` o la familia de ataque.
- UNSW-NB15: 42 variables, 10 valores de `attack_type`. CICIDS2017: 69 variables, 15 valores.
