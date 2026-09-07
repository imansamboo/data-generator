#!/usr/bin/env python3
"""Generate fake SCORE rows for distinct deposits from the source CSV's last date until today."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import jdatetime

CSV_COLUMNS = [
    "OPEN_DATE",
    "STATUS_NAME",
    "DEPOSIT_NUMBER",
    "MAIN_CUSTOMER_NUMBER",
    "MAIN_CUSTOMER_NATIONAL_CODE",
    "MAIN_CUSTOMER_NAME",
    "IS_REAL",
    "LAST_DATE",
    "FIRST_DATE",
    "DEPOSIT_TYPE_ID",
    "SCORE_MONTH_TRUNC",
]

ZERO_SCORE_STATUSES = {"بسته", "مسدودي بستانکار"}


@dataclass(frozen=True)
class DepositRecord:
    open_date: str
    status_name: str
    deposit_number: str
    main_customer_number: str
    main_customer_national_code: str
    main_customer_name: str
    is_real: str
    deposit_type_id: str
    base_score: int


def parse_jalali(date_str: str) -> jdatetime.date:
    year, month, day = map(int, date_str.split("/"))
    return jdatetime.date(year, month, day)


def format_jalali(date_value: jdatetime.date) -> str:
    return f"{date_value.year:04d}/{date_value.month:02d}/{date_value.day:02d}"


def load_deposits(source_csv: Path) -> tuple[list[DepositRecord], str]:
    deposits: dict[str, DepositRecord] = {}
    max_last_date = ""

    with source_csv.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = set(CSV_COLUMNS) - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"Missing columns in source CSV: {sorted(missing_columns)}")

        for row in reader:
            deposit_number = row["DEPOSIT_NUMBER"]
            if deposit_number not in deposits:
                deposits[deposit_number] = DepositRecord(
                    open_date=row["OPEN_DATE"],
                    status_name=row["STATUS_NAME"],
                    deposit_number=deposit_number,
                    main_customer_number=row["MAIN_CUSTOMER_NUMBER"],
                    main_customer_national_code=row["MAIN_CUSTOMER_NATIONAL_CODE"],
                    main_customer_name=row["MAIN_CUSTOMER_NAME"],
                    is_real=row["IS_REAL"],
                    deposit_type_id=row["DEPOSIT_TYPE_ID"],
                    base_score=int(row["SCORE_MONTH_TRUNC"]),
                )

            if row["LAST_DATE"] > max_last_date:
                max_last_date = row["LAST_DATE"]

    if not deposits:
        raise ValueError(f"No deposit rows found in {source_csv}")

    if not max_last_date:
        raise ValueError("Could not determine LAST_DATE from source CSV")

    return list(deposits.values()), max_last_date


def infer_period_length_days(first_date: str, last_date: str) -> int:
    first = parse_jalali(first_date)
    last = parse_jalali(last_date)
    return (last - first).days + 1


def build_periods(
    source_first_date: str,
    source_last_date: str,
    end_date: jdatetime.date,
) -> list[tuple[str, str]]:
    period_length = infer_period_length_days(source_first_date, source_last_date)
    current_first = parse_jalali(source_last_date) + jdatetime.timedelta(days=1)
    periods: list[tuple[str, str]] = []

    while current_first <= end_date:
        current_last = current_first + jdatetime.timedelta(days=period_length - 1)
        if current_last > end_date:
            current_last = end_date
        periods.append((format_jalali(current_first), format_jalali(current_last)))
        current_first = current_last + jdatetime.timedelta(days=1)

    return periods


def random_open_score(base_score: int, rng: random.Random) -> int:
    if base_score == 0:
        if rng.random() < 0.35:
            return 0
        return int(rng.lognormvariate(10.5, 1.4))

    multiplier = rng.uniform(0.75, 1.35)
    score = int(base_score * multiplier)
    if score < 0:
        return 0
    return score


def generate_score(deposit: DepositRecord, rng: random.Random) -> int:
    if deposit.status_name in ZERO_SCORE_STATUSES:
        return 0
    return random_open_score(deposit.base_score, rng)


def write_rows(
    output_csv: Path,
    deposits: list[DepositRecord],
    periods: list[tuple[str, str]],
    rng: random.Random,
) -> int:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        row_count = 0
        for first_date, last_date in periods:
            for deposit in deposits:
                writer.writerow(
                    {
                        "OPEN_DATE": deposit.open_date,
                        "STATUS_NAME": deposit.status_name,
                        "DEPOSIT_NUMBER": deposit.deposit_number,
                        "MAIN_CUSTOMER_NUMBER": deposit.main_customer_number,
                        "MAIN_CUSTOMER_NATIONAL_CODE": deposit.main_customer_national_code,
                        "MAIN_CUSTOMER_NAME": deposit.main_customer_name,
                        "IS_REAL": deposit.is_real,
                        "LAST_DATE": last_date,
                        "FIRST_DATE": first_date,
                        "DEPOSIT_TYPE_ID": deposit.deposit_type_id,
                        "SCORE_MONTH_TRUNC": generate_score(deposit, rng),
                    }
                )
                row_count += 1

    return row_count


def default_output_path(source_csv: Path, periods: list[tuple[str, str]]) -> Path:
    first_period_start = periods[0][0].replace("/", "")
    last_period_end = periods[-1][1].replace("/", "")
    return source_csv.with_name(f"SCORE_{first_period_start}_{last_period_end}.csv")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate fake SCORE CSV rows for each distinct deposit from the day after "
            "the source file's LAST_DATE through today (Jalali calendar)."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("SCORE_14050324_14050329.csv"),
        help="Source SCORE CSV file (default: SCORE_14050324_14050329.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: SCORE_<first>_<last>.csv next to input)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Inclusive end date in YYYY/MM/DD Jalali format (default: today)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible fake scores (default: 42)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_csv = args.input

    if not source_csv.exists():
        print(f"Input file not found: {source_csv}", file=sys.stderr)
        return 1

    deposits, max_last_date = load_deposits(source_csv)

    with source_csv.open(encoding="utf-8-sig", newline="") as handle:
        sample_row = next(csv.DictReader(handle))

    end_date = (
        parse_jalali(args.end_date)
        if args.end_date
        else jdatetime.date.today()
    )
    periods = build_periods(sample_row["FIRST_DATE"], max_last_date, end_date)

    if not periods:
        print(
            f"No periods to generate. Source LAST_DATE ({max_last_date}) is already "
            f"on or after end date ({format_jalali(end_date)}).",
            file=sys.stderr,
        )
        return 1

    output_csv = args.output or default_output_path(source_csv, periods)
    rng = random.Random(args.seed)
    row_count = write_rows(output_csv, deposits, periods, rng)

    print(f"Loaded {len(deposits)} distinct deposits from {source_csv.name}")
    print(f"Source LAST_DATE: {max_last_date}")
    print(f"Generated {len(periods)} period(s) through {format_jalali(end_date)}")
    print(f"Wrote {row_count} rows to {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
