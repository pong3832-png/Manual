from __future__ import annotations

import csv
from pathlib import Path


REQUIRED_COLUMNS = {"total_capital_krw"}


def load_total_capital_krw(path: Path | str) -> float | None:
    csv_path = Path(path)
    if not csv_path.exists():
        return None

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS.difference(fieldnames))
        if missing:
            raise ValueError(f"Capital actual CSV missing required columns: {missing}")

        row = next(reader, None)
        if row is None:
            return None

    raw_value = str(row.get("total_capital_krw", "")).strip()
    try:
        total_capital = float(raw_value)
    except ValueError as exc:
        raise ValueError("total_capital_krw must be a number.") from exc

    if total_capital <= 0:
        raise ValueError("total_capital_krw must be greater than 0.")
    return total_capital
