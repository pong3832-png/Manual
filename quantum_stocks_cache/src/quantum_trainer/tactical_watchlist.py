from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


EVENT_RANKING_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "final_watch_status",
    "rank_bucket",
    "final_rank_score",
    "quant_decision",
    "event_decision",
    "chase_risk",
    "entry_status",
    "market_regime_status",
    "sector_regime_status",
    "latest_price",
    "order_status",
    "external_api_requested",
}

ENTRY_WATCH_COLUMNS = {
    "symbol",
    "watch_status",
    "primary_blocker",
    "trigger_condition",
    "action_summary",
    "order_status",
    "external_api_requested",
    "broker_order_requested",
}

SECTOR_ROTATION_COLUMNS = {
    "sector",
    "rotation_status",
    "rotation_priority",
    "recovery_status",
    "regime_status",
    "opportunity_score",
    "operator_action",
    "order_status",
    "external_api_requested",
    "broker_order_requested",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "sector",
    "tactical_status",
    "tactical_priority",
    "priority_score",
    "final_watch_status",
    "entry_watch_status",
    "sector_rotation_status",
    "sector_recovery_status",
    "sector_regime_status",
    "final_rank_score",
    "chase_risk",
    "latest_price",
    "key_reason",
    "next_check",
    "operator_action",
    "order_status",
    "external_api_requested",
    "broker_order_requested",
]


@dataclass(frozen=True)
class TacticalWatchlistOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_tactical_watchlist(
    event_adjusted_ranking_csv: Path | str,
    entry_signal_watch_csv: Path | str,
    sector_rotation_watch_csv: Path | str,
    output_dir: Path | str,
    top_n: int = 30,
) -> TacticalWatchlistOutput:
    ranking = _load_csv(Path(event_adjusted_ranking_csv), EVENT_RANKING_COLUMNS, "event adjusted ranking")
    entry_watch = _load_optional_csv(Path(entry_signal_watch_csv), ENTRY_WATCH_COLUMNS)
    sector_rotation = _load_optional_csv(Path(sector_rotation_watch_csv), SECTOR_ROTATION_COLUMNS)
    report = _build_report(ranking=ranking, entry_watch=entry_watch, sector_rotation=sector_rotation, top_n=top_n)

    output_root = Path(output_dir).resolve() / "tactical_watchlist"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "tactical_watchlist.csv"
    markdown_path = output_root / "tactical_watchlist.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "ready_manual_review_count": int((report["tactical_status"] == "READY_MANUAL_REVIEW").sum()) if not report.empty else 0,
        "sector_recovery_watch_count": int((report["tactical_status"] == "SECTOR_RECOVERY_WATCH").sum()) if not report.empty else 0,
        "pullback_watch_count": int((report["tactical_status"] == "PULLBACK_WATCH").sum()) if not report.empty else 0,
        "market_defensive_wait_count": int((report["tactical_status"] == "MARKET_DEFENSIVE_WAIT").sum()) if not report.empty else 0,
        "overheated_wait_count": int((report["tactical_status"] == "OVERHEATED_WAIT").sum()) if not report.empty else 0,
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return TacticalWatchlistOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    frame = frame.copy()
    if "symbol" in frame.columns:
        frame["symbol"] = frame["symbol"].astype(str).str.strip()
    if "sector" in frame.columns:
        frame["sector"] = frame["sector"].astype(str).str.strip()
    return frame


def _load_optional_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=sorted(required_columns))
    return _load_csv(path, required_columns, path.stem.replace("_", " "))


def _build_report(
    ranking: pd.DataFrame,
    entry_watch: pd.DataFrame,
    sector_rotation: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    ordered = ranking.copy()
    ordered["_rank_bucket_sort"] = ordered["rank_bucket"].apply(_number)
    ordered["_score_sort"] = ordered["final_rank_score"].apply(_number)
    ordered = ordered.sort_values(["_rank_bucket_sort", "_score_sort", "symbol"], ascending=[True, False, True])
    if top_n > 0:
        ordered = ordered.head(top_n)

    entry_by_symbol = entry_watch.drop_duplicates("symbol").set_index("symbol") if not entry_watch.empty else None
    sector_by_name = sector_rotation.drop_duplicates("sector").set_index("sector") if not sector_rotation.empty else None

    rows: list[dict[str, object]] = []
    for row in ordered.to_dict(orient="records"):
        symbol = str(row.get("symbol", "")).strip()
        sector = str(row.get("sector", "")).strip()
        entry = entry_by_symbol.loc[symbol] if entry_by_symbol is not None and symbol in entry_by_symbol.index else pd.Series(dtype=object)
        sector_row = sector_by_name.loc[sector] if sector_by_name is not None and sector in sector_by_name.index else pd.Series(dtype=object)
        status = _tactical_status(row=row, entry=entry, sector_row=sector_row)
        rows.append(
            {
                "symbol": symbol,
                "company_name": str(row.get("company_name", "")),
                "sector": sector,
                "tactical_status": status,
                "tactical_priority": _tactical_priority(status),
                "priority_score": _priority_score(row=row, entry=entry, sector_row=sector_row, tactical_status=status),
                "final_watch_status": str(row.get("final_watch_status", "")),
                "entry_watch_status": str(_value(entry, "watch_status", row.get("entry_status", ""))),
                "sector_rotation_status": str(_value(sector_row, "rotation_status", "")),
                "sector_recovery_status": str(_value(sector_row, "recovery_status", "")),
                "sector_regime_status": str(_value(sector_row, "regime_status", row.get("sector_regime_status", ""))),
                "final_rank_score": _number(row.get("final_rank_score")),
                "chase_risk": str(row.get("chase_risk", "")),
                "latest_price": _number(row.get("latest_price")),
                "key_reason": _key_reason(status, row, entry, sector_row),
                "next_check": _next_check(status, entry, sector_row),
                "operator_action": _operator_action(status, entry, sector_row),
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "broker_order_requested": "NO",
            }
        )

    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if report.empty:
        return report
    return report.sort_values(["tactical_priority", "priority_score", "symbol"], ascending=[True, False, True]).reset_index(drop=True)


def _tactical_status(row: dict[str, object], entry: pd.Series, sector_row: pd.Series) -> str:
    final_status = str(row.get("final_watch_status", "")).upper()
    entry_status = str(_value(entry, "watch_status", row.get("entry_status", ""))).upper()
    sector_status = str(_value(sector_row, "rotation_status", "")).upper()
    event_decision = str(row.get("event_decision", "")).upper()

    if entry_status == "READY_MANUAL_REVIEW" or final_status == "READY_REVIEW":
        return "READY_MANUAL_REVIEW"
    if sector_status == "OVERHEATED_WAIT":
        return "OVERHEATED_WAIT"
    if final_status == "WAIT_PULLBACK" or entry_status == "WAIT_PRICE_PULLBACK":
        return "PULLBACK_WATCH"
    if (final_status == "MARKET_WAIT" or entry_status == "WAIT_MARKET_REGIME") and sector_status in {
        "RECOVERY_LEADER",
        "EARLY_ROTATION",
        "SELECTIVE_ROTATION",
    }:
        return "SECTOR_RECOVERY_WATCH"
    if final_status == "MARKET_WAIT" or entry_status == "WAIT_MARKET_REGIME":
        return "MARKET_DEFENSIVE_WAIT"
    if final_status in {"EVENT_ONLY", "EVENT_WATCH"} or event_decision in {"EVENT_FOCUS", "EVENT_WATCH"}:
        return "EVENT_MONITOR"
    return "LOW_PRIORITY"


def _tactical_priority(status: str) -> int:
    return {
        "READY_MANUAL_REVIEW": 1,
        "SECTOR_RECOVERY_WATCH": 2,
        "PULLBACK_WATCH": 3,
        "MARKET_DEFENSIVE_WAIT": 4,
        "OVERHEATED_WAIT": 5,
        "EVENT_MONITOR": 6,
        "LOW_PRIORITY": 9,
    }.get(status, 9)


def _priority_score(row: dict[str, object], entry: pd.Series, sector_row: pd.Series, tactical_status: str) -> float:
    score = _number(row.get("final_rank_score"))
    sector_status = str(_value(sector_row, "rotation_status", "")).upper()
    score += {
        "RECOVERY_LEADER": 20.0,
        "EARLY_ROTATION": 12.0,
        "SELECTIVE_ROTATION": 6.0,
        "DEFENSIVE_WAIT": -15.0,
        "OVERHEATED_WAIT": -35.0,
        "DATA_REQUIRED": -20.0,
    }.get(sector_status, 0.0)
    score += {
        "READY_MANUAL_REVIEW": 30.0,
        "SECTOR_RECOVERY_WATCH": 15.0,
        "PULLBACK_WATCH": 0.0,
        "MARKET_DEFENSIVE_WAIT": -10.0,
        "OVERHEATED_WAIT": -20.0,
        "EVENT_MONITOR": 2.0,
        "LOW_PRIORITY": -20.0,
    }.get(tactical_status, 0.0)
    if _is_chase_risk(row.get("chase_risk", "")):
        score -= 8.0
    if str(_value(entry, "primary_blocker", "")).upper() == "FILING_REVIEW":
        score -= 5.0
    return round(score, 4)


def _key_reason(status: str, row: dict[str, object], entry: pd.Series, sector_row: pd.Series) -> str:
    sector_status = str(_value(sector_row, "rotation_status", "")).upper()
    final_status = str(row.get("final_watch_status", "")).upper()
    entry_status = str(_value(entry, "watch_status", row.get("entry_status", ""))).upper()
    if status == "READY_MANUAL_REVIEW":
        return "종목 조건은 수동 검토 후보. 그래도 최종 확인과 주문은 별도"
    if status == "SECTOR_RECOVERY_WATCH":
        return f"{sector_status or 'SECTOR'} 섹터가 회복 관찰권이고 종목은 {final_status or entry_status} 상태"
    if status == "PULLBACK_WATCH":
        return "종목은 강하지만 추격위험 또는 가격 눌림 대기"
    if status == "MARKET_DEFENSIVE_WAIT":
        return "시장 또는 섹터 폭이 아직 방어적"
    if status == "OVERHEATED_WAIT":
        return "섹터 과열. 눌림 전 추격 금지"
    if status == "EVENT_MONITOR":
        return "이벤트 관찰 대상. 정량/수동 게이트 통과 전 주문 금지"
    return "우선순위 낮음"


def _next_check(status: str, entry: pd.Series, sector_row: pd.Series) -> str:
    trigger = str(_value(entry, "trigger_condition", "")).strip()
    if status == "READY_MANUAL_REVIEW":
        return "수동 6개 게이트와 자본 계획을 확인"
    if status == "SECTOR_RECOVERY_WATCH":
        return trigger or "시장 폭 회복, 섹터 회복 지속, 종목 추격위험 완화 확인"
    if status == "PULLBACK_WATCH":
        return trigger or "MA20 부근 눌림, 변동성 완화, chase_risk 하락 확인"
    if status == "OVERHEATED_WAIT":
        return str(_value(sector_row, "operator_action", "")).strip() or "섹터 과열 냉각 후 재검토"
    if status == "MARKET_DEFENSIVE_WAIT":
        return trigger or "시장/섹터 regime이 RISK_OFF에서 벗어나는지 확인"
    if status == "EVENT_MONITOR":
        return "이벤트가 실적/수주/가동률로 이어지는 근거 확인"
    return "상위 리포트 재생성 후 재평가"


def _operator_action(status: str, entry: pd.Series, sector_row: pd.Series) -> str:
    if status == "READY_MANUAL_REVIEW":
        return "수동 검토만 진행. 승인 전 주문 없음"
    if status == "SECTOR_RECOVERY_WATCH":
        return "섹터 회복 후보만 관찰. 시장 게이트 해제 전 신규 주문 없음"
    if status == "PULLBACK_WATCH":
        return "눌림 확인 전 추격 금지"
    if status == "MARKET_DEFENSIVE_WAIT":
        return "폭 회복 전까지 신규 진입 보류"
    if status == "OVERHEATED_WAIT":
        return "과열 구간. 냉각 전 추격 금지"
    if status == "EVENT_MONITOR":
        return "이벤트 근거만 모니터링. 매수 허가 아님"
    return str(_value(entry, "action_summary", _value(sector_row, "operator_action", "관찰 우선순위 낮음")))


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Tactical Watchlist",
        "",
        f"- row_count: {summary['row_count']}",
        f"- ready_manual_review_count: {summary['ready_manual_review_count']}",
        f"- sector_recovery_watch_count: {summary['sector_recovery_watch_count']}",
        f"- pullback_watch_count: {summary['pullback_watch_count']}",
        f"- market_defensive_wait_count: {summary['market_defensive_wait_count']}",
        f"- overheated_wait_count: {summary['overheated_wait_count']}",
        f"- external_api_requested: {summary['external_api_requested']}",
        f"- order_status: {summary['order_status']}",
        "",
        "## Top Rows",
        "",
    ]
    if report.empty:
        lines.append("No tactical watchlist rows.")
        return "\n".join(lines) + "\n"

    for row in report.head(20).to_dict(orient="records"):
        lines.append(
            "- {symbol} {company_name}: {status}, score={score}, sector={sector}, next={next_check}, order_status={order_status}".format(
                symbol=row["symbol"],
                company_name=row["company_name"],
                status=row["tactical_status"],
                score=row["priority_score"],
                sector=row["sector_rotation_status"],
                next_check=row["next_check"],
                order_status=row["order_status"],
            )
        )
    return "\n".join(lines) + "\n"


def _number(value: object) -> float:
    try:
        if value == "":
            return 0.0
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if pd.isna(number):
        return 0.0
    return number


def _value(row: pd.Series, key: str, default: object = "") -> object:
    if row.empty:
        return default
    value = row.get(key, default)
    if pd.isna(value):
        return default
    return value


def _is_chase_risk(value: object) -> bool:
    return str(value).strip().upper() in {"YES", "HIGH", "TRUE", "1"}
