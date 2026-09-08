# data-generator

Generate fake SCORE CSV data for distinct bank deposits.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

Reads deposit metadata from `SCORE_14050324_14050329.csv`, then generates one row per deposit for each daily `LAST_DATE` from the day after the source `LAST_DATE` through today (Jalali calendar). Each deposit gets exactly one row per date; `FIRST_DATE` is set equal to `LAST_DATE` because only the daily snapshot date matters.

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

## Gregorian / Shamsi calendar CSV

Generate a date mapping CSV with quoted columns `GregorianDate` and `ShamsiDate`:

```bash
python generate_date_calendar.py
```

Defaults: `2000-01-01` through `2100-12-29` → `calendar_2000-01-01_2100-12-29.csv`

Optional arguments:

- `--start YYYY-MM-DD` — first Gregorian date
- `--end YYYY-MM-DD` — last Gregorian date
- `--output PATH` — output CSV path
