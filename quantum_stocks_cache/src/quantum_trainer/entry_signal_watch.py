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
    "market_risk_posture",
    "sector_regime_status",
    "sector_risk_posture",
    "latest_price",
    "order_status",
    "external_api_requested",
}

PRE_BUY_COLUMNS = {
    "symbol",
    "decision_status",
    "readiness_blockers",
    "buy_ban_reasons",
    "entry_price_low",
    "entry_price_high",
    "order_status",
}

TREND_COLUMNS = {
    "symbol",
    "forecast_bias",
    "chase_risk",
    "trend_score",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "sector",
    "watch_status",
    "trigger_priority",
    "final_watch_status",
    "decision_status",
    "entry_status",
    "primary_blocker",
    "market_regime_status",
    "sector_regime_status",
    "forecast_bias",
    "chase_risk",
    "latest_price",
    "entry_price_low",
    "entry_price_high",
    "trigger_condition",
    "required_evidence",
    "review_cadence",
    "action_summary",
    "order_status",
    "external_api_requested",
    "broker_order_requested",
]


@dataclass(frozen=True)
class EntrySignalWatchOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_entry_signal_watch(
    event_adjusted_ranking_csv: Path | str,
    pre_buy_decision_csv: Path | str,
    trend_forecast_csv: Path | str,
    output_dir: Path | str,
    top_n: int = 30,
) -> EntrySignalWatchOutput:
    ranking = _load_csv(Path(event_adjusted_ranking_csv), EVENT_RANKING_COLUMNS, "event adjusted ranking")
    pre_buy = _load_optional_csv(Path(pre_buy_decision_csv), PRE_BUY_COLUMNS)
    trend = _load_optional_csv(Path(trend_forecast_csv), TREND_COLUMNS)

    report = _build_report(ranking=ranking, pre_buy=pre_buy, trend=trend, top_n=top_n)

    output_root = Path(output_dir).resolve() / "entry_signal_watch"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "entry_signal_watch.csv"
    markdown_path = output_root / "entry_signal_watch.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "market_wait_count": int((report["watch_status"] == "WAIT_MARKET_REGIME").sum()),
        "pullback_wait_count": int((report["watch_status"] == "WAIT_PRICE_PULLBACK").sum()),
        "filing_wait_count": int((report["watch_status"] == "WAIT_FILING_EVIDENCE").sum()),
        "manual_wait_count": int((report["watch_status"] == "WAIT_MANUAL_GATES").sum()),
        "event_only_count": int((report["watch_status"] == "WATCH_EVENT_ONLY").sum()),
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return EntrySignalWatchOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    return frame


def _load_optional_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=sorted(required_columns))
    return _load_csv(path, required_columns, path.stem.replace("_", " "))


def _build_report(
    ranking: pd.DataFrame,
    pre_buy: pd.DataFrame,
    trend: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    ordered = ranking.copy()
    ordered["_rank_bucket_sort"] = ordered["rank_bucket"].apply(_number)
    ordered["_score_sort"] = ordered["final_rank_score"].apply(_number)
    ordered = ordered.sort_values(["_rank_bucket_sort", "_score_sort", "symbol"], ascending=[True, False, True])
    if top_n > 0:
        ordered = ordered.head(top_n)

    pre_by_symbol = pre_buy.drop_duplicates("symbol").set_index("symbol") if not pre_buy.empty else None
    trend_by_symbol = trend.drop_duplicates("symbol").set_index("symbol") if not trend.empty else None

    rows: list[dict[str, object]] = []
    for row in ordered.to_dict(orient="records"):
        symbol = str(row["symbol"])
        pre_row = pre_by_symbol.loc[symbol] if pre_by_symbol is not None and symbol in pre_by_symbol.index else pd.Series(dtype=object)
        trend_row = trend_by_symbol.loc[symbol] if trend_by_symbol is not None and symbol in trend_by_symbol.index else pd.Series(dtype=object)
        blocker = _primary_blocker(row, pre_row, trend_row)
        watch_status = _watch_status(blocker)
        rows.append(
            {
                "symbol": symbol,
                "company_name": row.get("company_name", ""),
                "sector": row.get("sector", ""),
                "watch_status": watch_status,
                "trigger_priority": _trigger_priority(watch_status),
                "final_watch_status": row.get("final_watch_status", ""),
                "decision_status": str(pre_row.get("decision_status", row.get("quant_decision", ""))),
                "entry_status": row.get("entry_status", ""),
                "primary_blocker": blocker,
                "market_regime_status": row.get("market_regime_status", ""),
                "sector_regime_status": row.get("sector_regime_status", ""),
                "forecast_bias": str(trend_row.get("forecast_bias", "")),
                "chase_risk": str(trend_row.get("chase_risk", row.get("chase_risk", ""))),
                "latest_price": _number(row.get("latest_price")),
                "entry_price_low": _number(pre_row.get("entry_price_low", 0)),
                "entry_price_high": _number(pre_row.get("entry_price_high", 0)),
                "trigger_condition": _trigger_condition(blocker),
                "required_evidence": _required_evidence(blocker),
                "review_cadence": _review_cadence(blocker),
                "action_summary": _action_summary(blocker),
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "broker_order_requested": "NO",
            }
        )
    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    return report.sort_values(["trigger_priority", "symbol"], ascending=[True, True]).reset_index(drop=True)


def _primary_blocker(row: dict[str, object], pre_buy: pd.Series, trend: pd.Series) -> str:
    final_status = str(row.get("final_watch_status", "")).upper()
    entry_status = str(row.get("entry_status", "")).upper()
    blockers = f"{pre_buy.get('readiness_blockers', '')}; {pre_buy.get('buy_ban_reasons', '')}".lower()
    trend_bias = str(trend.get("forecast_bias", "")).upper()
    trend_chase = str(trend.get("chase_risk", row.get("chase_risk", ""))).upper()
    event_decision = str(row.get("event_decision", "")).upper()

    if final_status == "MARKET_WAIT" or entry_status == "MARKET_WAIT" or "market regime" in blockers:
        return "MARKET_REGIME"
    if final_status == "WAIT_PULLBACK" or trend_bias == "WATCH_PULLBACK" or trend_chase == "HIGH":
        return "PRICE_PULLBACK"
    if "filing risk hold" in blockers or "filing risk summary not available" in blockers:
        return "FILING_REVIEW"
    if "manual gate" in blockers or "manual review" in blockers:
        return "MANUAL_REVIEW"
    if final_status == "READY_REVIEW":
        return "USER_CONFIRMATION"
    if event_decision == "EVENT_FOCUS" or final_status in {"EVENT_ONLY", "EVENT_WATCH"}:
        return "EVENT_EVIDENCE"
    return "LOW_PRIORITY"


def _watch_status(blocker: str) -> str:
    return {
        "MARKET_REGIME": "WAIT_MARKET_REGIME",
        "PRICE_PULLBACK": "WAIT_PRICE_PULLBACK",
        "FILING_REVIEW": "WAIT_FILING_EVIDENCE",
        "MANUAL_REVIEW": "WAIT_MANUAL_GATES",
        "USER_CONFIRMATION": "READY_MANUAL_REVIEW",
        "EVENT_EVIDENCE": "WATCH_EVENT_ONLY",
        "LOW_PRIORITY": "LOW_PRIORITY",
    }.get(blocker, "LOW_PRIORITY")


def _trigger_priority(watch_status: str) -> int:
    return {
        "WAIT_MARKET_REGIME": 1,
        "WAIT_PRICE_PULLBACK": 2,
        "WAIT_FILING_EVIDENCE": 3,
        "WAIT_MANUAL_GATES": 4,
        "READY_MANUAL_REVIEW": 5,
        "WATCH_EVENT_ONLY": 6,
        "LOW_PRIORITY": 9,
    }.get(watch_status, 9)


def _trigger_condition(blocker: str) -> str:
    return {
        "MARKET_REGIME": "Market/sector posture clears from RISK_OFF/DEFENSIVE or wait-pullback state.",
        "PRICE_PULLBACK": "Forecast bias is no longer WATCH_PULLBACK and chase_risk is not HIGH.",
        "FILING_REVIEW": "Filing risk summary is available and no HOLD_REVIEW or fatal issue remains.",
        "MANUAL_REVIEW": "Manual six-gate review is confirmed by the user; do not auto-write actual config.",
        "USER_CONFIRMATION": "User confirms exact price band, thesis, and risk controls outside this report.",
        "EVENT_EVIDENCE": "Event stays relevant and quant/trend evidence improves enough for review.",
    }.get(blocker, "No near-term trigger; keep on low-priority watch.")


def _required_evidence(blocker: str) -> str:
    return {
        "MARKET_REGIME": "Regenerate trend_forecast and market_regime from local cache; external refresh requires approval.",
        "PRICE_PULLBACK": "Check local trend_forecast for lower chase risk and updated entry band.",
        "FILING_REVIEW": "Use existing filing summaries or request approved OpenDART review for the specific symbol.",
        "MANUAL_REVIEW": "Prepare proposal only; final manual actual config requires explicit user confirmation.",
        "USER_CONFIRMATION": "Human decision only; this repository still keeps order_status=NO_ORDER.",
        "EVENT_EVIDENCE": "Use local manual event input unless live news/API is explicitly approved.",
    }.get(blocker, "No extra evidence requested.")


def _review_cadence(blocker: str) -> str:
    return {
        "MARKET_REGIME": "Daily after local reports refresh.",
        "PRICE_PULLBACK": "Daily while candidate remains in top watch ranking.",
        "FILING_REVIEW": "After filing evidence changes or a user-approved filing review.",
        "MANUAL_REVIEW": "When the user is ready to confirm review gates.",
        "USER_CONFIRMATION": "At the moment of human review; still no automatic order.",
        "EVENT_EVIDENCE": "During the event window only.",
    }.get(blocker, "Weekly or when ranking changes.")


def _action_summary(blocker: str) -> str:
    return {
        "MARKET_REGIME": "시장 회복 전까지 신규 진입 보류.",
        "PRICE_PULLBACK": "추격 금지. 눌림과 이격 해소를 먼저 확인.",
        "FILING_REVIEW": "공시 리스크 근거가 정리될 때까지 대기.",
        "MANUAL_REVIEW": "수동 6개 게이트 확정 전까지 대기.",
        "USER_CONFIRMATION": "사람이 가격과 리스크를 확인해야 하는 검토 상태.",
        "EVENT_EVIDENCE": "이벤트 관찰만. 정량/가격 근거가 붙기 전까지 대기.",
    }.get(blocker, "낮은 우선순위. 신규 매수 검토 대상 아님.")


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Entry Signal Watch",
        "",
        "Local-only wait-trigger report. It does not fetch data, place orders, or write manual review config.",
        "",
        f"- Rows: {summary['row_count']}",
        f"- WAIT_MARKET_REGIME: {summary['market_wait_count']}",
        f"- WAIT_PRICE_PULLBACK: {summary['pullback_wait_count']}",
        f"- WAIT_FILING_EVIDENCE: {summary['filing_wait_count']}",
        f"- WAIT_MANUAL_GATES: {summary['manual_wait_count']}",
        f"- WATCH_EVENT_ONLY: {summary['event_only_count']}",
        "- external_api_requested: NO",
        "- order_status: NO_ORDER",
        "",
        "| Symbol | Company | Status | Blocker | Trigger | Order |",
        "|---|---|---|---|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.company_name} | {row.watch_status} | {row.primary_blocker} | "
            f"{row.trigger_condition} | {row.order_status} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
