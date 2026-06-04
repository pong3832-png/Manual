from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


TREND_COLUMNS = {
    "symbol",
    "sector",
    "forecast_bias",
    "chase_risk",
    "trend_score",
}

OUTPUT_COLUMNS = [
    "scope",
    "sector",
    "symbol_count",
    "bullish_count",
    "watch_pullback_count",
    "watch_rebound_count",
    "bearish_count",
    "neutral_count",
    "unknown_count",
    "high_chase_count",
    "bullish_ratio",
    "bearish_ratio",
    "high_chase_ratio",
    "average_trend_score",
    "regime_status",
    "risk_posture",
    "order_status",
    "external_api_requested",
    "action_summary",
]


@dataclass(frozen=True)
class MarketRegimeOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_market_regime(
    trend_forecast_csv: Path | str,
    output_dir: Path | str,
) -> MarketRegimeOutput:
    trend = _load_trend_forecast(Path(trend_forecast_csv))
    report = _build_report(trend)

    output_root = Path(output_dir).resolve() / "market_regime"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "market_regime.csv"
    markdown_path = output_root / "market_regime.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "risk_on_count": int((report["regime_status"] == "RISK_ON").sum()) if not report.empty else 0,
        "extended_uptrend_count": int((report["regime_status"] == "EXTENDED_UPTREND").sum()) if not report.empty else 0,
        "risk_off_count": int((report["regime_status"] == "RISK_OFF").sum()) if not report.empty else 0,
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return MarketRegimeOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_trend_forecast(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Trend forecast CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(TREND_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Trend forecast CSV missing required columns: {missing}")
    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    frame["sector"] = frame["sector"].astype(str).str.strip().replace("", "UNKNOWN")
    return frame


def _build_report(trend: pd.DataFrame) -> pd.DataFrame:
    rows = [_summary_row(scope="MARKET", sector="ALL", frame=trend)]
    for sector, sector_frame in trend.groupby("sector", dropna=False):
        rows.append(_summary_row(scope="SECTOR", sector=str(sector), frame=sector_frame))
    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    report["_scope_rank"] = report["scope"].map({"MARKET": 0, "SECTOR": 1}).fillna(9)
    report = report.sort_values(
        ["_scope_rank", "regime_status", "symbol_count", "average_trend_score"],
        ascending=[True, True, False, False],
    )
    return report.drop(columns=["_scope_rank"]).reset_index(drop=True)


def _summary_row(scope: str, sector: str, frame: pd.DataFrame) -> dict[str, object]:
    count = int(len(frame))
    bullish_count = _bias_count(frame, "BULLISH")
    watch_pullback_count = _bias_count(frame, "WATCH_PULLBACK")
    watch_rebound_count = _bias_count(frame, "WATCH_REBOUND")
    bearish_count = _bias_count(frame, "BEARISH")
    neutral_count = _bias_count(frame, "NEUTRAL")
    unknown_count = _bias_count(frame, "UNKNOWN")
    high_chase_count = int((frame["chase_risk"].astype(str).str.upper() == "HIGH").sum()) if count else 0
    bullish_ratio = _ratio(bullish_count + watch_pullback_count, count)
    bearish_ratio = _ratio(bearish_count, count)
    high_chase_ratio = _ratio(high_chase_count, count)
    average_trend_score = round(float(pd.to_numeric(frame["trend_score"], errors="coerce").fillna(0).mean()), 4) if count else 0.0
    regime_status = _regime_status(
        bullish_ratio=bullish_ratio,
        bearish_ratio=bearish_ratio,
        high_chase_ratio=high_chase_ratio,
        watch_rebound_count=watch_rebound_count,
        count=count,
    )
    return {
        "scope": scope,
        "sector": sector,
        "symbol_count": count,
        "bullish_count": bullish_count,
        "watch_pullback_count": watch_pullback_count,
        "watch_rebound_count": watch_rebound_count,
        "bearish_count": bearish_count,
        "neutral_count": neutral_count,
        "unknown_count": unknown_count,
        "high_chase_count": high_chase_count,
        "bullish_ratio": round(bullish_ratio, 6),
        "bearish_ratio": round(bearish_ratio, 6),
        "high_chase_ratio": round(high_chase_ratio, 6),
        "average_trend_score": average_trend_score,
        "regime_status": regime_status,
        "risk_posture": _risk_posture(regime_status),
        "order_status": "NO_ORDER",
        "external_api_requested": "NO",
        "action_summary": _action_summary(regime_status),
    }


def _bias_count(frame: pd.DataFrame, bias: str) -> int:
    return int((frame["forecast_bias"].astype(str).str.upper() == bias).sum()) if not frame.empty else 0


def _ratio(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return value / total


def _regime_status(
    bullish_ratio: float,
    bearish_ratio: float,
    high_chase_ratio: float,
    watch_rebound_count: int,
    count: int,
) -> str:
    if count <= 0:
        return "NO_DATA"
    if bearish_ratio >= 0.55:
        return "RISK_OFF"
    if bullish_ratio >= 0.55 and high_chase_ratio >= 0.20:
        return "EXTENDED_UPTREND"
    if bullish_ratio >= 0.45:
        return "RISK_ON"
    if watch_rebound_count / count >= 0.35:
        return "RECOVERY_WATCH"
    return "MIXED"


def _risk_posture(regime_status: str) -> str:
    return {
        "RISK_ON": "SELECTIVE_BUY_REVIEW",
        "EXTENDED_UPTREND": "WAIT_PULLBACK",
        "RISK_OFF": "DEFENSIVE",
        "RECOVERY_WATCH": "WAIT_CONFIRMATION",
        "MIXED": "SELECTIVE_WATCH",
        "NO_DATA": "DATA_REQUIRED",
    }.get(regime_status, "SELECTIVE_WATCH")


def _action_summary(regime_status: str) -> str:
    if regime_status == "RISK_ON":
        return "broad trend supports selective review; keep order_status=NO_ORDER"
    if regime_status == "EXTENDED_UPTREND":
        return "trend is strong but crowded; wait for pullback before new entries; keep order_status=NO_ORDER"
    if regime_status == "RISK_OFF":
        return "downtrend breadth dominates; defensive posture; keep order_status=NO_ORDER"
    if regime_status == "RECOVERY_WATCH":
        return "rebound candidates are forming; wait for confirmation; keep order_status=NO_ORDER"
    if regime_status == "NO_DATA":
        return "trend data missing; refresh only with explicit approval; keep order_status=NO_ORDER"
    return "mixed market breadth; compare sectors before individual names; keep order_status=NO_ORDER"


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Market Regime",
        "",
        "Local-only market and sector breadth report built from `trend_forecast.csv`.",
        "It does not fetch prices, call external APIs, or place orders.",
        "",
        f"- Rows: {summary['row_count']}",
        f"- RISK_ON: {summary['risk_on_count']}",
        f"- EXTENDED_UPTREND: {summary['extended_uptrend_count']}",
        f"- RISK_OFF: {summary['risk_off_count']}",
        "- External API requested: NO",
        "- Order status: NO_ORDER",
        "",
        "| Scope | Sector | Regime | Posture | Symbols | Bullish | Pullback | Bearish | High Chase | Score |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.scope} | {row.sector} | {row.regime_status} | {row.risk_posture} | "
            f"{int(row.symbol_count)} | {int(row.bullish_count)} | {int(row.watch_pullback_count)} | "
            f"{int(row.bearish_count)} | {int(row.high_chase_count)} | {float(row.average_trend_score):.1f} |"
        )
    return "\n".join(lines).rstrip() + "\n"
