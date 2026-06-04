from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


MARKET_REGIME_COLUMNS = {
    "scope",
    "sector",
    "symbol_count",
    "bullish_ratio",
    "bearish_ratio",
    "high_chase_ratio",
    "regime_status",
    "risk_posture",
    "order_status",
    "external_api_requested",
}

ENTRY_SIGNAL_COLUMNS = {
    "sector",
    "watch_status",
    "order_status",
}

OUTPUT_COLUMNS = [
    "scope",
    "sector",
    "recovery_status",
    "review_priority",
    "regime_status",
    "risk_posture",
    "symbol_count",
    "bullish_ratio",
    "bearish_ratio",
    "high_chase_ratio",
    "blocked_watch_count",
    "unlock_condition",
    "required_evidence",
    "review_cadence",
    "action_summary",
    "order_status",
    "external_api_requested",
    "broker_order_requested",
]


@dataclass(frozen=True)
class MarketRecoveryWatchOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_market_recovery_watch(
    market_regime_csv: Path | str,
    output_dir: Path | str,
    entry_signal_watch_csv: Path | str | None = None,
) -> MarketRecoveryWatchOutput:
    market_regime = _load_csv(Path(market_regime_csv), MARKET_REGIME_COLUMNS, "market regime")
    entry_signal = _load_optional_entry_signal(Path(entry_signal_watch_csv)) if entry_signal_watch_csv else pd.DataFrame()
    report = _build_report(market_regime, entry_signal)

    output_root = Path(output_dir).resolve() / "market_recovery_watch"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "market_recovery_watch.csv"
    markdown_path = output_root / "market_recovery_watch.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "breadth_wait_count": int((report["recovery_status"] == "WAIT_BREADTH_RECOVERY").sum()) if not report.empty else 0,
        "overheat_wait_count": int((report["recovery_status"] == "WAIT_OVERHEAT_COOLING").sum()) if not report.empty else 0,
        "confirmation_watch_count": int((report["recovery_status"] == "WATCH_CONFIRMATION").sum()) if not report.empty else 0,
        "confirmed_count": int((report["recovery_status"] == "RECOVERY_CONFIRMED").sum()) if not report.empty else 0,
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return MarketRecoveryWatchOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame.copy()


def _load_optional_entry_signal(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=sorted(ENTRY_SIGNAL_COLUMNS))
    return _load_csv(path, ENTRY_SIGNAL_COLUMNS, "entry signal watch")


def _build_report(market_regime: pd.DataFrame, entry_signal: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in market_regime.to_dict(orient="records"):
        regime = str(row.get("regime_status", "")).strip().upper()
        status = _recovery_status(regime)
        scope = str(row.get("scope", "")).strip().upper()
        sector = str(row.get("sector", "")).strip()
        rows.append(
            {
                "scope": scope,
                "sector": sector,
                "recovery_status": status,
                "review_priority": _review_priority(status),
                "regime_status": regime,
                "risk_posture": str(row.get("risk_posture", "")).strip().upper(),
                "symbol_count": int(_number(row.get("symbol_count"))),
                "bullish_ratio": round(_number(row.get("bullish_ratio")), 6),
                "bearish_ratio": round(_number(row.get("bearish_ratio")), 6),
                "high_chase_ratio": round(_number(row.get("high_chase_ratio")), 6),
                "blocked_watch_count": _blocked_watch_count(entry_signal, scope, sector),
                "unlock_condition": _unlock_condition(status),
                "required_evidence": _required_evidence(status),
                "review_cadence": _review_cadence(status),
                "action_summary": _action_summary(status),
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "broker_order_requested": "NO",
            }
        )
    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if report.empty:
        return report
    report["_scope_rank"] = report["scope"].map({"MARKET": 0, "SECTOR": 1}).fillna(9)
    report = report.sort_values(
        ["review_priority", "_scope_rank", "blocked_watch_count", "symbol_count"],
        ascending=[True, True, False, False],
    )
    return report.drop(columns=["_scope_rank"]).reset_index(drop=True)


def _blocked_watch_count(entry_signal: pd.DataFrame, scope: str, sector: str) -> int:
    if entry_signal.empty:
        return 0
    market_wait = entry_signal["watch_status"].astype(str).str.upper() == "WAIT_MARKET_REGIME"
    if scope == "MARKET":
        return int(market_wait.sum())
    sector_match = entry_signal["sector"].astype(str).str.strip() == sector
    return int((market_wait & sector_match).sum())


def _recovery_status(regime_status: str) -> str:
    if regime_status == "RISK_OFF":
        return "WAIT_BREADTH_RECOVERY"
    if regime_status == "EXTENDED_UPTREND":
        return "WAIT_OVERHEAT_COOLING"
    if regime_status == "RECOVERY_WATCH":
        return "WATCH_CONFIRMATION"
    if regime_status == "RISK_ON":
        return "RECOVERY_CONFIRMED"
    if regime_status == "NO_DATA":
        return "DATA_REQUIRED"
    return "SELECTIVE_SECTOR_WATCH"


def _review_priority(recovery_status: str) -> int:
    return {
        "WAIT_BREADTH_RECOVERY": 1,
        "WAIT_OVERHEAT_COOLING": 2,
        "WATCH_CONFIRMATION": 3,
        "SELECTIVE_SECTOR_WATCH": 4,
        "RECOVERY_CONFIRMED": 5,
        "DATA_REQUIRED": 9,
    }.get(recovery_status, 9)


def _unlock_condition(recovery_status: str) -> str:
    return {
        "WAIT_BREADTH_RECOVERY": "상승/눌림 30% 이상, 하락 55% 미만 확인",
        "WAIT_OVERHEAT_COOLING": "추격위험 20% 이하 또는 가격 눌림 확인",
        "WATCH_CONFIRMATION": "반등 후보가 늘고 RISK_ON 또는 MIXED 이상으로 안정",
        "SELECTIVE_SECTOR_WATCH": "섹터별 강도 차이를 확인하고 강한 섹터만 재검토",
        "RECOVERY_CONFIRMED": "회복 확인됨. 그래도 수동 게이트와 가격 조건 확인",
        "DATA_REQUIRED": "로컬 가격 흐름 데이터 확보 필요",
    }.get(recovery_status, "조건 확인 필요")


def _required_evidence(recovery_status: str) -> str:
    if recovery_status == "DATA_REQUIRED":
        return "가격 데이터 갱신은 사용자 승인 후에만 실행"
    return "로컬 trend_forecast, market_regime, entry_signal_watch 재생성"


def _review_cadence(recovery_status: str) -> str:
    if recovery_status == "RECOVERY_CONFIRMED":
        return "후보별 수동 게이트 검토 시 확인"
    if recovery_status == "DATA_REQUIRED":
        return "데이터 승인 이후 확인"
    return "매일 로컬 리포트 갱신 후 확인"


def _action_summary(recovery_status: str) -> str:
    return {
        "WAIT_BREADTH_RECOVERY": "폭 회복 전까지 신규 진입 보류",
        "WAIT_OVERHEAT_COOLING": "추격위험 해소 전까지 추격 금지",
        "WATCH_CONFIRMATION": "회복 초입 관찰. 확인 전 신규 진입 보류",
        "SELECTIVE_SECTOR_WATCH": "전체 매수장 아님. 섹터별 선별 관찰",
        "RECOVERY_CONFIRMED": "회복 확인. 후보별 수동 게이트 검토만 가능",
        "DATA_REQUIRED": "데이터 없이는 판단 보류",
    }.get(recovery_status, "신규 진입 보류")


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Market Recovery Watch",
        "",
        "Local-only market unlock report. It does not fetch prices, call external APIs, or place orders.",
        "",
        f"- Rows: {summary['row_count']}",
        f"- WAIT_BREADTH_RECOVERY: {summary['breadth_wait_count']}",
        f"- WAIT_OVERHEAT_COOLING: {summary['overheat_wait_count']}",
        f"- WATCH_CONFIRMATION: {summary['confirmation_watch_count']}",
        f"- RECOVERY_CONFIRMED: {summary['confirmed_count']}",
        "- external_api_requested: NO",
        "- order_status: NO_ORDER",
        "",
        "| Scope | Sector | Status | Regime | Blocked Watch | Unlock | Order |",
        "|---|---|---|---|---:|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.scope} | {row.sector} | {row.recovery_status} | {row.regime_status} | "
            f"{int(row.blocked_watch_count)} | {row.unlock_condition} | {row.order_status} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
