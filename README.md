# data-generator

Generate fake SCORE CSV data for distinct bank deposits.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

Reads deposit metadata from `SCORE_14050324_14050329.csv`, then generates one row per deposit for each monthly period from the day after the source `LAST_DATE` through today (Jalali calendar).

```bash
python generate_score_data.py
```

Optional arguments:

- `--input PATH` — source CSV (default: `SCORE_14050324_14050329.csv`)
- `--output PATH` — output CSV path (default: `SCORE_<first>_<last>.csv`)
- `--end-date YYYY/MM/DD` — inclusive Jalali end date (default: today)
- `--seed N` — random seed for reproducible scores (default: 42)

Example:

```bash
python generate_score_data.py --seed 123 --output generated_scores.csv
```
