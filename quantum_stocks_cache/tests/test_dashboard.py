from __future__ import annotations

import importlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def test_dashboard_renders_easy_korean_quant_trainer_view() -> None:
    module = importlib.import_module("quantum_trainer.dashboard")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        reports = root / "reports"
        profit_dir = reports / "profit_focus"
        memo_dir = reports / "investment_memo"
        gate_dir = reports / "decision_gate"
        filing_dir = reports / "filing_review"
        pre_buy_dir = reports / "pre_buy_decision"
        universe_dir = reports / "universe_stock_analysis"
        universe_coverage_dir = reports / "universe_coverage"
        operating_status_dir = reports / "operating_status"
        symbol_dir = reports / "symbol_analysis"
        orders_dir = reports / "orders"
        tracking_dir = reports / "performance_tracking"
        capital_plan_dir = reports / "decision_gate"
        for directory in [
            profit_dir,
            memo_dir,
            gate_dir,
            filing_dir,
            pre_buy_dir,
            universe_dir,
            universe_coverage_dir,
            operating_status_dir,
            symbol_dir,
            orders_dir,
            tracking_dir,
            capital_plan_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "sector": "지주/건설",
                    "profit_focus_status": "CORE_FOCUS",
                    "conviction_score": 77.01,
                    "expected_20d_return": 0.158,
                    "upside_probability": 0.99,
                    "ma20_gap": 0.097,
                    "return_20d": 0.361,
                    "per": 18.45,
                    "pbr": 1.25,
                    "why_profit_candidate": "conviction_score=77.01; upside_probability=99.0%",
                    "why_not_now": "manual gate not ready",
                    "invalidation_rule": "TODAY_FOCUS 이탈, SMA20 하회",
                    "next_step": "사업/공시 수동 확인",
                },
                {
                    "symbol": "005930.KS",
                    "company_name": "삼성전자",
                    "sector": "반도체",
                    "profit_focus_status": "WAIT_RISK",
                    "conviction_score": 62.16,
                    "expected_20d_return": 0.198,
                    "upside_probability": 0.86,
                    "ma20_gap": 0.187,
                    "return_20d": 0.458,
                    "per": 41.9,
                    "pbr": 4.34,
                    "why_profit_candidate": "conviction_score=62.16",
                    "why_not_now": "valuation review required",
                    "invalidation_rule": "TODAY_FOCUS 이탈",
                    "next_step": "관찰",
                },
            ]
        ).to_csv(profit_dir / "profit_focus.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "memo_status": "THESIS_REVIEW",
                    "order_status": "NO_ORDER",
                    "core_thesis": "지주 가치와 실적 개선을 함께 보는 후보",
                    "evidence": "conviction_score=77.01",
                    "risks": "건설 프로젝트와 바이오 지분 변동 확인 필요",
                    "manual_checks": "최근 공시 확인; 손실 방어 조건 확인",
                    "loss_defense": "TODAY_FOCUS 이탈 시 신규 매수 중단",
                    "next_action": "수동 확인",
                }
            ]
        ).to_csv(memo_dir / "investment_memo.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "decision_gate_status": "WAITING_MANUAL_EVIDENCE",
                    "order_status": "NO_ORDER",
                    "gate_reason": "manual review required",
                    "filing_review": "UNKNOWN",
                    "earnings_review": "UNKNOWN",
                    "business_driver_review": "UNKNOWN",
                    "valuation_review": "UNKNOWN",
                    "loss_rule_review": "UNKNOWN",
                    "capital_plan_review": "UNKNOWN",
                    "loss_defense": "TODAY_FOCUS 이탈",
                }
            ]
        ).to_csv(gate_dir / "decision_gate.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "risk_id": "legal_litigation_exposure",
                    "risk_title": "소송 노출",
                    "source_checks": "litigation_review",
                    "evidence_count": 8,
                    "key_evidence": "소송 금액이 재무제표에 중요한 영향을 줄지 확인",
                    "fatal_risk": "NO",
                    "gate_opinion": "PASS_CANDIDATE_WITH_MONITORING",
                    "monitoring_rule": "충당부채와 경영진 평가 변화 확인",
                }
            ]
        ).to_csv(filing_dir / "filing_risk_summary_028260.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "005930.KS",
                    "risk_id": "semiconductor_cycle_risk",
                    "risk_title": "Semiconductor filing risk",
                    "source_checks": "business_driver_review",
                    "evidence_count": 2,
                    "key_evidence": "반도체 업황 변동 확인",
                    "fatal_risk": "NO",
                    "gate_opinion": "HOLD_REVIEW",
                    "monitoring_rule": "업황과 밸류에이션 확인",
                }
            ]
        ).to_csv(filing_dir / "filing_risk_summary_005930.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "decision_status": "WAIT",
                    "order_status": "NO_ORDER",
                    "buy_reasons": "conviction_score=77.01",
                    "buy_ban_reasons": "manual gate not ready",
                    "entry_price_low": 386000,
                    "entry_price_high": 410500,
                    "staged_buy_plan": "first tranche 30%",
                    "stop_loss_rule": "SMA20 break",
                    "next_review_date": "2026-05-29",
                }
            ]
        ).to_csv(pre_buy_dir / "pre_buy_decision.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "filing_review": "PASS_CANDIDATE",
                    "earnings_review": "PASS_CANDIDATE",
                    "business_driver_review": "PASS_CANDIDATE",
                    "valuation_review": "PASS_CANDIDATE",
                    "loss_rule_review": "PASS_CANDIDATE",
                    "capital_plan_review": "UNKNOWN",
                    "recommended_actual_action": "DO_NOT_COPY_AUTOMATICALLY",
                    "review_notes": "capital plan needs final confirmation",
                }
            ]
        ).to_csv(gate_dir / "manual_review_draft.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "filing_review": "PASS",
                    "earnings_review": "PASS",
                    "business_driver_review": "PASS",
                    "valuation_review": "PASS",
                    "loss_rule_review": "PASS",
                    "capital_plan_review": "PASS",
                    "review_notes": "USER_CONFIRMATION_REQUIRED",
                    "proposal_status": "READY_FOR_USER_CONFIRMATION",
                    "approval_required": "YES",
                    "apply_target": "configs/manual_review.actual.csv",
                    "source_action": "DO_NOT_COPY_AUTOMATICALLY",
                }
            ]
        ).to_csv(gate_dir / "manual_review_proposal.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "apply_mode": "DRY_RUN",
                    "ready_to_apply": "YES",
                    "confirm_required": "YES",
                    "actual_config_written": "NO",
                    "actual_output_csv": "configs/manual_review.actual.csv",
                    "blocker": "waiting for explicit user confirmation",
                    "candidate_source": "manual_review_proposal.csv",
                }
            ]
        ).to_csv(gate_dir / "manual_review_apply_plan.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "sector": "지주/건설",
                    "decision_status": "WAIT",
                    "order_status": "NO_ORDER",
                    "price_trend_status": "TREND_OK",
                    "alpha_status": "ALPHA_BUY_READY",
                    "valuation_status": "VALUATION_NEUTRAL",
                    "risk_status": "RISK_OK",
                    "latest_price": 410500,
                    "research_score": 77.01,
                    "expected_20d_return": 0.158,
                    "upside_probability": 0.99,
                    "reason_summary": "ALPHA_BUY_READY; TREND_OK",
                    "action_summary": "manual gate required",
                },
                {
                    "symbol": "999999.KS",
                    "company_name": "사용자 추가 기업",
                    "sector": "사용자 관심종목",
                    "decision_status": "REJECT",
                    "order_status": "NO_ORDER",
                    "price_trend_status": "TREND_WEAK",
                    "alpha_status": "ALPHA_AVOID",
                    "valuation_status": "VALUATION_UNKNOWN",
                    "risk_status": "RISK_REVIEW",
                    "latest_price": 12345,
                    "research_score": 19.0,
                    "expected_20d_return": -0.04,
                    "upside_probability": 0.41,
                    "reason_summary": "weak trend",
                    "action_summary": "exclude until trend recovers",
                },
            ]
        ).to_csv(universe_dir / "universe_stock_analysis.csv", index=False)
        pd.DataFrame(
            [
                {
                    "universe_status": "EXPAND_UNIVERSE",
                    "universe_count": 2,
                    "min_count": 20,
                    "max_count": 50,
                    "count_status": "TOO_SMALL",
                    "sector_count": 2,
                    "required_symbol_count": 6,
                    "required_missing_count": 2,
                    "required_missing_symbols": "005930.KS;000660.KS",
                    "price_coverage_status": "PRICE_DATA_REQUIRED",
                    "price_missing_count": 1,
                    "price_missing_symbols": "000660.KS",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "next_step": "add more core companies",
                }
            ]
        ).to_csv(universe_coverage_dir / "universe_coverage.csv", index=False)
        pd.DataFrame(
            [
                {
                    "completion_status": "NOT_DONE",
                    "usage_status": "READY_FOR_REVIEW_USE",
                    "done_message": "DONE: 끝. Review dashboard is ready; broker order still requires manual action.",
                    "top_symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "decision_status": "WAIT",
                    "decision_gate_status": "WAITING_MANUAL_EVIDENCE",
                    "manual_actual_written": "NO",
                    "capital_status": "CAPITAL_AMOUNT_REQUIRED",
                    "universe_status": "EXPAND_UNIVERSE",
                    "price_coverage_status": "PRICE_DATA_REQUIRED",
                    "order_candidate_status": "BLOCKED_CAPITAL_REQUIRED",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "broker_order_requested": "NO",
                    "blockers": "decision gate waiting manual evidence; capital amount required",
                    "next_step": "Use dashboard for final human review. Broker order remains manual only.",
                    "dashboard_path": "reports/dashboard/index.html",
                }
            ]
        ).to_csv(operating_status_dir / "operating_status.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "006800.KS",
                    "company_name": "미래에셋증권",
                    "sector": "증권",
                    "market": "KOSPI",
                    "code": "006800",
                    "universe_action": "ADDED",
                    "analysis_status": "ANALYSIS_READY",
                    "local_pipeline_ready": "YES",
                    "price_data_status": "READY",
                    "price_rows": 120,
                    "min_samples_required": 80,
                    "blocking_reason": "",
                    "company_research_rank": 4,
                    "latest_price": 8200,
                    "latest_price_date": "2026-05-28",
                    "research_score": 64.5,
                    "research_view": "WATCHLIST",
                    "decision": "WAIT",
                    "why_summary": "ALPHA_WAIT,ABOVE_SMA20",
                    "company_research_csv": "reports/company_research/company_research.csv",
                    "company_research_md": "reports/company_research/company_research.md",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "broker_order_requested": "NO",
                    "next_step": "review company_research and today dashboard",
                },
                {
                    "symbol": "091990.KQ",
                    "company_name": "사용자 바이오",
                    "sector": "바이오",
                    "market": "KOSDAQ",
                    "code": "091990",
                    "universe_action": "ADDED",
                    "analysis_status": "DATA_REQUIRED",
                    "local_pipeline_ready": "NO",
                    "price_data_status": "MISSING",
                    "price_rows": 0,
                    "min_samples_required": 80,
                    "blocking_reason": "missing cached price history",
                    "company_research_rank": "",
                    "latest_price": "",
                    "latest_price_date": "",
                    "research_score": "",
                    "research_view": "",
                    "decision": "",
                    "why_summary": "",
                    "company_research_csv": "",
                    "company_research_md": "",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "broker_order_requested": "NO",
                    "next_step": "refresh market data with explicit approval",
                },
            ]
        ).to_csv(symbol_dir / "symbol_analysis_added.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "order_status": "BLOCKED_CAPITAL_REQUIRED",
                    "candidate_shares": 0,
                    "estimated_order_value": 0,
                    "capital_status": "CAPITAL_REQUIRED",
                    "latest_price": 410500,
                    "target_value": 0,
                    "execution_mode": "MANUAL_REVIEW_ONLY",
                }
            ]
        ).to_csv(orders_dir / "order_candidates.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "scenario_capital": 3_000_000,
                    "scenario_status": "SCENARIO_REVIEW_ONLY",
                    "order_status": "NO_ORDER",
                    "execution_mode": "MANUAL_REVIEW_ONLY",
                    "latest_price": 410500,
                    "max_position_weight": 0.15,
                    "cash_buffer_weight": 0.25,
                    "target_position_value": 450000,
                    "target_position_shares": 1,
                    "first_tranche_value": 135000,
                    "first_tranche_shares": 0,
                    "second_tranche_value": 135000,
                    "second_tranche_shares": 0,
                    "final_tranche_value": 180000,
                    "final_tranche_shares": 0,
                }
            ]
        ).to_csv(orders_dir / "capital_scenarios.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG",
                    "tracking_status": "TRACKING_ACTIVE",
                    "buy_date": "2026-05-28",
                    "buy_price": 116000,
                    "shares": 5,
                    "latest_price": 121800,
                    "latest_price_date": "2026-06-04",
                    "invested_value": 580000,
                    "current_value": 609000,
                    "unrealized_pnl": 29000,
                    "unrealized_return": 0.05,
                    "one_week_check_date": "2026-06-04",
                    "one_month_check_date": "2026-06-28",
                    "quarter_check_date": "2026-08-28",
                    "one_week_due": "YES",
                    "one_month_due": "NO",
                    "quarter_due": "NO",
                    "thesis": "지주 가치 재평가",
                    "thesis_status": "INTACT",
                    "stop_loss_rule": "-7% 손실 시 축소",
                    "review_action": "ONE_WEEK_REVIEW_DUE",
                    "order_status": "NO_ORDER",
                    "broker_order_requested": "NO",
                    "next_step": "점검일마다 thesis 유지 여부와 손익 원인을 기록하세요.",
                }
            ]
        ).to_csv(tracking_dir / "performance_tracking.csv", index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "삼성물산",
                    "capital_plan_review": "PASS_CANDIDATE",
                    "amount_status": "CAPITAL_AMOUNT_REQUIRED",
                    "order_status": "NO_ORDER",
                    "max_position_weight": 0.15,
                    "cash_buffer_weight": 0.25,
                    "first_tranche_pct": 0.30,
                    "second_tranche_pct": 0.30,
                    "final_tranche_pct": 0.40,
                    "add_condition": "Add only if CORE_FOCUS persists",
                    "reduce_condition": "If SMA20 breaks and average cost drawdown reaches -7%, reduce 50%",
                    "stop_condition": "If conviction_score < 60, stop new buys",
                    "immediate_halt_condition": "실적 훼손 또는 치명적 공시 리스크 발생 시 즉시 중단",
                    "review_notes": "rules fixed before amount",
                }
            ]
        ).to_csv(capital_plan_dir / "capital_plan_review_028260.csv", index=False)

        output = module.run_dashboard(reports_dir=reports)

        assert output.html_path.exists()
        assert output.summary["top_symbol"] == "028260.KS"
        assert output.summary["order_status"] == "NO_ORDER"

        html = output.html_path.read_text(encoding="utf-8")
        assert "퀀트 트레이너" in html
        assert "오늘 결론" in html
        assert "지금 할 일" in html
        assert "1순위 후보" in html
        assert "삼성물산" in html
        assert "기다림" in html
        assert "자동 주문 없음" in html
        assert "주문은 자동 실행되지 않습니다" in html
        assert "1순위 공시 리스크" in html
        assert "치명 0개 / 통과 후보(모니터링 필요)" in html
        assert "왜 후보인가" in html
        assert "매수 금지 이유" in html
        assert "손실 방어 규칙" in html
        assert "공시 리스크 요약" in html
        assert "치명적 리스크 0개" in html
        assert "후보별 공시 리스크 현황" in html
        assert "Semiconductor filing risk" in html
        assert "수동 확인 6개 항목" in html
        assert "자본 계획" in html
        assert "투자 후 성과 추적" in html
        assert "1주 점검 필요" in html
        assert "다른 후보와 비교" in html
        assert "내가 넣은 종목 분석 상태" in html
        assert "사용자 추가 기업" in html
        assert "미래에셋증권" in html
        assert "상세 자료" in html
        assert "Quantum Stocks Dashboard" not in html
        assert "Decision Gate" not in html
        assert "manual gate" not in html
        assert "conviction_score" not in html
        assert "upside_probability" not in html
        assert "actual_config_written" not in html
        assert "missing cached price history" not in html
        assert "Broker order" not in html


def test_dashboard_labels_missing_top_filing_risk_as_review_required() -> None:
    module = importlib.import_module("quantum_trainer.dashboard")

    assert module._filing_risk_status_text(pd.DataFrame(), "UNKNOWN") == "공시요약 없음 / 검토 필요"
    assert "filing risk summary" not in module._friendly_text(
        "pre-buy decision is WAIT; filing risk summary not available"
    )
    assert "filing risk hold review" not in module._friendly_text("filing risk hold review")
    assert module._decision_sentence("코미코", "WAIT").startswith("코미코는")
