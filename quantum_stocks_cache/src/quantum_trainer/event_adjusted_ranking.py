from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


UNIVERSE_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
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
}

EVENT_COLUMNS = {
    "symbol",
    "company_name",
    "catalyst_title",
    "event_score",
    "event_decision",
    "chase_risk",
    "action_summary",
}

TREND_FORECAST_COLUMNS = {
    "symbol",
    "forecast_bias",
    "chase_risk",
}

MARKET_REGIME_COLUMNS = {
    "scope",
    "sector",
    "regime_status",
    "risk_posture",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "sector",
    "final_watch_status",
    "rank_bucket",
    "final_rank_score",
    "quant_decision",
    "research_score",
    "event_decision",
    "event_score",
    "chase_risk",
    "entry_status",
    "market_regime_status",
    "market_risk_posture",
    "sector_regime_status",
    "sector_risk_posture",
    "latest_price",
    "expected_20d_return",
    "upside_probability",
    "return_20d",
    "ma20_gap",
    "valuation_status",
    "risk_status",
    "catalyst_title",
    "action_summary",
    "order_status",
    "external_api_requested",
]


@dataclass(frozen=True)
class EventAdjustedRankingOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_event_adjusted_ranking(
    universe_csv: Path | str,
    event_csv: Path | str,
    output_dir: Path | str,
    trend_forecast_csv: Path | str | None = None,
    market_regime_csv: Path | str | None = None,
) -> EventAdjustedRankingOutput:
    universe = _load_universe(Path(universe_csv))
    events, event_input_status = _load_events(Path(event_csv))
    trend_forecast = _load_trend_forecast(Path(trend_forecast_csv)) if trend_forecast_csv else pd.DataFrame(columns=sorted(TREND_FORECAST_COLUMNS))
    market_regime = _load_market_regime(Path(market_regime_csv)) if market_regime_csv else pd.DataFrame(columns=sorted(MARKET_REGIME_COLUMNS))
    report = _build_report(universe=universe, events=events, trend_forecast=trend_forecast, market_regime=market_regime)
    report = report.sort_values(["rank_bucket", "final_rank_score", "symbol"], ascending=[True, False, True])
    report = report.reset_index(drop=True)

    output_root = Path(output_dir).resolve() / "event_adjusted_ranking"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "event_adjusted_ranking.csv"
    markdown_path = output_root / "event_adjusted_ranking.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    summary = {
        "row_count": int(len(report)),
        "ready_count": int((report["final_watch_status"] == "READY_REVIEW").sum()),
        "pullback_count": int((report["final_watch_status"] == "WAIT_PULLBACK").sum()),
        "market_wait_count": int((report["final_watch_status"] == "MARKET_WAIT").sum()),
        "event_only_count": int((report["final_watch_status"] == "EVENT_ONLY").sum()),
        "event_input_status": event_input_status,
        "external_api_requested": "NO",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return EventAdjustedRankingOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_universe(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Universe stock analysis CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(UNIVERSE_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Universe stock analysis CSV missing required columns: {missing}")
    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    return frame


def _load_events(path: Path) -> tuple[pd.DataFrame, str]:
    if not path.exists():
        return pd.DataFrame(columns=sorted(EVENT_COLUMNS)), "NO_EVENT_REPORT"
    frame = pd.read_csv(path).fillna("")
    missing = sorted(EVENT_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Event catalysts CSV missing required columns: {missing}")
    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    return frame, "READY"


def _load_trend_forecast(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=sorted(TREND_FORECAST_COLUMNS))
    frame = pd.read_csv(path).fillna("")
    missing = sorted(TREND_FORECAST_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Trend forecast CSV missing required columns: {missing}")
    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    return frame


def _load_market_regime(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=sorted(MARKET_REGIME_COLUMNS))
    frame = pd.read_csv(path).fillna("")
    missing = sorted(MARKET_REGIME_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Market regime CSV missing required columns: {missing}")
    frame = frame.copy()
    frame["scope"] = frame["scope"].astype(str).str.strip().str.upper()
    frame["sector"] = frame["sector"].astype(str).str.strip()
    return frame


def _build_report(
    universe: pd.DataFrame,
    events: pd.DataFrame,
    trend_forecast: pd.DataFrame,
    market_regime: pd.DataFrame,
) -> pd.DataFrame:
    event_by_symbol = events.drop_duplicates(subset=["symbol"]).set_index("symbol") if not events.empty else None
    trend_by_symbol = (
        trend_forecast.drop_duplicates(subset=["symbol"]).set_index("symbol") if not trend_forecast.empty else None
    )
    rows: list[dict[str, object]] = []
    for row in universe.to_dict(orient="records"):
        symbol = str(row["symbol"])
        event = event_by_symbol.loc[symbol] if event_by_symbol is not None and symbol in event_by_symbol.index else pd.Series(dtype=object)
        trend = trend_by_symbol.loc[symbol] if trend_by_symbol is not None and symbol in trend_by_symbol.index else pd.Series(dtype=object)
        regime_context = _market_regime_context(market_regime, str(row.get("sector", "")))
        event_score = _number(_value(event, "event_score", 0.0))
        event_decision = str(_value(event, "event_decision", "NO_EVENT"))
        chase_risk = _is_chase_risk(row=row, event=event, trend=trend)
        market_blocks_entry = _market_regime_blocks_entry(regime_context)
        final_status = _final_watch_status(
            quant_decision=str(row.get("decision_status", "")),
            event_decision=event_decision,
            chase_risk=chase_risk,
            market_blocks_entry=market_blocks_entry,
        )
        rows.append(
            {
                "symbol": symbol,
                "company_name": str(row.get("company_name", "")),
                "sector": str(row.get("sector", "")),
                "final_watch_status": final_status,
                "rank_bucket": _rank_bucket(final_status),
                "final_rank_score": _final_rank_score(row, event_score, chase_risk),
                "quant_decision": str(row.get("decision_status", "")),
                "research_score": _number(row.get("research_score")),
                "event_decision": event_decision,
                "event_score": event_score,
                "chase_risk": "YES" if chase_risk else "NO",
                "entry_status": _entry_status(final_status, chase_risk),
                "market_regime_status": str(regime_context.get("market_regime_status", "")),
                "market_risk_posture": str(regime_context.get("market_risk_posture", "")),
                "sector_regime_status": str(regime_context.get("sector_regime_status", "")),
                "sector_risk_posture": str(regime_context.get("sector_risk_posture", "")),
                "latest_price": _number(row.get("latest_price")),
                "expected_20d_return": _number(row.get("expected_20d_return")),
                "upside_probability": _number(row.get("upside_probability")),
                "return_20d": _number(row.get("return_20d")),
                "ma20_gap": _number(row.get("ma20_gap")),
                "valuation_status": str(row.get("valuation_status", "")),
                "risk_status": str(row.get("risk_status", "")),
                "catalyst_title": str(_value(event, "catalyst_title", "")),
                "action_summary": _action_summary(final_status),
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _market_regime_context(frame: pd.DataFrame, sector: str) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)
    market = frame.loc[(frame["scope"] == "MARKET") & (frame["sector"].str.upper() == "ALL")]
    sector_frame = frame.loc[(frame["scope"] == "SECTOR") & (frame["sector"] == sector)]
    market_row = market.iloc[0] if not market.empty else pd.Series(dtype=object)
    sector_row = sector_frame.iloc[0] if not sector_frame.empty else pd.Series(dtype=object)
    return pd.Series(
        {
            "market_regime_status": str(market_row.get("regime_status", "")),
            "market_risk_posture": str(market_row.get("risk_posture", "")),
            "sector_regime_status": str(sector_row.get("regime_status", "")),
            "sector_risk_posture": str(sector_row.get("risk_posture", "")),
        }
    )


def _market_regime_blocks_entry(regime_context: pd.Series) -> bool:
    if regime_context.empty:
        return False
    return _regime_blocks(
        str(regime_context.get("market_regime_status", "")),
        str(regime_context.get("market_risk_posture", "")),
    ) or _regime_blocks(
        str(regime_context.get("sector_regime_status", "")),
        str(regime_context.get("sector_risk_posture", "")),
    )


def _regime_blocks(regime_status: str, risk_posture: str) -> bool:
    return regime_status.upper() in {"RISK_OFF", "EXTENDED_UPTREND", "RECOVERY_WATCH", "NO_DATA"} or risk_posture.upper() in {
        "DEFENSIVE",
        "WAIT_PULLBACK",
        "WAIT_CONFIRMATION",
        "DATA_REQUIRED",
    }


def _final_watch_status(
    quant_decision: str,
    event_decision: str,
    chase_risk: bool,
    market_blocks_entry: bool,
) -> str:
    quant = quant_decision.upper()
    event = event_decision.upper()
    if quant == "BUY_READY" and market_blocks_entry:
        return "MARKET_WAIT"
    if quant == "BUY_READY" and not chase_risk:
        return "READY_REVIEW"
    if quant == "BUY_READY" and chase_risk:
        return "WAIT_PULLBACK"
    if event == "EVENT_FOCUS":
        return "EVENT_ONLY"
    if event in {"WAIT_PULLBACK_EVENT", "EVENT_WATCH"}:
        return "EVENT_WATCH"
    if quant == "WAIT":
        return "QUANT_WAIT"
    return "LOW_PRIORITY"


def _rank_bucket(final_status: str) -> int:
    return {
        "READY_REVIEW": 1,
        "MARKET_WAIT": 2,
        "WAIT_PULLBACK": 2,
        "EVENT_ONLY": 3,
        "EVENT_WATCH": 4,
        "QUANT_WAIT": 5,
        "LOW_PRIORITY": 6,
    }.get(final_status, 9)


def _final_rank_score(row: dict[str, object], event_score: float, chase_risk: bool) -> float:
    score = _number(row.get("research_score")) * 0.65 + event_score * 0.35
    if str(row.get("decision_status", "")).upper() == "BUY_READY":
        score += 8.0
    if str(row.get("risk_status", "")).upper() == "RISK_REVIEW":
        score -= 12.0
    if chase_risk:
        score -= 8.0
    return round(max(0.0, min(score, 100.0)), 6)


def _is_chase_risk(row: dict[str, object], event: pd.Series, trend: pd.Series) -> bool:
    if str(_value(event, "chase_risk", "NO")).upper() == "YES":
        return True
    if str(_value(trend, "chase_risk", "LOW")).upper() == "HIGH":
        return True
    if str(_value(trend, "forecast_bias", "")).upper() == "WATCH_PULLBACK":
        return True
    return _number(row.get("return_20d")) >= 0.25 or _number(row.get("ma20_gap")) >= 0.15


def _entry_status(final_status: str, chase_risk: bool) -> str:
    if final_status == "MARKET_WAIT":
        return "MARKET_WAIT"
    if chase_risk:
        return "WAIT_PULLBACK"
    return "ENTRY_REVIEW"


def _action_summary(final_status: str) -> str:
    if final_status == "READY_REVIEW":
        return "정량과 이벤트가 충돌하지 않습니다. 그래도 수동 게이트와 매수가를 확인하고 주문은 직접 실행합니다."
    if final_status == "MARKET_WAIT":
        return "개별 후보가 좋아도 시장/섹터 흐름이 불리합니다. 신규 진입은 보류하고 방어적으로 관찰합니다."
    if final_status == "WAIT_PULLBACK":
        return "후보 강도는 높지만 단기 이격이 큽니다. 추격 금지, 눌림 대기."
    if final_status == "EVENT_ONLY":
        return "이벤트 직접성은 높지만 정량 게이트가 부족합니다. 단기 뉴스 관찰만."
    if final_status == "EVENT_WATCH":
        return "이벤트 후보입니다. 가격, 공시, 실적 근거가 붙기 전까지 관찰."
    if final_status == "QUANT_WAIT":
        return "정량 대기 후보입니다. 이벤트나 추세 회복이 필요합니다."
    return "우선순위 낮음. 신규 매수 검토 대상 아님."


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# 이벤트 조정 최종 감시 랭킹",
        "",
        "정량 점수, 이벤트 촉매, 추격위험을 합친 로컬 감시 랭킹입니다.",
        "실제 주문 실행 문서가 아니며 모든 행은 `NO_ORDER`입니다.",
        "",
        f"- Row count: {summary['row_count']}",
        f"- Ready review: {summary['ready_count']}",
        f"- Wait pullback: {summary['pullback_count']}",
        f"- Market wait: {summary['market_wait_count']}",
        f"- Event only: {summary['event_only_count']}",
        f"- Event input: {summary['event_input_status']}",
        f"- external_api_requested: {summary['external_api_requested']}",
        "",
        "| Rank | Symbol | Company | Final | Score | Quant | Event | Chase | Action |",
        "|---:|---|---|---|---:|---|---|---|---|",
    ]
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        lines.append(
            f"| {rank} | {row.symbol} | {row.company_name} | {row.final_watch_status} | "
            f"{float(row.final_rank_score):.1f} | {row.quant_decision} | {row.event_decision} | "
            f"{row.chase_risk} | {row.action_summary} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _value(row: pd.Series, column: str, default: object) -> object:
    if row.empty or column not in row.index:
        return default
    return row[column]


def _number(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
