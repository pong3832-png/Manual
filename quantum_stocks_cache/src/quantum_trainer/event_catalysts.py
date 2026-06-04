from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


EVENT_INPUT_COLUMNS = {
    "symbol",
    "catalyst_title",
    "catalyst_type",
    "impact_level",
    "event_status",
    "source",
    "summary",
}

EVENT_OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "catalyst_title",
    "catalyst_type",
    "impact_level",
    "event_status",
    "source",
    "summary",
    "event_score",
    "event_decision",
    "chase_risk",
    "research_score",
    "research_view",
    "quant_decision",
    "return_20d",
    "ma20_gap",
    "extension_risk",
    "action_summary",
    "order_status",
    "external_api_requested",
]

RESEARCH_DEFAULTS = {
    "company_name": "",
    "research_score": 0.0,
    "research_view": "",
    "decision": "",
    "return_20d": 0.0,
    "ma20_gap": 0.0,
    "drawdown_20d": 0.0,
    "extension_risk": "ENTRY_RANGE_OK",
}


@dataclass(frozen=True)
class EventCatalystsOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_event_catalysts(
    event_csv: Path | str,
    company_research_csv: Path | str,
    output_dir: Path | str,
    as_of: str | None = None,
) -> EventCatalystsOutput:
    output_root = Path(output_dir).resolve() / "event_catalysts"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "event_catalysts.csv"
    markdown_path = output_root / "event_catalysts.md"

    event_path = Path(event_csv).resolve()
    if not event_path.exists():
        report = pd.DataFrame(columns=EVENT_OUTPUT_COLUMNS)
        summary: dict[str, int | str] = {
            "input_status": "NO_EVENT_INPUT",
            "event_count": 0,
            "focus_count": 0,
            "wait_pullback_count": 0,
            "external_api_requested": "NO",
        }
        report.to_csv(csv_path, index=False, encoding="utf-8-sig")
        markdown_path.write_text(_render_markdown(report, summary, as_of), encoding="utf-8")
        return EventCatalystsOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)

    events = _load_event_input(event_path)
    research = _load_company_research(Path(company_research_csv))
    report = _build_report(events=events, research=research)
    report = report.sort_values(["event_score", "research_score", "symbol"], ascending=[False, False, True])
    report = report.reset_index(drop=True)

    summary = {
        "input_status": "READY",
        "event_count": int(len(report)),
        "focus_count": int((report["event_decision"] == "EVENT_FOCUS").sum()),
        "wait_pullback_count": int((report["event_decision"] == "WAIT_PULLBACK_EVENT").sum()),
        "external_api_requested": "NO",
    }
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report, summary, as_of), encoding="utf-8")
    return EventCatalystsOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_event_input(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path).fillna("")
    missing = sorted(EVENT_INPUT_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Event catalyst CSV missing required columns: {missing}")
    if "company_name" not in frame.columns:
        frame["company_name"] = ""
    frame = frame.copy()
    for column in EVENT_INPUT_COLUMNS.union({"company_name"}):
        frame[column] = frame[column].astype(str).str.strip()
    return frame


def _load_company_research(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Company research CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    if "symbol" not in frame.columns:
        raise ValueError("Company research CSV must include a 'symbol' column.")
    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    for column, default in RESEARCH_DEFAULTS.items():
        if column not in frame.columns:
            frame[column] = default
    return frame


def _build_report(events: pd.DataFrame, research: pd.DataFrame) -> pd.DataFrame:
    research_by_symbol = research.drop_duplicates(subset=["symbol"]).set_index("symbol")
    rows: list[dict[str, object]] = []
    for event in events.itertuples(index=False):
        symbol = str(event.symbol)
        research_row = research_by_symbol.loc[symbol] if symbol in research_by_symbol.index else pd.Series(dtype=object)
        score = _event_score(
            catalyst_type=str(event.catalyst_type),
            impact_level=str(event.impact_level),
            event_status=str(event.event_status),
            research_row=research_row,
        )
        chase = _chase_risk(research_row)
        decision = _event_decision(score, chase)
        company_name = str(event.company_name).strip() or str(_value(research_row, "company_name", symbol))
        rows.append(
            {
                "symbol": symbol,
                "company_name": company_name,
                "catalyst_title": str(event.catalyst_title),
                "catalyst_type": str(event.catalyst_type).upper(),
                "impact_level": str(event.impact_level).upper(),
                "event_status": str(event.event_status).upper(),
                "source": str(event.source),
                "summary": str(event.summary),
                "event_score": score,
                "event_decision": decision,
                "chase_risk": "YES" if chase else "NO",
                "research_score": _number(_value(research_row, "research_score", 0.0)),
                "research_view": str(_value(research_row, "research_view", "")),
                "quant_decision": str(_value(research_row, "decision", "")),
                "return_20d": _number(_value(research_row, "return_20d", 0.0)),
                "ma20_gap": _number(_value(research_row, "ma20_gap", 0.0)),
                "extension_risk": str(_value(research_row, "extension_risk", "ENTRY_RANGE_OK")),
                "action_summary": _action_summary(decision),
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
            }
        )
    return pd.DataFrame(rows, columns=EVENT_OUTPUT_COLUMNS)


def _event_score(
    catalyst_type: str,
    impact_level: str,
    event_status: str,
    research_row: pd.Series,
) -> float:
    impact_scores = {"HIGH": 45.0, "MEDIUM": 30.0, "LOW": 15.0}
    type_scores = {
        "DIRECT_MEETING": 25.0,
        "AI_PARTNERSHIP": 20.0,
        "GPU_INFRA": 20.0,
        "SUPPLY_CHAIN": 18.0,
        "ORDER_CONTRACT": 25.0,
        "EARNINGS_GUIDANCE": 20.0,
        "THEME_SPILLOVER": 10.0,
    }
    status_scores = {"CONFIRMED": 20.0, "UPCOMING": 18.0, "REPORTED": 15.0, "RUMORED": 8.0, "PAST": 5.0}
    score = (
        impact_scores.get(impact_level.upper(), 20.0)
        + type_scores.get(catalyst_type.upper(), 10.0)
        + status_scores.get(event_status.upper(), 8.0)
    )
    if _number(_value(research_row, "research_score", 0.0)) >= 60.0:
        score += 5.0
    if str(_value(research_row, "decision", "")).upper() == "BUY_READY":
        score += 5.0
    return float(min(score, 100.0))


def _chase_risk(research_row: pd.Series) -> bool:
    extension = str(_value(research_row, "extension_risk", "ENTRY_RANGE_OK")).upper()
    return (
        extension in {"OVEREXTENDED_WAIT", "EXTREME_EXTENSION"}
        or _number(_value(research_row, "return_20d", 0.0)) >= 0.20
        or _number(_value(research_row, "ma20_gap", 0.0)) >= 0.15
    )


def _event_decision(score: float, chase_risk: bool) -> str:
    if score >= 70.0 and chase_risk:
        return "WAIT_PULLBACK_EVENT"
    if score >= 70.0:
        return "EVENT_FOCUS"
    if score >= 50.0:
        return "EVENT_WATCH"
    return "BACKGROUND_EVENT"


def _action_summary(event_decision: str) -> str:
    if event_decision == "WAIT_PULLBACK_EVENT":
        return "이벤트 촉매는 강하지만 단기 급등/이격 부담이 있어 추격 금지. 눌림과 거래량 안정 확인."
    if event_decision == "EVENT_FOCUS":
        return "이벤트 직접성이 높음. 정량 게이트, 가격 조건, 수동 검토를 함께 확인. 주문 실행 없음."
    if event_decision == "EVENT_WATCH":
        return "이벤트 후보로 관찰. 가격 추격보다 다음 공시/실적 확인 우선."
    return "배경 이벤트로만 기록. 매수 판단에 직접 반영하지 않음."


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str], as_of: str | None) -> str:
    lines = [
        "# 뉴스/이벤트 촉매",
        "",
        "로컬 수동 입력 이벤트를 정량 후보와 결합한 참고 리포트입니다.",
        "외부 뉴스/API 호출 없음. 주문 실행 없음.",
        "",
        f"- 기준일: {as_of or 'UNKNOWN'}",
        f"- 입력 상태: {summary['input_status']}",
        f"- 이벤트 수: {summary['event_count']}",
        f"- 핵심 이벤트: {summary['focus_count']}",
        f"- 눌림 대기 이벤트: {summary['wait_pullback_count']}",
        f"- external_api_requested: {summary['external_api_requested']}",
        "",
        "| 순위 | 종목 | 이벤트 | 점수 | 판단 | 추격위험 | 대응 |",
        "|---:|---|---|---:|---|---|---|",
    ]
    if report.empty:
        lines.append("| - | - | 로컬 이벤트 입력 없음 | 0 | NO_EVENT_INPUT | - | 이벤트 CSV를 준비하면 표시됩니다 |")
    else:
        for rank, row in enumerate(report.itertuples(index=False), start=1):
            lines.append(
                f"| {rank} | {row.symbol} {row.company_name} | {row.catalyst_title} | "
                f"{float(row.event_score):.1f} | {row.event_decision} | {row.chase_risk} | {row.action_summary} |"
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
