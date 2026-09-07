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
    first_date: str
    deposit_type_id: str
    base_score: int
    last_date: str


def parse_jalali(date_str: str) -> jdatetime.date:
    year, month, day = map(int, date_str.split("/"))
    return jdatetime.date(year, month, day)


def format_jalali(date_value: jdatetime.date) -> str:
    return f"{date_value.year:04d}/{date_value.month:02d}/{date_value.day:02d}"


def load_deposits(source_csv: Path) -> list[DepositRecord]:
    deposits: dict[str, DepositRecord] = {}

    with source_csv.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = set(CSV_COLUMNS) - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"Missing columns in source CSV: {sorted(missing_columns)}")

        for row in reader:
            deposit_number = row["DEPOSIT_NUMBER"]
            existing = deposits.get(deposit_number)
            if existing is None or row["LAST_DATE"] > existing.last_date:
                deposits[deposit_number] = DepositRecord(
                    open_date=row["OPEN_DATE"],
                    status_name=row["STATUS_NAME"],
                    deposit_number=deposit_number,
                    main_customer_number=row["MAIN_CUSTOMER_NUMBER"],
                    main_customer_national_code=row["MAIN_CUSTOMER_NATIONAL_CODE"],
                    main_customer_name=row["MAIN_CUSTOMER_NAME"],
                    is_real=row["IS_REAL"],
                    first_date=row["FIRST_DATE"],
                    deposit_type_id=row["DEPOSIT_TYPE_ID"],
                    base_score=int(row["SCORE_MONTH_TRUNC"]),
                    last_date=row["LAST_DATE"],
                )

    if not deposits:
        raise ValueError(f"No deposit rows found in {source_csv}")

    return list(deposits.values())


def build_last_dates(start_date: jdatetime.date, end_date: jdatetime.date) -> list[str]:
    dates: list[str] = []
    current = start_date
    while current <= end_date:
        dates.append(format_jalali(current))
        current += jdatetime.timedelta(days=1)
    return dates


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
    last_dates: list[str],
    rng: random.Random,
) -> int:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        row_count = 0
        for last_date in last_dates:
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
                        "FIRST_DATE": deposit.first_date,
                        "DEPOSIT_TYPE_ID": deposit.deposit_type_id,
                        "SCORE_MONTH_TRUNC": generate_score(deposit, rng),
                    }
                )
                row_count += 1

    return row_count


def default_output_path(source_csv: Path, last_dates: list[str]) -> Path:
    first_date = last_dates[0].replace("/", "")
    last_date = last_dates[-1].replace("/", "")
    return source_csv.with_name(f"SCORE_{first_date}_{last_date}.csv")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate fake SCORE CSV rows with one LAST_DATE per deposit per day, "
            "from the day after each deposit's source LAST_DATE through today."
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

    deposits = load_deposits(source_csv)
    end_date = (
        parse_jalali(args.end_date)
        if args.end_date
        else jdatetime.date.today()
    )

    source_last_date = max(parse_jalali(deposit.last_date) for deposit in deposits)
    start_date = source_last_date + jdatetime.timedelta(days=1)
    if start_date > end_date:
        print(
            f"No dates to generate. Source LAST_DATE ({format_jalali(source_last_date)}) is "
            f"already on or after end date ({format_jalali(end_date)}).",
            file=sys.stderr,
        )
        return 1

    last_dates = build_last_dates(start_date, end_date)
    output_csv = args.output or default_output_path(source_csv, last_dates)
    rng = random.Random(args.seed)
    row_count = write_rows(output_csv, deposits, last_dates, rng)

    print(f"Loaded {len(deposits)} distinct deposits from {source_csv.name}")
    print(f"LAST_DATE range: {last_dates[0]} -> {last_dates[-1]} ({len(last_dates)} day(s))")
    print(f"Rows per deposit: {len(last_dates)}")
    print(f"Wrote {row_count} rows to {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
