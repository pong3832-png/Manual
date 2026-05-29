from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from quantum_trainer.io import load_price_csv
from quantum_trainer.research_universe import normalize_research_universe


DEFAULT_REQUIRED_SYMBOLS = (
    "005930.KS",
    "005380.KS",
    "000660.KS",
    "028260.KS",
    "003550.KS",
    "012330.KS",
)


@dataclass(frozen=True)
class UniverseCoverageOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, str | int]


def run_universe_coverage(
    universe_csv: Path | str,
    output_dir: Path | str,
    prices_csv: Path | str | None = None,
    min_count: int = 20,
    max_count: int = 50,
    full_universe_min_count: int = 1000,
    min_price_coverage_ratio: float = 0.99,
    required_symbols: Sequence[str] | None = None,
) -> UniverseCoverageOutput:
    if min_count <= 0:
        raise ValueError("min_count must be greater than 0.")
    if max_count < min_count:
        raise ValueError("max_count must be greater than or equal to min_count.")

    universe_path = Path(universe_csv).resolve()
    if not universe_path.exists():
        raise FileNotFoundError(f"Research universe CSV not found: {universe_path}")

    source = pd.read_csv(universe_path, dtype=str).fillna("")
    universe = normalize_research_universe(source)
    symbols = universe["symbol"].astype(str).tolist()
    symbol_set = set(symbols)

    required = [_normalize_required_symbol(symbol) for symbol in (required_symbols or DEFAULT_REQUIRED_SYMBOLS)]
    required_missing = [symbol for symbol in required if symbol not in symbol_set]

    price_missing = _missing_price_symbols(symbols=symbols, prices_csv=prices_csv)
    count_status = _count_status(
        len(universe),
        min_count=min_count,
        max_count=max_count,
        full_universe_min_count=full_universe_min_count,
    )
    price_coverage_ratio = (len(symbols) - len(price_missing)) / len(symbols) if symbols else 0.0
    price_status = _price_status(
        price_missing=price_missing,
        coverage_ratio=price_coverage_ratio,
        min_price_coverage_ratio=min_price_coverage_ratio,
    )
    universe_status = (
        "PASS_CANDIDATE"
        if count_status in {"COUNT_OK", "FULL_UNIVERSE_OK"}
        and not required_missing
        and price_status in {"PRICE_COVERAGE_READY", "PRICE_COVERAGE_PARTIAL"}
        else "EXPAND_UNIVERSE"
    )

    report_row: dict[str, str | int] = {
        "universe_status": universe_status,
        "universe_count": int(len(universe)),
        "min_count": int(min_count),
        "max_count": int(max_count),
        "count_status": count_status,
        "sector_count": int(universe["sector"].replace("", "UNKNOWN").nunique()),
        "required_symbol_count": int(len(required)),
        "required_missing_count": int(len(required_missing)),
        "required_missing_symbols": ";".join(required_missing),
        "price_coverage_status": price_status,
        "price_coverage_ratio": round(float(price_coverage_ratio), 6),
        "price_missing_count": int(len(price_missing)),
        "price_missing_symbols": ";".join(price_missing),
        "order_status": "NO_ORDER",
        "external_api_requested": "NO",
        "next_step": _next_step(
            count_status=count_status,
            required_missing=required_missing,
            price_missing=price_missing,
            price_status=price_status,
        ),
    }

    output_root = Path(output_dir).resolve() / "universe_coverage"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "universe_coverage.csv"
    markdown_path = output_root / "universe_coverage.md"
    report = pd.DataFrame([report_row])
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report_row), encoding="utf-8")

    summary = {
        "universe_status": universe_status,
        "universe_count": int(len(universe)),
        "required_missing_count": int(len(required_missing)),
        "price_missing_count": int(len(price_missing)),
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
    }
    return UniverseCoverageOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        report=report,
        summary=summary,
    )


def _missing_price_symbols(symbols: Sequence[str], prices_csv: Path | str | None) -> list[str]:
    if prices_csv is None:
        return list(symbols)
    price_path = Path(prices_csv).resolve()
    if not price_path.exists():
        return list(symbols)
    prices = load_price_csv(price_path)
    available = set(prices.columns.astype(str))
    return [symbol for symbol in symbols if symbol not in available]


def _count_status(count: int, min_count: int, max_count: int, full_universe_min_count: int) -> str:
    if count < min_count:
        return "TOO_SMALL"
    if count >= full_universe_min_count:
        return "FULL_UNIVERSE_OK"
    if count > max_count:
        return "TOO_LARGE"
    return "COUNT_OK"


def _price_status(
    price_missing: Sequence[str],
    coverage_ratio: float,
    min_price_coverage_ratio: float,
) -> str:
    if not price_missing:
        return "PRICE_COVERAGE_READY"
    if coverage_ratio >= min_price_coverage_ratio:
        return "PRICE_COVERAGE_PARTIAL"
    return "PRICE_DATA_REQUIRED"


def _normalize_required_symbol(symbol: str) -> str:
    text = str(symbol).strip()
    if text.endswith(".KS") or text.endswith(".KQ"):
        return text
    if text.isdigit():
        return f"{text.zfill(6)}.KS"
    return text


def _next_step(
    count_status: str,
    required_missing: Sequence[str],
    price_missing: Sequence[str],
    price_status: str,
) -> str:
    if count_status == "TOO_SMALL":
        return "add more core companies until the universe reaches the target range"
    if count_status == "TOO_LARGE":
        return "trim the universe to the strongest 20-50 comparable companies"
    if required_missing:
        return "add missing core comparison companies before ranking"
    if price_missing and price_status == "PRICE_DATA_REQUIRED":
        return "refresh cached prices with explicit approval before ranking"
    return "run company research, manual gates, and dashboard review"


def _render_markdown(report: dict[str, str | int]) -> str:
    return "\n".join(
        [
            "# Universe Coverage",
            "",
            f"- Universe status: {report['universe_status']}",
            f"- Count: {report['universe_count']} / target {report['min_count']}-{report['max_count']} ({report['count_status']})",
            f"- Sector count: {report['sector_count']}",
            f"- Required missing: {report['required_missing_count']} {report['required_missing_symbols']}",
            f"- Price coverage: {report['price_coverage_status']} missing={report['price_missing_count']}",
            f"- Order status: {report['order_status']}",
            f"- External API requested: {report['external_api_requested']}",
            f"- Next step: {report['next_step']}",
            "",
            "This report is local-only. It does not fetch data, place orders, or update manual review config.",
            "",
        ]
    )
