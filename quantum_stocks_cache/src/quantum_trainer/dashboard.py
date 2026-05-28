from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd


PROFIT_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "profit_focus_status",
    "conviction_score",
    "expected_20d_return",
    "upside_probability",
    "ma20_gap",
    "return_20d",
    "per",
    "pbr",
    "why_profit_candidate",
    "why_not_now",
    "invalidation_rule",
    "next_step",
}

MEMO_COLUMNS = {
    "symbol",
    "company_name",
    "memo_status",
    "order_status",
    "core_thesis",
    "evidence",
    "risks",
    "manual_checks",
    "loss_defense",
    "next_action",
}

GATE_COLUMNS = {
    "symbol",
    "company_name",
    "decision_gate_status",
    "order_status",
    "gate_reason",
    "filing_review",
    "earnings_review",
    "business_driver_review",
    "valuation_review",
    "loss_rule_review",
    "capital_plan_review",
    "loss_defense",
}

REVIEW_COLUMNS = [
    "filing_review",
    "earnings_review",
    "business_driver_review",
    "valuation_review",
    "loss_rule_review",
    "capital_plan_review",
]

FILING_RISK_COLUMNS = {
    "symbol",
    "risk_id",
    "risk_title",
    "source_checks",
    "evidence_count",
    "key_evidence",
    "fatal_risk",
    "gate_opinion",
    "monitoring_rule",
}

PRE_BUY_COLUMNS = {
    "symbol",
    "company_name",
    "decision_status",
    "order_status",
    "buy_reasons",
    "buy_ban_reasons",
    "entry_price_low",
    "entry_price_high",
    "staged_buy_plan",
    "stop_loss_rule",
    "next_review_date",
}

MANUAL_REVIEW_DRAFT_COLUMNS = {
    "symbol",
    "company_name",
    "filing_review",
    "earnings_review",
    "business_driver_review",
    "valuation_review",
    "loss_rule_review",
    "capital_plan_review",
    "recommended_actual_action",
    "review_notes",
}

MANUAL_REVIEW_PROPOSAL_COLUMNS = {
    "symbol",
    "filing_review",
    "earnings_review",
    "business_driver_review",
    "valuation_review",
    "loss_rule_review",
    "capital_plan_review",
    "review_notes",
    "proposal_status",
    "approval_required",
    "apply_target",
    "source_action",
}

MANUAL_REVIEW_APPLY_PLAN_COLUMNS = {
    "symbol",
    "apply_mode",
    "ready_to_apply",
    "confirm_required",
    "actual_config_written",
    "actual_output_csv",
    "blocker",
    "candidate_source",
}

UNIVERSE_STOCK_COLUMNS = {
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
    "research_score",
    "expected_20d_return",
    "upside_probability",
    "reason_summary",
    "action_summary",
}

ORDER_CANDIDATE_COLUMNS = {
    "symbol",
    "company_name",
    "order_status",
    "candidate_shares",
    "estimated_order_value",
    "capital_status",
    "latest_price",
    "target_value",
    "execution_mode",
}

CAPITAL_SCENARIO_COLUMNS = {
    "symbol",
    "company_name",
    "scenario_capital",
    "scenario_status",
    "order_status",
    "execution_mode",
    "latest_price",
    "max_position_weight",
    "cash_buffer_weight",
    "target_position_value",
    "target_position_shares",
    "first_tranche_value",
    "first_tranche_shares",
    "second_tranche_value",
    "second_tranche_shares",
    "final_tranche_value",
    "final_tranche_shares",
}

CAPITAL_PLAN_COLUMNS = {
    "symbol",
    "company_name",
    "capital_plan_review",
    "amount_status",
    "order_status",
    "max_position_weight",
    "cash_buffer_weight",
    "first_tranche_pct",
    "second_tranche_pct",
    "final_tranche_pct",
    "add_condition",
    "reduce_condition",
    "stop_condition",
    "immediate_halt_condition",
    "review_notes",
}

PERFORMANCE_TRACKING_COLUMNS = {
    "symbol",
    "company_name",
    "tracking_status",
    "buy_date",
    "buy_price",
    "shares",
    "latest_price",
    "latest_price_date",
    "invested_value",
    "current_value",
    "unrealized_pnl",
    "unrealized_return",
    "one_week_check_date",
    "one_month_check_date",
    "quarter_check_date",
    "one_week_due",
    "one_month_due",
    "quarter_due",
    "thesis",
    "thesis_status",
    "stop_loss_rule",
    "review_action",
    "order_status",
    "broker_order_requested",
    "next_step",
}

OPERATING_STATUS_COLUMNS = {
    "completion_status",
    "usage_status",
    "done_message",
    "top_symbol",
    "company_name",
    "decision_status",
    "decision_gate_status",
    "manual_actual_written",
    "capital_status",
    "universe_status",
    "price_coverage_status",
    "order_candidate_status",
    "order_status",
    "external_api_requested",
    "broker_order_requested",
    "blockers",
    "next_step",
    "dashboard_path",
}

SYMBOL_ANALYSIS_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "market",
    "code",
    "universe_action",
    "analysis_status",
    "local_pipeline_ready",
    "price_data_status",
    "price_rows",
    "min_samples_required",
    "blocking_reason",
    "company_research_rank",
    "latest_price",
    "latest_price_date",
    "research_score",
    "research_view",
    "decision",
    "why_summary",
    "company_research_csv",
    "company_research_md",
    "order_status",
    "external_api_requested",
    "broker_order_requested",
    "next_step",
}

UNIVERSE_COVERAGE_COLUMNS = {
    "universe_status",
    "universe_count",
    "min_count",
    "max_count",
    "count_status",
    "sector_count",
    "required_symbol_count",
    "required_missing_count",
    "required_missing_symbols",
    "price_coverage_status",
    "price_missing_count",
    "price_missing_symbols",
    "order_status",
    "external_api_requested",
    "next_step",
}


STATUS_KO = {
    "BUY_READY": "매수 검토 가능",
    "WAIT": "기다림",
    "REJECT": "제외",
    "NO_ORDER": "자동 주문 없음",
    "DONE": "완료",
    "NOT_DONE": "아직 준비 중",
    "READY_FOR_REVIEW_USE": "화면 사용 가능",
    "READY_FOR_SIZING_REVIEW": "수량 검토 가능",
    "READY_FOR_MANUAL_REVIEW": "수동 검토 가능",
    "WAITING_MANUAL_EVIDENCE": "수동 근거 확인 대기",
    "PASS": "통과",
    "FAIL": "실패",
    "UNKNOWN": "확인 필요",
    "PASS_CANDIDATE": "통과 후보",
    "PASS_CANDIDATE_WITH_MONITORING": "통과 후보(모니터링 필요)",
    "HOLD_REVIEW": "보류 검토",
    "EXCLUDE": "제외",
    "CORE_FOCUS": "핵심 후보",
    "WAIT_RISK": "위험 확인",
    "NEEDS_CHECKLIST": "체크리스트 필요",
    "WATCH_ONLY": "관찰만",
    "CAPITAL_PROVIDED": "자본금 입력됨",
    "CAPITAL_REQUIRED": "자본금 필요",
    "CAPITAL_AMOUNT_REQUIRED": "투자금 입력 필요",
    "PRICE_COVERAGE_READY": "가격 데이터 준비",
    "PRICE_DATA_REQUIRED": "가격 데이터 필요",
    "EXPAND_UNIVERSE": "비교군 확대 필요",
    "PASS_CANDIDATE_UNIVERSE": "비교군 통과",
    "TOO_SMALL": "비교군 부족",
    "REVIEW_ONLY": "검토 전용",
    "BLOCKED_CAPITAL_REQUIRED": "자본금 확인 전 보류",
    "MANUAL_REVIEW_ONLY": "수동 검토 전용",
    "SCENARIO_REVIEW_ONLY": "시나리오 검토용",
    "DRY_RUN": "미리보기",
    "READY_FOR_USER_CONFIRMATION": "사용자 확인 대기",
    "DO_NOT_COPY_AUTOMATICALLY": "자동 반영 금지",
    "YES": "예",
    "NO": "아니오",
    "ANALYSIS_READY": "분석 가능",
    "DATA_REQUIRED": "데이터 필요",
    "READY": "준비됨",
    "MISSING": "데이터 없음",
    "ADDED": "추가됨",
    "TREND_OK": "추세 양호",
    "TREND_WEAK": "추세 약함",
    "ALPHA_BUY_READY": "상승 후보",
    "ALPHA_WAIT": "대기",
    "ALPHA_AVOID": "피함",
    "VALUATION_NEUTRAL": "밸류에이션 중립",
    "VALUATION_UNKNOWN": "밸류 확인 필요",
    "RISK_OK": "위험 낮음",
    "RISK_REVIEW": "위험 검토",
    "WATCHLIST": "관찰 목록",
    "TRACKING_ACTIVE": "성과 추적 중",
    "NO_TRADE_JOURNAL": "매수 기록 없음",
    "ONE_WEEK_REVIEW_DUE": "1주 점검 필요",
    "ONE_MONTH_REVIEW_DUE": "1개월 점검 필요",
    "QUARTER_REVIEW_DUE": "분기 점검 필요",
    "REDUCE_OR_STOP_REVIEW_DUE": "축소/중단 검토",
    "HOLD_AND_MONITOR": "보유 관찰",
    "WRITE_TRADE_JOURNAL_AFTER_BUY": "매수 후 기록 필요",
    "INTACT": "유지",
    "BROKEN": "깨짐",
    "NOT_STARTED": "시작 전",
}

TEXT_REPLACEMENTS = {
    "BUY_READY candidate for manual gate and position sizing review": "매수 검토 후보입니다. 수동 확인과 수량 검토가 필요합니다",
    "keep order_status=NO_ORDER": "자동 주문은 실행하지 않습니다",
    "SMA20 holds": "20일선 유지",
    "no new filing/earnings blocker appears": "새 공시/실적 차단 사유가 없을 때",
    "manual gate remains clean": "수동 확인 항목이 계속 통과일 때",
    "manual gate FAIL": "수동 확인 실패",
    "fatal filing risk": "치명적 공시 리스크",
    "manual gate 실패": "수동 확인 실패",
    "or thesis break stops all additional buys immediately": "또는 투자 논리가 깨지면 추가 매수를 즉시 중단",
    "missing cached price history": "캐시된 가격 기록이 없습니다",
    "conviction_score=": "확신 점수 ",
    "upside_probability=": "상승 확률 ",
    "decision gate waiting manual evidence": "수동 근거 확인 대기",
    "manual gate not ready": "수동 확인이 끝나지 않았습니다",
    "manual gate required": "수동 확인이 필요합니다",
    "manual review required": "수동 검토가 필요합니다",
    "capital amount required": "투자금 입력이 필요합니다",
    "actual manual review config not applied": "최종 수동 검토값이 아직 반영되지 않았습니다",
    "waiting for explicit user confirmation": "사용자 최종 확인을 기다립니다",
    "Confirm manual review and enter capital before any real buy review.": "실제 매수 검토 전 수동 확인과 투자금 입력을 끝내세요.",
    "Resolve blockers before real buy review.": "실제 매수 검토 전 막힌 항목을 해결하세요.",
    "Use dashboard for final human review. Broker order remains manual only.": "대시보드에서 최종 검토하세요. 실제 주문은 증권앱에서만 직접 실행합니다.",
    "DONE: 끝. Review dashboard is ready; broker order still requires manual action.": "끝. 대시보드 검토 준비가 끝났고, 실제 주문은 직접 실행해야 합니다.",
    "refresh market data with explicit approval": "승인 후 가격 데이터를 새로 갱신하세요",
    "review company_research and today dashboard": "기업 리서치와 오늘 화면을 확인하세요",
    "add more core companies": "우량 기업 비교군을 더 추가하세요",
    "valuation review required": "밸류에이션 확인이 필요합니다",
    "weak trend": "추세가 약합니다",
    "exclude until trend recovers": "추세가 회복될 때까지 제외",
    "Add only if CORE_FOCUS persists": "핵심 후보 상태가 유지될 때만 추가 매수",
    "If SMA20 breaks and average cost drawdown reaches -7%, reduce 50%": "20일선 이탈과 평균단가 대비 -7% 손실이 함께 나오면 절반 축소",
    "If conviction_score < 60, stop new buys": "확신 점수가 60 미만이면 신규 매수 중단",
    "SMA20 break": "20일선 이탈",
    "first tranche 30%": "첫 매수는 계획 수량의 30%",
    "capital plan needs final confirmation": "자본 계획 최종 확인 필요",
    "rules fixed before amount": "금액보다 규칙을 먼저 확정",
    "USER_CONFIRMATION_REQUIRED": "사용자 확인 필요",
    "conviction_score": "확신 점수",
    "upside_probability": "상승 확률",
    "TODAY_FOCUS": "오늘 핵심 후보",
    "SMA20": "20일선",
    "ALPHA_BUY_READY": "상승 후보",
    "TREND_OK": "추세 양호",
    "ALPHA_WAIT": "대기",
    "ABOVE_SMA20": "20일선 위",
}

COMPANY_NAME_KO = {
    "Samsung Electronics": "삼성전자",
    "Hyundai Motor": "현대차",
    "SK hynix": "SK하이닉스",
    "Samsung C&T": "삼성물산",
    "LG Corp": "LG",
    "Hyundai Mobis": "현대모비스",
}


@dataclass(frozen=True)
class DashboardOutput:
    html_path: Path
    summary: dict[str, str | int | float]


def run_dashboard(reports_dir: Path | str, output_dir: Path | str | None = None) -> DashboardOutput:
    reports_root = Path(reports_dir).resolve()
    output_root = Path(output_dir).resolve() if output_dir else reports_root / "dashboard"
    output_root.mkdir(parents=True, exist_ok=True)

    profit = _load_csv(reports_root / "profit_focus" / "profit_focus.csv", PROFIT_COLUMNS, "profit focus")
    memo = _load_csv(reports_root / "investment_memo" / "investment_memo.csv", MEMO_COLUMNS, "investment memo")
    gate = _load_csv(reports_root / "decision_gate" / "decision_gate.csv", GATE_COLUMNS, "decision gate")

    top = _top_focus(profit)
    top_symbol = str(top.get("symbol", ""))
    memo_row = _row_for_symbol(memo, top_symbol)
    gate_row = _row_for_symbol(gate, top_symbol)
    filing_risk = _load_filing_risk_summary(reports_root, top_symbol)
    filing_risk_opinion = _filing_risk_opinion(filing_risk)
    pre_buy = _load_pre_buy_decision(reports_root, top_symbol)
    manual_draft = _load_manual_review_draft(reports_root, top_symbol)
    manual_proposal = _load_manual_review_proposal(reports_root, top_symbol)
    manual_apply = _load_manual_review_apply_plan(reports_root, top_symbol)
    universe = _load_universe_stock_analysis(reports_root)
    universe_coverage = _load_universe_coverage(reports_root)
    operating_status = _load_operating_status(reports_root)
    symbol_analysis = _load_symbol_analysis(reports_root)
    order_candidate = _load_order_candidate(reports_root, top_symbol)
    capital_scenarios = _load_capital_scenarios(reports_root, top_symbol)
    capital_plan = _load_capital_plan(reports_root, top_symbol)
    performance_tracking = _load_performance_tracking(reports_root)

    summary = {
        "top_symbol": top_symbol,
        "top_company": str(top.get("company_name", "")),
        "profit_focus_status": str(top.get("profit_focus_status", "")),
        "decision_gate_status": str(gate_row.get("decision_gate_status", "UNKNOWN")),
        "order_status": str(gate_row.get("order_status", memo_row.get("order_status", "NO_ORDER"))),
        "pre_buy_decision": str(pre_buy.get("decision_status", "NO_ORDER")),
        "filing_risk_opinion": filing_risk_opinion,
        "manual_review_draft": str(manual_draft.get("recommended_actual_action", "UNKNOWN")),
        "manual_review_proposal": str(manual_proposal.get("proposal_status", "UNKNOWN")),
        "manual_review_actual_written": str(manual_apply.get("actual_config_written", "UNKNOWN")),
        "order_candidate_status": str(order_candidate.get("order_status", "NO_ORDER")),
        "capital_plan_review": str(capital_plan.get("capital_plan_review", "UNKNOWN")),
        "universe_coverage_status": str(universe_coverage.get("universe_status", "UNKNOWN")),
        "universe_price_coverage_status": str(universe_coverage.get("price_coverage_status", "UNKNOWN")),
        "completion_status": str(operating_status.get("completion_status", "UNKNOWN")),
        "usage_status": str(operating_status.get("usage_status", "UNKNOWN")),
        "core_count": int((profit["profit_focus_status"] == "CORE_FOCUS").sum()),
        "wait_count": int((profit["profit_focus_status"] != "CORE_FOCUS").sum()),
        "universe_count": int(len(universe)),
        "universe_buy_ready_count": int((universe["decision_status"] == "BUY_READY").sum()) if not universe.empty else 0,
        "symbol_analysis_count": int(len(symbol_analysis)),
        "symbol_data_required_count": int((symbol_analysis["analysis_status"] == "DATA_REQUIRED").sum()) if not symbol_analysis.empty else 0,
    }

    html_path = output_root / "index.html"
    html_path.write_text(
        _render_html(
            profit,
            top,
            memo_row,
            gate_row,
            filing_risk,
            pre_buy,
            manual_draft,
            manual_proposal,
            manual_apply,
            universe,
            universe_coverage,
            operating_status,
            symbol_analysis,
            order_candidate,
            capital_scenarios,
            capital_plan,
            performance_tracking,
            summary,
        ),
        encoding="utf-8",
    )
    return DashboardOutput(html_path=html_path, summary=summary)


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame


def _top_focus(profit: pd.DataFrame) -> pd.Series:
    ordered = profit.copy()
    ordered["_rank"] = ordered["profit_focus_status"].map(
        {"CORE_FOCUS": 4, "WAIT_RISK": 3, "NEEDS_CHECKLIST": 2, "WATCH_ONLY": 1}
    ).fillna(0)
    ordered = ordered.sort_values(["_rank", "conviction_score"], ascending=[False, False])
    return ordered.iloc[0]


def _row_for_symbol(frame: pd.DataFrame, symbol: str) -> pd.Series:
    row = frame.loc[frame["symbol"] == symbol]
    if row.empty:
        return pd.Series(dtype=object)
    return row.iloc[0]


def _load_filing_risk_summary(reports_root: Path, symbol: str) -> pd.DataFrame:
    code = symbol.split(".")[0]
    path = reports_root / "filing_review" / f"filing_risk_summary_{code}.csv"
    if not path.exists():
        return pd.DataFrame(columns=sorted(FILING_RISK_COLUMNS))
    return _load_csv(path, FILING_RISK_COLUMNS, "filing risk summary")


def _filing_risk_opinion(filing_risk: pd.DataFrame) -> str:
    if filing_risk.empty:
        return "UNKNOWN"
    if (filing_risk["fatal_risk"].astype(str).str.upper() == "YES").any():
        return "EXCLUDE"
    if (filing_risk["gate_opinion"].astype(str) == "HOLD_REVIEW").any():
        return "HOLD_REVIEW"
    return "PASS_CANDIDATE_WITH_MONITORING"


def _load_pre_buy_decision(reports_root: Path, symbol: str) -> pd.Series:
    path = reports_root / "pre_buy_decision" / "pre_buy_decision.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, PRE_BUY_COLUMNS, "pre-buy decision")
    return _row_for_symbol(frame, symbol)


def _load_manual_review_draft(reports_root: Path, symbol: str) -> pd.Series:
    path = reports_root / "decision_gate" / "manual_review_draft.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, MANUAL_REVIEW_DRAFT_COLUMNS, "manual review draft")
    return _row_for_symbol(frame, symbol)


def _load_manual_review_proposal(reports_root: Path, symbol: str) -> pd.Series:
    path = reports_root / "decision_gate" / "manual_review_proposal.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, MANUAL_REVIEW_PROPOSAL_COLUMNS, "manual review proposal")
    return _row_for_symbol(frame, symbol)


def _load_manual_review_apply_plan(reports_root: Path, symbol: str) -> pd.Series:
    path = reports_root / "decision_gate" / "manual_review_apply_plan.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, MANUAL_REVIEW_APPLY_PLAN_COLUMNS, "manual review apply plan")
    return _row_for_symbol(frame, symbol)


def _load_universe_stock_analysis(reports_root: Path) -> pd.DataFrame:
    path = reports_root / "universe_stock_analysis" / "universe_stock_analysis.csv"
    if not path.exists():
        return pd.DataFrame(columns=sorted(UNIVERSE_STOCK_COLUMNS))
    return _load_csv(path, UNIVERSE_STOCK_COLUMNS, "universe stock analysis")


def _load_universe_coverage(reports_root: Path) -> pd.Series:
    path = reports_root / "universe_coverage" / "universe_coverage.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, UNIVERSE_COVERAGE_COLUMNS, "universe coverage")
    if frame.empty:
        return pd.Series(dtype=object)
    return frame.iloc[0]


def _load_operating_status(reports_root: Path) -> pd.Series:
    path = reports_root / "operating_status" / "operating_status.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, OPERATING_STATUS_COLUMNS, "operating status")
    if frame.empty:
        return pd.Series(dtype=object)
    return frame.iloc[0]


def _load_symbol_analysis(reports_root: Path) -> pd.DataFrame:
    directory = reports_root / "symbol_analysis"
    if not directory.exists():
        return pd.DataFrame(columns=sorted(SYMBOL_ANALYSIS_COLUMNS))
    frames: list[pd.DataFrame] = []
    for path in sorted(directory.glob("symbol_analysis*.csv")):
        frames.append(_load_csv(path, SYMBOL_ANALYSIS_COLUMNS, "symbol analysis"))
    if not frames:
        return pd.DataFrame(columns=sorted(SYMBOL_ANALYSIS_COLUMNS))
    return pd.concat(frames, ignore_index=True)


def _load_order_candidate(reports_root: Path, symbol: str) -> pd.Series:
    path = reports_root / "orders" / "order_candidates.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, ORDER_CANDIDATE_COLUMNS, "order candidates")
    return _row_for_symbol(frame, symbol)


def _load_capital_scenarios(reports_root: Path, symbol: str) -> pd.DataFrame:
    path = reports_root / "orders" / "capital_scenarios.csv"
    if not path.exists():
        return pd.DataFrame(columns=sorted(CAPITAL_SCENARIO_COLUMNS))
    frame = _load_csv(path, CAPITAL_SCENARIO_COLUMNS, "capital scenarios")
    return frame.loc[frame["symbol"] == symbol].copy()


def _load_capital_plan(reports_root: Path, symbol: str) -> pd.Series:
    code = symbol.split(".")[0]
    path = reports_root / "decision_gate" / f"capital_plan_review_{code}.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, CAPITAL_PLAN_COLUMNS, "capital plan review")
    return _row_for_symbol(frame, symbol)


def _load_performance_tracking(reports_root: Path) -> pd.DataFrame:
    path = reports_root / "performance_tracking" / "performance_tracking.csv"
    if not path.exists():
        return pd.DataFrame(columns=sorted(PERFORMANCE_TRACKING_COLUMNS))
    return _load_csv(path, PERFORMANCE_TRACKING_COLUMNS, "performance tracking")


def _render_html(
    profit: pd.DataFrame,
    top: pd.Series,
    memo: pd.Series,
    gate: pd.Series,
    filing_risk: pd.DataFrame,
    pre_buy: pd.Series,
    manual_draft: pd.Series,
    manual_proposal: pd.Series,
    manual_apply: pd.Series,
    universe: pd.DataFrame,
    universe_coverage: pd.Series,
    operating_status: pd.Series,
    symbol_analysis: pd.DataFrame,
    order_candidate: pd.Series,
    capital_scenarios: pd.DataFrame,
    capital_plan: pd.Series,
    performance_tracking: pd.DataFrame,
    summary: dict[str, str | int | float],
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    company = _company_name(_first_text(top.get("company_name"), operating_status.get("company_name"), "후보 없음"))
    symbol = _first_text(top.get("symbol"), operating_status.get("top_symbol"), "")
    display_name = f"{company} ({symbol})" if symbol else company
    decision = _first_text(pre_buy.get("decision_status"), operating_status.get("decision_status"), "NO_ORDER")
    order_status = _first_text(order_candidate.get("order_status"), operating_status.get("order_status"), "NO_ORDER")
    gate_status = _first_text(gate.get("decision_gate_status"), operating_status.get("decision_gate_status"), "UNKNOWN")
    blockers = _first_text(
        operating_status.get("blockers"),
        pre_buy.get("buy_ban_reasons"),
        gate.get("gate_reason"),
        "막힌 항목 없음",
    )

    lines = [
        "<!doctype html>",
        '<html lang="ko">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>퀀트 트레이너</title>",
        "<style>",
        _css(),
        "</style>",
        "</head>",
        "<body>",
        '<main class="page">',
        '<header class="topbar">',
        "<div>",
        "<h1>퀀트 트레이너</h1>",
        f"<p>업데이트 {escape(now)} · 실제 주문은 이 화면에서 실행되지 않습니다.</p>",
        "</div>",
        _pill(order_status),
        "</header>",
        '<section class="answer">',
        '<div class="answer-main">',
        '<span class="eyebrow">오늘 결론</span>',
        f"<h2>{escape(_decision_sentence(company, decision))}</h2>",
        f"<p>{escape(_main_action_sentence(decision, gate_status, blockers))}</p>",
        "</div>",
        '<aside class="safety-note">',
        "<strong>주문은 자동 실행되지 않습니다</strong>",
        "<span>이 화면은 판단서입니다. 주문 여부와 수량은 증권앱에서 직접 최종 확인해야 합니다.</span>",
        "</aside>",
        "</section>",
        '<section class="quick-grid">',
        _metric("1순위 후보", display_name, "focus"),
        _metric("판단", _ko_status(decision), _status_class(decision)),
        _metric("검토 수량", _order_size_text(order_candidate), "neutral"),
        _metric("비교 종목", f"{int(summary['universe_count'])}개", "neutral"),
        "</section>",
        '<section class="two-column">',
        '<article class="panel">',
        "<h2>지금 할 일</h2>",
        _action_list(decision, order_status, gate_status, order_candidate),
        "</article>",
        '<article class="panel">',
        "<h2>1순위 후보</h2>",
        _candidate_snapshot(top, pre_buy, order_candidate),
        "</article>",
        "</section>",
        '<section class="two-column">',
        '<article class="panel">',
        "<h2>왜 후보인가</h2>",
        _why_candidate(top, memo, pre_buy),
        "</article>",
        '<article class="panel">',
        "<h2>매수 금지 이유</h2>",
        _why_not_buy(top, pre_buy, operating_status, gate),
        "</article>",
        "</section>",
        '<section class="two-column">',
        '<article class="panel">',
        "<h2>손실 방어 규칙</h2>",
        _capital_plan(capital_plan, pre_buy, gate),
        "</article>",
        '<article class="panel">',
        "<h2>수동 확인 6개 항목</h2>",
        _manual_review(gate, manual_draft, manual_proposal, manual_apply),
        "</article>",
        "</section>",
        '<section class="panel">',
        "<h2>공시 리스크 요약</h2>",
        _filing_risk_summary(filing_risk, str(summary["filing_risk_opinion"])),
        "</section>",
        '<section class="panel">',
        "<h2>자본 계획</h2>",
        _capital_scenarios(capital_scenarios, capital_plan),
        "</section>",
        '<section class="panel">',
        "<h2>투자 후 성과 추적</h2>",
        _performance_tracking(performance_tracking),
        "</section>",
        '<section class="panel">',
        "<h2>다른 후보와 비교</h2>",
        _universe_stock_analysis(universe),
        "</section>",
        '<section class="panel">',
        "<h2>내가 넣은 종목 분석 상태</h2>",
        _symbol_analysis(symbol_analysis),
        "</section>",
        '<section class="panel">',
        "<h2>프로그램 상태</h2>",
        _operating_status(operating_status, universe_coverage),
        "</section>",
        '<section class="panel details-panel">',
        "<h2>상세 자료</h2>",
        "<p>처음에는 위 결론만 보면 됩니다. 원본 근거가 필요할 때만 아래 파일을 여세요.</p>",
        _report_links(),
        "</section>",
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(lines)


def _css() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #172026;
  --muted: #64727a;
  --line: #d7dee2;
  --paper: #f5f7f8;
  --panel: #ffffff;
  --soft: #eef5f4;
  --blue: #176b87;
  --green: #16794c;
  --amber: #b45309;
  --red: #b42318;
  --violet: #665191;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 15px/1.6 "Segoe UI", "Malgun Gothic", Arial, sans-serif;
}
.page { width: min(1120px, calc(100% - 28px)); margin: 20px auto 42px; }
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 8px 0 16px;
}
h1, h2, h3, p { margin-top: 0; }
h1 { margin-bottom: 4px; font-size: 30px; line-height: 1.15; letter-spacing: 0; }
h2 { margin-bottom: 12px; font-size: 19px; letter-spacing: 0; }
h3 { margin-bottom: 8px; font-size: 22px; letter-spacing: 0; }
p { margin-bottom: 10px; }
.topbar p, .muted { color: var(--muted); }
.answer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 14px;
  margin-bottom: 14px;
}
.answer-main, .safety-note, .panel, .metric {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.answer-main {
  padding: 22px;
  border-left: 6px solid var(--blue);
}
.answer-main h2 { margin-bottom: 8px; font-size: 28px; line-height: 1.24; }
.eyebrow {
  display: block;
  margin-bottom: 8px;
  color: var(--blue);
  font-size: 13px;
  font-weight: 800;
}
.safety-note {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  padding: 18px;
  background: var(--soft);
}
.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.two-column {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.panel { margin-bottom: 12px; padding: 18px; }
.metric { padding: 15px; min-height: 92px; }
.metric .label, th { color: var(--muted); font-size: 12px; font-weight: 700; }
.metric .value { margin-top: 6px; font-size: 21px; font-weight: 800; overflow-wrap: anywhere; }
.focus { border-left: 5px solid var(--blue); }
.ready { border-left: 5px solid var(--green); }
.waiting, .warn { border-left: 5px solid var(--amber); }
.blocked { border-left: 5px solid var(--red); }
.neutral { border-left: 5px solid var(--violet); }
.status {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  max-width: 100%;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 10px;
  background: #fff;
  font-size: 12px;
  font-weight: 800;
  overflow-wrap: anywhere;
}
.status.ready { color: var(--green); border-color: var(--green); }
.status.waiting, .status.warn { color: var(--amber); border-color: var(--amber); }
.status.blocked { color: var(--red); border-color: var(--red); }
.small-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 0;
}
.mini {
  min-height: 68px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  background: #fbfcfd;
}
.mini span { display: block; color: var(--muted); font-size: 12px; }
.mini strong { display: block; margin-top: 4px; font-size: 16px; overflow-wrap: anywhere; }
.action-list { margin: 0; padding-left: 20px; }
.action-list li { margin-bottom: 8px; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
th, td {
  text-align: left;
  border-top: 1px solid var(--line);
  padding: 10px 8px;
  vertical-align: top;
  overflow-wrap: anywhere;
}
.links { display: flex; flex-wrap: wrap; gap: 9px; }
.links a {
  color: var(--blue);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px 10px;
  background: #fff;
  text-decoration: none;
}
@media (max-width: 860px) {
  .answer, .quick-grid, .two-column, .small-grid { grid-template-columns: 1fr; }
  .topbar { align-items: flex-start; flex-direction: column; }
  .answer-main h2 { font-size: 24px; }
}
"""


def _metric(label: str, value: str, style: str) -> str:
    return (
        f'<article class="metric {escape(style)}">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        "</article>"
    )


def _mini(label: str, value: str) -> str:
    return f'<div class="mini"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'


def _pill(value: object) -> str:
    raw = _first_text(value, "UNKNOWN")
    return f'<span class="status {_status_class(raw)}">{escape(_ko_status(raw))}</span>'


def _decision_sentence(company: str, decision: object) -> str:
    label = _ko_status(decision)
    if str(decision).upper() == "BUY_READY":
        return f"{company}은 매수 검토 가능 상태입니다"
    if str(decision).upper() == "WAIT":
        return f"{company}은 아직 기다림입니다"
    if str(decision).upper() == "REJECT":
        return f"{company}은 오늘 제외입니다"
    return f"현재 판단은 {label}입니다"


def _main_action_sentence(decision: object, gate_status: object, blockers: object) -> str:
    raw = str(decision).upper()
    if raw == "BUY_READY":
        return "분할 매수안과 손실 방어 규칙을 확인한 뒤, 증권앱에서 직접 주문 여부를 결정하세요."
    if raw == "WAIT":
        return f"아직 주문 단계가 아닙니다. {_friendly_text(blockers)}"
    if raw == "REJECT":
        return "오늘은 매수 후보에서 제외하고 다음 후보를 보세요."
    return f"{_ko_status(gate_status)} 상태입니다. 막힌 항목을 먼저 확인하세요."


def _order_size_text(order_candidate: pd.Series) -> str:
    if order_candidate.empty:
        return "수량 없음"
    shares = int(_number(order_candidate.get("candidate_shares")))
    value = _money(order_candidate.get("estimated_order_value"))
    return f"{shares}주 / {value}"


def _candidate_snapshot(top: pd.Series, pre_buy: pd.Series, order_candidate: pd.Series) -> str:
    latest_price = _money(_first_text(order_candidate.get("latest_price"), top.get("latest_price"), ""))
    entry = _entry_range(pre_buy)
    rows = [
        '<div class="small-grid">',
        _mini("확신 점수", f"{_number(top.get('conviction_score')):.1f}점"),
        _mini("20일 기대", _pct(top.get("expected_20d_return"))),
        _mini("상승 확률", _pct(top.get("upside_probability"))),
        _mini("현재가", latest_price),
        _mini("진입 가격", entry),
        _mini("주문 방식", _ko_status(order_candidate.get("execution_mode", "MANUAL_REVIEW_ONLY"))),
        "</div>",
    ]
    return "\n".join(rows)


def _action_list(decision: object, order_status: object, gate_status: object, order_candidate: pd.Series) -> str:
    raw = str(decision).upper()
    steps: list[str]
    if raw == "BUY_READY":
        steps = [
            f"검토 수량은 {_order_size_text(order_candidate)}입니다.",
            "진입 가격대와 손절 조건을 다시 확인합니다.",
            "실제 주문은 증권앱에서 직접 실행합니다.",
        ]
    elif raw == "WAIT":
        steps = [
            f"{_ko_status(gate_status)} 상태를 먼저 해결합니다.",
            "가격, 공시, 실적, 손실 방어 규칙이 모두 통과될 때까지 기다립니다.",
            "오늘은 자동 주문도, 자동 매수도 하지 않습니다.",
        ]
    elif raw == "REJECT":
        steps = [
            "이 후보는 오늘 매수하지 않습니다.",
            "다른 후보와 비교 표에서 다음 종목을 확인합니다.",
        ]
    else:
        steps = [
            "판단 상태를 먼저 확인합니다.",
            "UNKNOWN이 남아 있으면 해당 항목의 근거를 채웁니다.",
        ]
    if str(order_status).upper() != "NO_ORDER":
        steps.append(f"주문 후보 상태는 {_ko_status(order_status)}이며, 그래도 자동 주문은 실행되지 않습니다.")
    return "<ol class=\"action-list\">" + "".join(f"<li>{escape(step)}</li>" for step in steps) + "</ol>"


def _why_candidate(top: pd.Series, memo: pd.Series, pre_buy: pd.Series) -> str:
    lines = [
        _paragraph("핵심 thesis", memo.get("core_thesis")),
        _paragraph("정량 근거", top.get("why_profit_candidate")),
        _paragraph("매수 이유", pre_buy.get("buy_reasons")),
        _paragraph("다음 확인", top.get("next_step")),
    ]
    return "\n".join(line for line in lines if line)


def _why_not_buy(top: pd.Series, pre_buy: pd.Series, operating_status: pd.Series, gate: pd.Series) -> str:
    reasons = [
        _paragraph("막힌 항목", operating_status.get("blockers")),
        _paragraph("매수 금지 이유", pre_buy.get("buy_ban_reasons")),
        _paragraph("아직 기다리는 이유", top.get("why_not_now")),
        _paragraph("게이트 사유", gate.get("gate_reason")),
    ]
    rendered = [reason for reason in reasons if reason]
    if not rendered:
        return '<p class="muted">현재 표시할 매수 금지 이유가 없습니다.</p>'
    return "\n".join(rendered)


def _capital_plan(capital_plan: pd.Series, pre_buy: pd.Series, gate: pd.Series) -> str:
    if capital_plan.empty:
        fallback = _first_text(pre_buy.get("stop_loss_rule"), gate.get("loss_defense"), "손실 방어 규칙 없음")
        return f"<p>{escape(_friendly_text(fallback))}</p>"
    rows = [
        '<div class="small-grid">',
        _mini("한 종목 최대 비중", _pct(capital_plan.get("max_position_weight"))),
        _mini("현금 버퍼", _pct(capital_plan.get("cash_buffer_weight"))),
        _mini("첫 매수", _pct(capital_plan.get("first_tranche_pct"))),
        "</div>",
        _paragraph("추가 매수", capital_plan.get("add_condition")),
        _paragraph("비중 축소", capital_plan.get("reduce_condition")),
        _paragraph("신규 매수 중단", capital_plan.get("stop_condition")),
        _paragraph("즉시 중단", capital_plan.get("immediate_halt_condition")),
    ]
    return "\n".join(row for row in rows if row)


def _manual_review(
    gate: pd.Series,
    manual_draft: pd.Series,
    manual_proposal: pd.Series,
    manual_apply: pd.Series,
) -> str:
    source = gate if not gate.empty else manual_draft
    labels = {
        "filing_review": "공시",
        "earnings_review": "실적",
        "business_driver_review": "사업 동력",
        "valuation_review": "밸류에이션",
        "loss_rule_review": "손실 규칙",
        "capital_plan_review": "자본 계획",
    }
    rows = ['<div class="small-grid">']
    for column, label in labels.items():
        rows.append(_mini(label, _ko_status(source.get(column, "UNKNOWN"))))
    rows.append("</div>")
    if not manual_proposal.empty:
        rows.append(_paragraph("제안 상태", manual_proposal.get("proposal_status")))
    if not manual_apply.empty:
        rows.append(_paragraph("실제 반영", _actual_config_written_text(manual_apply.get("actual_config_written", "NO"))))
    return "\n".join(rows)


def _filing_risk_summary(filing_risk: pd.DataFrame, opinion: str) -> str:
    if filing_risk.empty:
        return '<p class="muted">공시 리스크 요약 파일이 없습니다. OpenDART 리스크 요약을 먼저 생성하세요.</p>'
    fatal_count = int((filing_risk["fatal_risk"].astype(str).str.upper() == "YES").sum())
    rows = [
        f"<p><strong>치명적 리스크 {fatal_count}개</strong> · 판단: {_pill(opinion)}</p>",
        "<table>",
        "<thead><tr><th>위험</th><th>근거 수</th><th>판단</th><th>관리 기준</th></tr></thead>",
        "<tbody>",
    ]
    for row in filing_risk.head(5).itertuples(index=False):
        rows.append(
            "<tr>"
            f"<td>{escape(_friendly_text(row.risk_title))}</td>"
            f"<td>{int(_number(row.evidence_count))}</td>"
            f"<td>{escape(_ko_status(row.gate_opinion))}</td>"
            f"<td>{escape(_friendly_text(row.monitoring_rule))}</td>"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def _capital_scenarios(capital_scenarios: pd.DataFrame, capital_plan: pd.Series) -> str:
    if capital_scenarios.empty:
        return '<p class="muted">자본 시나리오가 없습니다.</p>'
    rows = [
        "<table>",
        "<thead><tr><th>투자금</th><th>목표 금액</th><th>목표 수량</th><th>첫 매수 수량</th><th>상태</th></tr></thead>",
        "<tbody>",
    ]
    for row in capital_scenarios.itertuples(index=False):
        rows.append(
            "<tr>"
            f"<td>{_money(row.scenario_capital)}</td>"
            f"<td>{_money(row.target_position_value)}</td>"
            f"<td>{int(_number(row.target_position_shares))}주</td>"
            f"<td>{int(_number(row.first_tranche_shares))}주</td>"
            f"<td>{escape(_ko_status(row.scenario_status))}</td>"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    if not capital_plan.empty:
        rows.append(_paragraph("메모", capital_plan.get("review_notes")))
    return "\n".join(row for row in rows if row)


def _performance_tracking(performance_tracking: pd.DataFrame) -> str:
    if performance_tracking.empty:
        return '<p class="muted">아직 투자 후 성과 추적 리포트가 없습니다.</p>'
    rows = [
        "<p>실제 매수 후에는 매수 당시 thesis, 손익, 1주/1개월/분기 점검을 여기에 기록합니다.</p>",
        "<table>",
        "<thead><tr><th>종목</th><th>상태</th><th>손익</th><th>수익률</th><th>점검</th><th>다음 할 일</th></tr></thead>",
        "<tbody>",
    ]
    for row in performance_tracking.head(8).itertuples(index=False):
        symbol = str(row.symbol).strip() or "-"
        company = _company_name(row.company_name) if str(row.company_name).strip() else "매수 기록 없음"
        rows.append(
            "<tr>"
            f"<td>{escape(company)}<br><span class=\"muted\">{escape(symbol)}</span></td>"
            f"<td>{escape(_ko_status(row.tracking_status))}</td>"
            f"<td>{_money(row.unrealized_pnl)}</td>"
            f"<td>{_pct(row.unrealized_return)}</td>"
            f"<td>{escape(_ko_status(row.review_action))}</td>"
            f"<td>{escape(_friendly_text(row.next_step))}</td>"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def _universe_stock_analysis(universe: pd.DataFrame) -> str:
    if universe.empty:
        return '<p class="muted">비교 후보 분석 파일이 없습니다. 후보군을 먼저 생성하세요.</p>'
    ordered = universe.copy()
    ordered["_rank"] = ordered["decision_status"].map({"BUY_READY": 4, "WAIT": 3, "REJECT": 1}).fillna(0)
    ordered = ordered.sort_values(["_rank", "research_score"], ascending=[False, False]).head(12)
    rows = [
        f"<p>삼성물산 하나만 보지 않고, 현재 {len(universe)}개 기업을 같은 기준으로 비교합니다.</p>",
        "<table>",
        "<thead><tr><th>종목</th><th>판단</th><th>점수</th><th>현재가</th><th>해야 할 일</th></tr></thead>",
        "<tbody>",
    ]
    for row in ordered.itertuples(index=False):
        rows.append(
            "<tr>"
            f"<td>{escape(_company_name(row.company_name))}<br><span class=\"muted\">{escape(str(row.symbol))}</span></td>"
            f"<td>{escape(_ko_status(row.decision_status))}</td>"
            f"<td>{_number(row.research_score):.1f}</td>"
            f"<td>{_money(row.latest_price)}</td>"
            f"<td>{escape(_friendly_text(row.action_summary))}</td>"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def _symbol_analysis(symbol_analysis: pd.DataFrame) -> str:
    if symbol_analysis.empty:
        return '<p class="muted">사용자가 추가한 종목 분석 상태가 없습니다.</p>'
    rows = [
        "<p>새 기업을 넣으면 가격 데이터가 충분한지, 바로 분석 가능한지 여기에서 확인합니다.</p>",
        "<table>",
        "<thead><tr><th>종목</th><th>분석 상태</th><th>가격 데이터</th><th>판단</th><th>막힌 이유</th></tr></thead>",
        "<tbody>",
    ]
    for row in symbol_analysis.head(12).itertuples(index=False):
        rows.append(
            "<tr>"
            f"<td>{escape(_company_name(row.company_name))}<br><span class=\"muted\">{escape(str(row.symbol))}</span></td>"
            f"<td>{escape(_ko_status(row.analysis_status))}</td>"
            f"<td>{escape(_ko_status(row.price_data_status))}</td>"
            f"<td>{escape(_ko_status(row.decision))}</td>"
            f"<td>{escape(_friendly_text(row.blocking_reason))}</td>"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def _operating_status(status: pd.Series, coverage: pd.Series) -> str:
    if status.empty:
        return '<p class="muted">운영 상태 파일이 없습니다.</p>'
    rows = [
        '<div class="small-grid">',
        _mini("완료 상태", _ko_status(status.get("completion_status", "UNKNOWN"))),
        _mini("사용 상태", _ko_status(status.get("usage_status", "UNKNOWN"))),
        _mini("주문 상태", _ko_status(status.get("order_status", "NO_ORDER"))),
        _mini("수동 검토", _ko_status(status.get("manual_actual_written", "UNKNOWN"))),
        _mini("투자금", _ko_status(status.get("capital_status", "UNKNOWN"))),
        _mini("가격 데이터", _ko_status(status.get("price_coverage_status", "UNKNOWN"))),
        "</div>",
        _paragraph("다음 단계", status.get("next_step")),
    ]
    if not coverage.empty:
        rows.append(_paragraph("비교군 상태", coverage.get("universe_status")))
        rows.append(_paragraph("부족한 필수 종목", coverage.get("required_missing_symbols")))
    return "\n".join(row for row in rows if row)


def _report_links() -> str:
    links = [
        ("오늘 핵심 후보", "../profit_focus/today_focus.md"),
        ("투자 메모", "../investment_memo/investment_memo.md"),
        ("결정 게이트", "../decision_gate/decision_gate.md"),
        ("공시 리스크", "../filing_review/"),
        ("매수 준비 판단서", "../pre_buy_decision/pre_buy_decision.md"),
        ("주문 후보", "../orders/order_candidates.md"),
        ("자본 시나리오", "../orders/capital_scenarios.md"),
        ("비교 후보", "../universe_stock_analysis/universe_stock_analysis.md"),
        ("개별 종목 분석", "../symbol_analysis/"),
    ]
    return '<div class="links">' + "".join(
        f'<a href="{escape(href)}">{escape(label)}</a>' for label, href in links
    ) + "</div>"


def _paragraph(label: str, value: object) -> str:
    text = _friendly_text(value)
    if not text or text == "없음":
        return ""
    return f"<p><strong>{escape(label)}:</strong> {escape(text)}</p>"


def _entry_range(pre_buy: pd.Series) -> str:
    if pre_buy.empty:
        return "-"
    low = _number(pre_buy.get("entry_price_low"))
    high = _number(pre_buy.get("entry_price_high"))
    if not low and not high:
        return "-"
    return f"{int(low):,}원 - {int(high):,}원"


def _first_text(*values: object) -> str:
    for value in values:
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


def _company_name(value: object) -> str:
    text = _first_text(value)
    return COMPANY_NAME_KO.get(text, text)


def _actual_config_written_text(value: object) -> str:
    if str(value).strip().upper() == "YES":
        return "최종 수동 검토값이 반영됐습니다"
    return "최종 수동 검토값이 아직 반영되지 않았습니다"


def _friendly_text(value: object) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return "없음"
    for raw, korean in sorted(TEXT_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(raw, korean)
    for raw, korean in sorted(STATUS_KO.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(raw, korean)
    return text.replace(";", " · ").replace(",", ", ")


def _ko_status(value: object) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return "확인 필요"
    upper = text.upper()
    if upper in STATUS_KO:
        return STATUS_KO[upper]
    return _friendly_text(text)


def _status_class(value: object) -> str:
    text = str(value).upper()
    if "BUY_READY" in text or "READY" in text or "PASS" in text or "DONE" in text:
        return "ready"
    if "REJECT" in text or "BLOCK" in text or "FAIL" in text or "EXCLUDE" in text:
        return "blocked"
    if "WAIT" in text or "UNKNOWN" in text or "REQUIRED" in text or "NO_ORDER" in text:
        return "waiting"
    return "neutral"


def _money(value: object) -> str:
    amount = _number(value)
    if amount <= 0:
        return "0원"
    return f"{int(round(amount)):,}원"


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _pct(value: object) -> str:
    return f"{_number(value) * 100:.1f}%"
