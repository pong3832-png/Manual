from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


MARKET_RECOVERY_COLUMNS = {
    "scope",
    "sector",
    "recovery_status",
    "regime_status",
    "symbol_count",
    "bullish_ratio",
    "bearish_ratio",
    "high_chase_ratio",
    "order_status",
    "external_api_requested",
}

TREND_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "forecast_bias",
    "chase_risk",
    "trend_score",
    "research_score",
    "order_status",
    "external_api_requested",
}

OUTPUT_COLUMNS = [
    "sector",
    "rotation_status",
    "rotation_priority",
    "recovery_status",
    "regime_status",
    "symbol_count",
    "bullish_ratio",
    "bearish_ratio",
    "high_chase_ratio",
    "candidate_count",
    "bullish_candidate_count",
    "rebound_candidate_count",
    "high_chase_candidate_count",
    "opportunity_score",
    "top_candidates",
    "operator_action",
    "order_status",
    "external_api_requested",
    "broker_order_requested",
]


@dataclass(frozen=True)
class SectorRotationWatchOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_sector_rotation_watch(
    market_recovery_watch_csv: Path | str,
    trend_forecast_csv: Path | str,
    output_dir: Path | str,
    top_candidates_per_sector: int = 3,
) -> SectorRotationWatchOutput:
    recovery = _load_csv(Path(market_recovery_watch_csv), MARKET_RECOVERY_COLUMNS, "market recovery watch")
    trend = _load_csv(Path(trend_forecast_csv), TREND_COLUMNS, "trend forecast")
    report = _build_report(recovery, trend, top_candidates_per_sector=top_candidates_per_sector)

    output_root = Path(output_dir).resolve() / "sector_rotation_watch"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "sector_rotation_watch.csv"
    markdown_path = output_root / "sector_rotation_watch.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "leader_count": int((report["rotation_status"] == "RECOVERY_LEADER").sum()) if not report.empty else 0,
        "early_rotation_count": int((report["rotation_status"] == "EARLY_ROTATION").sum()) if not report.empty else 0,
        "defensive_wait_count": int((report["rotation_status"] == "DEFENSIVE_WAIT").sum()) if not report.empty else 0,
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return SectorRotationWatchOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame.copy()


def _build_report(
    recovery: pd.DataFrame,
    trend: pd.DataFrame,
    top_candidates_per_sector: int,
) -> pd.DataFrame:
    sectors = recovery.loc[recovery["scope"].astype(str).str.upper() == "SECTOR"].copy()
    trend_by_sector = {str(sector): frame.copy() for sector, frame in trend.groupby("sector", dropna=False)}

    rows: list[dict[str, object]] = []
    for row in sectors.to_dict(orient="records"):
        sector = str(row.get("sector", "")).strip()
        recovery_status = str(row.get("recovery_status", "")).strip().upper()
        rotation_status = _rotation_status(recovery_status)
        sector_trend = trend_by_sector.get(sector, pd.DataFrame(columns=trend.columns))
        rows.append(
            {
                "sector": sector,
                "rotation_status": rotation_status,
                "rotation_priority": _rotation_priority(rotation_status),
                "recovery_status": recovery_status,
                "regime_status": str(row.get("regime_status", "")).strip().upper(),
                "symbol_count": int(_number(row.get("symbol_count"))),
                "bullish_ratio": round(_number(row.get("bullish_ratio")), 6),
                "bearish_ratio": round(_number(row.get("bearish_ratio")), 6),
                "high_chase_ratio": round(_number(row.get("high_chase_ratio")), 6),
                "candidate_count": int(len(sector_trend)),
                "bullish_candidate_count": _bias_count(sector_trend, "BULLISH"),
                "rebound_candidate_count": _bias_count(sector_trend, "WATCH_REBOUND"),
                "high_chase_candidate_count": _high_chase_count(sector_trend),
                "opportunity_score": _opportunity_score(row, rotation_status, sector_trend),
                "top_candidates": _top_candidates(sector_trend, limit=top_candidates_per_sector),
                "operator_action": _operator_action(rotation_status),
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "broker_order_requested": "NO",
            }
        )
    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if report.empty:
        return report
    return report.sort_values(
        ["rotation_priority", "opportunity_score", "sector"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def _rotation_status(recovery_status: str) -> str:
    return {
        "RECOVERY_CONFIRMED": "RECOVERY_LEADER",
        "WATCH_CONFIRMATION": "EARLY_ROTATION",
        "SELECTIVE_SECTOR_WATCH": "SELECTIVE_ROTATION",
        "WAIT_OVERHEAT_COOLING": "OVERHEATED_WAIT",
        "WAIT_BREADTH_RECOVERY": "DEFENSIVE_WAIT",
        "DATA_REQUIRED": "DATA_REQUIRED",
    }.get(recovery_status, "SELECTIVE_ROTATION")


def _rotation_priority(rotation_status: str) -> int:
    return {
        "RECOVERY_LEADER": 1,
        "EARLY_ROTATION": 2,
        "SELECTIVE_ROTATION": 3,
        "OVERHEATED_WAIT": 4,
        "DEFENSIVE_WAIT": 5,
        "DATA_REQUIRED": 9,
    }.get(rotation_status, 9)


def _opportunity_score(row: dict[str, object], rotation_status: str, sector_trend: pd.DataFrame) -> float:
    base = {
        "RECOVERY_LEADER": 70.0,
        "EARLY_ROTATION": 60.0,
        "SELECTIVE_ROTATION": 45.0,
        "OVERHEATED_WAIT": 30.0,
        "DEFENSIVE_WAIT": 10.0,
        "DATA_REQUIRED": 0.0,
    }.get(rotation_status, 0.0)
    bullish = _number(row.get("bullish_ratio"))
    bearish = _number(row.get("bearish_ratio"))
    high_chase = _number(row.get("high_chase_ratio"))
    candidate_bonus = min(float(len(sector_trend)), 10.0) * 0.5
    return round(base + bullish * 25.0 + (1.0 - bearish) * 10.0 - high_chase * 20.0 + candidate_bonus, 4)


def _top_candidates(sector_trend: pd.DataFrame, limit: int) -> str:
    if sector_trend.empty or limit <= 0:
        return ""
    eligible = sector_trend.loc[
        (sector_trend["chase_risk"].astype(str).str.upper() != "HIGH")
        & sector_trend["forecast_bias"].astype(str).str.upper().isin({"BULLISH", "WATCH_REBOUND", "NEUTRAL"})
    ].copy()
    if eligible.empty:
        return ""
    eligible["_bias_rank"] = eligible["forecast_bias"].astype(str).str.upper().map(
        {"BULLISH": 3, "WATCH_REBOUND": 2, "NEUTRAL": 1}
    ).fillna(0)
    eligible["_trend_sort"] = eligible["trend_score"].apply(_number)
    eligible["_research_sort"] = eligible["research_score"].apply(_number)
    eligible = eligible.sort_values(["_bias_rank", "_trend_sort", "_research_sort", "symbol"], ascending=[False, False, False, True])
    labels: list[str] = []
    for row in eligible.head(limit).itertuples(index=False):
        company = str(row.company_name).strip() or str(row.symbol).strip()
        labels.append(f"{company}({row.symbol})")
    return "; ".join(labels)


def _operator_action(rotation_status: str) -> str:
    return {
        "RECOVERY_LEADER": "회복 선도 섹터. 그래도 후보별 수동 게이트와 가격 조건만 검토",
        "EARLY_ROTATION": "초기 회복 섹터. 추격 없이 후보만 관찰",
        "SELECTIVE_ROTATION": "선별 섹터. 강한 후보와 약한 후보를 분리해서 관찰",
        "OVERHEATED_WAIT": "과열. 눌림 전 추격 금지",
        "DEFENSIVE_WAIT": "방어 대기. 폭 회복 전 신규 진입 보류",
        "DATA_REQUIRED": "데이터 필요. 외부 갱신은 승인 후에만 실행",
    }.get(rotation_status, "섹터별 선별 관찰")


def _bias_count(frame: pd.DataFrame, bias: str) -> int:
    if frame.empty:
        return 0
    return int((frame["forecast_bias"].astype(str).str.upper() == bias).sum())


def _high_chase_count(frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    return int((frame["chase_risk"].astype(str).str.upper() == "HIGH").sum())


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Sector Rotation Watch",
        "",
        "Local-only sector rotation report. It does not fetch prices, call external APIs, or place orders.",
        "",
        f"- Rows: {summary['row_count']}",
        f"- RECOVERY_LEADER: {summary['leader_count']}",
        f"- EARLY_ROTATION: {summary['early_rotation_count']}",
        f"- DEFENSIVE_WAIT: {summary['defensive_wait_count']}",
        "- external_api_requested: NO",
        "- order_status: NO_ORDER",
        "",
        "| Sector | Status | Score | Candidates | Action | Order |",
        "|---|---|---:|---|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.sector} | {row.rotation_status} | {float(row.opportunity_score):.1f} | "
            f"{row.top_candidates} | {row.operator_action} | {row.order_status} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
