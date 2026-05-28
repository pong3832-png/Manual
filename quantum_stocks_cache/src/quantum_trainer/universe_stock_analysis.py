from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "latest_price",
    "latest_price_date",
    "research_score",
    "research_view",
    "decision",
    "expected_20d_return",
    "upside_probability",
    "return_20d",
    "ma20_gap",
    "drawdown_20d",
    "why_summary",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "sector",
    "analysis_status",
    "decision_status",
    "order_status",
    "price_trend_status",
    "alpha_status",
    "valuation_status",
    "risk_status",
    "latest_price",
    "latest_price_date",
    "research_score",
    "expected_20d_return",
    "upside_probability",
    "return_20d",
    "ma20_gap",
    "drawdown_20d",
    "per",
    "pbr",
    "reason_summary",
    "action_summary",
]


@dataclass(frozen=True)
class UniverseStockAnalysisOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int]


def run_universe_stock_analysis(
    company_research_csv: Path | str,
    output_dir: Path | str,
) -> UniverseStockAnalysisOutput:
    research = _load_company_research(Path(company_research_csv))
    report = _build_report(research)

    output_root = Path(output_dir).resolve() / "universe_stock_analysis"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "universe_stock_analysis.csv"
    markdown_path = output_root / "universe_stock_analysis.md"

    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    summary = {
        "row_count": int(len(report)),
        "buy_ready_count": int((report["decision_status"] == "BUY_READY").sum()),
        "wait_count": int((report["decision_status"] == "WAIT").sum()),
        "reject_count": int((report["decision_status"] == "REJECT").sum()),
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return UniverseStockAnalysisOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        report=report,
        summary=summary,
    )


def _load_company_research(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Company research CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Company research CSV missing required columns: {missing}")
    return frame


def _build_report(research: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in research.to_dict(orient="records"):
        trend_status = _price_trend_status(row)
        alpha_status = _alpha_status(row)
        valuation_status = _valuation_status(row)
        risk_status = _risk_status(row)
        decision_status = _decision_status(
            row=row,
            trend_status=trend_status,
            alpha_status=alpha_status,
            valuation_status=valuation_status,
            risk_status=risk_status,
        )
        rows.append(
            {
                "symbol": str(row["symbol"]),
                "company_name": str(row["company_name"]),
                "sector": str(row["sector"]),
                "analysis_status": "ANALYZED",
                "decision_status": decision_status,
                "order_status": "NO_ORDER",
                "price_trend_status": trend_status,
                "alpha_status": alpha_status,
                "valuation_status": valuation_status,
                "risk_status": risk_status,
                "latest_price": _number(row.get("latest_price")),
                "latest_price_date": str(row.get("latest_price_date", "")),
                "research_score": _number(row.get("research_score")),
                "expected_20d_return": _number(row.get("expected_20d_return")),
                "upside_probability": _number(row.get("upside_probability")),
                "return_20d": _number(row.get("return_20d")),
                "ma20_gap": _number(row.get("ma20_gap")),
                "drawdown_20d": _number(row.get("drawdown_20d")),
                "per": _number(row.get("per")),
                "pbr": _number(row.get("pbr")),
                "reason_summary": _reason_summary(
                    row=row,
                    trend_status=trend_status,
                    alpha_status=alpha_status,
                    valuation_status=valuation_status,
                    risk_status=risk_status,
                ),
                "action_summary": _action_summary(decision_status),
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _price_trend_status(row: dict[str, object]) -> str:
    return_20d = _number(row.get("return_20d"))
    ma20_gap = _number(row.get("ma20_gap"))
    if return_20d > 0.0 and ma20_gap > 0.0:
        return "TREND_OK"
    if return_20d <= 0.0 and ma20_gap <= 0.0:
        return "TREND_WEAK"
    return "TREND_MIXED"


def _alpha_status(row: dict[str, object]) -> str:
    decision = str(row.get("decision", "")).upper()
    if decision == "BUY_READY":
        return "ALPHA_BUY_READY"
    if decision == "WAIT":
        return "ALPHA_WAIT"
    if decision == "AVOID":
        return "ALPHA_AVOID"
    return "ALPHA_UNKNOWN"


def _valuation_status(row: dict[str, object]) -> str:
    per = _number(row.get("per"))
    pbr = _number(row.get("pbr"))
    if per <= 0.0 or pbr <= 0.0:
        return "VALUATION_UNKNOWN"
    if per > 30.0 or pbr > 3.0:
        return "VALUATION_EXPENSIVE"
    if per <= 20.0 and pbr <= 1.5:
        return "VALUATION_REASONABLE"
    return "VALUATION_NEUTRAL"


def _risk_status(row: dict[str, object]) -> str:
    if _number(row.get("drawdown_20d")) <= -0.10:
        return "RISK_REVIEW"
    if str(row.get("fundamental_view", "")).upper() == "FUNDAMENTAL_WEAK":
        return "RISK_REVIEW"
    return "RISK_OK"


def _decision_status(
    row: dict[str, object],
    trend_status: str,
    alpha_status: str,
    valuation_status: str,
    risk_status: str,
) -> str:
    research_view = str(row.get("research_view", "")).upper()
    if alpha_status == "ALPHA_AVOID" or research_view == "AVOID_FOR_NOW" or risk_status == "RISK_REVIEW":
        return "REJECT"
    if (
        alpha_status == "ALPHA_BUY_READY"
        and trend_status == "TREND_OK"
        and valuation_status != "VALUATION_EXPENSIVE"
        and risk_status == "RISK_OK"
    ):
        return "BUY_READY"
    return "WAIT"


def _reason_summary(
    row: dict[str, object],
    trend_status: str,
    alpha_status: str,
    valuation_status: str,
    risk_status: str,
) -> str:
    parts = [
        str(row.get("why_summary", "")).strip(),
        f"trend={trend_status}",
        f"alpha={alpha_status}",
        f"valuation={valuation_status}",
        f"risk={risk_status}",
    ]
    return "; ".join(part for part in parts if part)


def _action_summary(decision_status: str) -> str:
    if decision_status == "BUY_READY":
        return "BUY_READY candidate for manual gate and position sizing review; keep order_status=NO_ORDER."
    if decision_status == "REJECT":
        return "Exclude until alpha, trend, valuation, or risk condition recovers; keep order_status=NO_ORDER."
    return "Keep on watchlist until trend, alpha, valuation, and manual review improve; keep order_status=NO_ORDER."


def _render_markdown(report: pd.DataFrame, summary: dict[str, int]) -> str:
    lines = [
        "# Universe Stock Analysis",
        "",
        "This report analyzes every company in `company_research.csv` using the same local price, alpha, valuation, and risk rules.",
        "It is not an order ticket. Every row keeps `order_status=NO_ORDER`.",
        "",
        f"- Total analyzed: {summary['row_count']}",
        f"- BUY_READY: {summary['buy_ready_count']}",
        f"- WAIT: {summary['wait_count']}",
        f"- REJECT: {summary['reject_count']}",
        "",
        "| Symbol | Company | Decision | Trend | Alpha | Valuation | Risk | Score | Action |",
        "|---|---|---|---|---|---|---|---:|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            "| {symbol} | {company} | {decision} | {trend} | {alpha} | {valuation} | {risk} | {score:.2f} | {action} |".format(
                symbol=row.symbol,
                company=row.company_name,
                decision=row.decision_status,
                trend=row.price_trend_status,
                alpha=row.alpha_status,
                valuation=row.valuation_status,
                risk=row.risk_status,
                score=float(row.research_score),
                action=row.action_summary,
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
