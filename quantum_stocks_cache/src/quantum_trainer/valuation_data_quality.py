from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


RESEARCH_COLUMNS = {
    "symbol",
    "company_name",
    "per",
    "pbr",
}

MEMO_COLUMNS = {
    "symbol",
    "company_name",
    "evidence",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "valuation_source",
    "data_gap",
    "per",
    "pbr",
    "roe",
    "liabilities_to_equity",
    "market_cap",
    "valuation_status",
    "valuation_review_candidate",
    "order_status",
    "external_api_requested",
    "next_step",
]


@dataclass(frozen=True)
class ValuationDataQualityOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, str | int]


def run_valuation_data_quality(
    company_research_csv: Path | str,
    investment_memo_csv: Path | str,
    output_dir: Path | str,
) -> ValuationDataQualityOutput:
    research = _load_csv(Path(company_research_csv), RESEARCH_COLUMNS, "company research")
    memo = _load_csv(Path(investment_memo_csv), MEMO_COLUMNS, "investment memo")

    rows: list[dict[str, object]] = []
    for source in _ordered_symbols(research, memo):
        research_row = _row_for_symbol(research, source)
        memo_row = _row_for_symbol(memo, source)
        values = _valuation_values(research_row, memo_row)
        status = _valuation_status(values["per"], values["pbr"])
        rows.append(
            {
                "symbol": source,
                "company_name": _first_text(research_row.get("company_name"), memo_row.get("company_name")),
                "valuation_source": values["valuation_source"],
                "data_gap": values["data_gap"],
                "per": values["per"],
                "pbr": values["pbr"],
                "roe": values["roe"],
                "liabilities_to_equity": values["liabilities_to_equity"],
                "market_cap": values["market_cap"],
                "valuation_status": status,
                "valuation_review_candidate": _valuation_review_candidate(status),
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "next_step": _next_step(values["data_gap"], status),
            }
        )

    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    output_root = Path(output_dir).resolve() / "valuation_data_quality"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "valuation_data_quality.csv"
    markdown_path = output_root / "valuation_data_quality.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")

    summary = {
        "row_count": int(len(report)),
        "fallback_count": int((report["valuation_source"] == "INVESTMENT_MEMO_FALLBACK").sum()) if not report.empty else 0,
        "missing_count": int((report["valuation_source"] == "MISSING").sum()) if not report.empty else 0,
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
    }
    return ValuationDataQualityOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame


def _ordered_symbols(research: pd.DataFrame, memo: pd.DataFrame) -> list[str]:
    symbols: list[str] = []
    for frame in (memo, research):
        for symbol in frame["symbol"].astype(str):
            if symbol not in symbols:
                symbols.append(symbol)
    return symbols


def _row_for_symbol(frame: pd.DataFrame, symbol: str) -> pd.Series:
    row = frame.loc[frame["symbol"].astype(str) == symbol]
    if row.empty:
        return pd.Series(dtype=object)
    return row.iloc[0]


def _valuation_values(research: pd.Series, memo: pd.Series) -> dict[str, object]:
    research_per = _number(research.get("per"))
    research_pbr = _number(research.get("pbr"))
    memo_text = _memo_text(memo)
    memo_per = _number_from_text(memo_text, "PER")
    memo_pbr = _number_from_text(memo_text, "PBR")

    if research_per > 0.0 and research_pbr > 0.0:
        source = "COMPANY_RESEARCH"
        gap = "NO_GAP"
        per = research_per
        pbr = research_pbr
    elif memo_per > 0.0 and memo_pbr > 0.0:
        source = "INVESTMENT_MEMO_FALLBACK"
        gap = "RESEARCH_VALUATION_BLANK"
        per = memo_per
        pbr = memo_pbr
    else:
        source = "MISSING"
        gap = "VALUATION_DATA_REQUIRED"
        per = research_per if research_per > 0.0 else memo_per
        pbr = research_pbr if research_pbr > 0.0 else memo_pbr

    return {
        "valuation_source": source,
        "data_gap": gap,
        "per": round(per, 4),
        "pbr": round(pbr, 4),
        "roe": round(_percent_from_text(memo_text, "ROE"), 6),
        "liabilities_to_equity": round(_percent_from_text(memo_text, "total_liabilities_to_equity"), 6),
        "market_cap": _market_cap_from_text(memo_text),
    }


def _memo_text(memo: pd.Series) -> str:
    return "; ".join(
        str(memo.get(column, ""))
        for column in ("evidence", "risks", "manual_checks", "core_thesis", "next_action")
    )


def _valuation_status(per: object, pbr: object) -> str:
    per_value = _number(per)
    pbr_value = _number(pbr)
    if per_value <= 0.0 or pbr_value <= 0.0:
        return "VALUATION_DATA_REQUIRED"
    if per_value >= 35.0 or pbr_value >= 3.0:
        return "PREMIUM_REVIEW_REQUIRED"
    return "VALUATION_READY"


def _valuation_review_candidate(status: str) -> str:
    if status == "VALUATION_READY":
        return "PASS_CANDIDATE"
    return "UNKNOWN"


def _next_step(data_gap: object, status: str) -> str:
    if str(data_gap) == "VALUATION_DATA_REQUIRED":
        return "OpenDART/price refresh approval required before filling valuation fields"
    if str(data_gap) == "RESEARCH_VALUATION_BLANK":
        return "OpenDART/price refresh approval required before overwriting local valuation memo fallback"
    if status == "PREMIUM_REVIEW_REQUIRED":
        return "keep valuation_review UNKNOWN until premium is justified by earnings or pullback"
    return "use local valuation metrics in manual review proposal"


def _render_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Valuation Data Quality",
        "",
        "This report is local-only. It does not fetch prices, call OpenDART, edit manual review config, or place orders.",
        "",
        "| Symbol | Company | Source | Gap | PER | PBR | Status | Review | Order |",
        "|---|---|---|---|---:|---:|---|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.company_name} | {row.valuation_source} | {row.data_gap} | "
            f"{row.per:.2f} | {row.pbr:.2f} | {row.valuation_status} | "
            f"{row.valuation_review_candidate} | {row.order_status} |"
        )
    lines.extend(
        [
            "",
            f"- External API requested: {'NO'}",
            f"- Order status: {'NO_ORDER'}",
            "",
        ]
    )
    return "\n".join(lines)


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _number_from_text(text: str, label: str) -> float:
    match = re.search(rf"\b{re.escape(label)}\s*=\s*([0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
    if not match:
        return 0.0
    return _number(match.group(1))


def _percent_from_text(text: str, label: str) -> float:
    return _number_from_text(text, label) / 100.0


def _market_cap_from_text(text: str) -> str:
    match = re.search(r"\bmarket_cap\s*=\s*([^;]+)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def _first_text(*values: object) -> str:
    for value in values:
        text = str(value).strip()
        if text:
            return text
    return ""
