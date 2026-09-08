#!/usr/bin/env python3
"""Generate a Gregorian to Shamsi (Jalali) date mapping CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

import jdatetime

DEFAULT_START = date(2000, 1, 1)
DEFAULT_END = date(2100, 12, 29)
CSV_COLUMNS = ["GregorianDate", "ShamsiDate"]


def parse_gregorian(date_str: str) -> date:
    year, month, day = map(int, date_str.split("-"))
    return date(year, month, day)


def format_gregorian(date_value: date) -> str:
    return date_value.isoformat()


def format_shamsi(date_value: date) -> str:
    shamsi = jdatetime.date.fromgregorian(date=date_value)
    return f"{shamsi.year:04d}/{shamsi.month:02d}/{shamsi.day:02d}"


def generate_rows(start_date: date, end_date: date) -> list[dict[str, str]]:
    if start_date > end_date:
        raise ValueError("start date must be on or before end date")

    rows: list[dict[str, str]] = []
    current = start_date
    while current <= end_date:
        rows.append(
            {
                "GregorianDate": format_gregorian(current),
                "ShamsiDate": format_shamsi(current),
            }
        )
        current += timedelta(days=1)

    return rows


def write_csv(output_csv: Path, rows: list[dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_COLUMNS,
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(rows)


def default_output_path(start_date: date, end_date: date) -> Path:
    return Path(f"calendar_{start_date.isoformat()}_{end_date.isoformat()}.csv")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a CSV mapping Gregorian dates to Shamsi dates."
    )
    parser.add_argument(
        "--start",
        default=DEFAULT_START.isoformat(),
        help="Start Gregorian date YYYY-MM-DD (default: 2000-01-01)",
    )
    parser.add_argument(
        "--end",
        default=DEFAULT_END.isoformat(),
        help="End Gregorian date YYYY-MM-DD (default: 2100-12-29)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: calendar_<start>_<end>.csv)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    start_date = parse_gregorian(args.start)
    end_date = parse_gregorian(args.end)

    try:
        rows = generate_rows(start_date, end_date)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    output_csv = args.output or default_output_path(start_date, end_date)
    write_csv(output_csv, rows)

    print(f"Generated {len(rows)} rows")
    print(f"Gregorian range: {format_gregorian(start_date)} -> {format_gregorian(end_date)}")
    print(f"Wrote {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
