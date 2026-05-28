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


def test_pre_buy_decision_keeps_wait_and_no_order_until_manual_gate_is_ready() -> None:
    module = importlib.import_module("quantum_trainer.pre_buy_decision")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        profit_csv = root / "profit_focus.csv"
        gate_csv = root / "decision_gate.csv"
        research_csv = root / "company_research.csv"
        filing_dir = root / "filing_review"
        decision_dir = root / "decision_gate"
        output_dir = root / "reports"
        filing_dir.mkdir()
        decision_dir.mkdir()

        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "sector": "Holding",
                    "profit_focus_status": "CORE_FOCUS",
                    "conviction_score": 82.13,
                    "expected_20d_return": 0.147,
                    "upside_probability": 0.99,
                    "ma20_gap": 0.064,
                    "return_20d": 0.318,
                    "why_profit_candidate": "conviction_score=82.13; upside_probability=99.0%",
                    "why_not_now": "핵심 후보지만 실제 주문 전 수동 확인 필요",
                    "invalidation_rule": "TODAY_FOCUS 이탈, SMA20 하회, conviction_score 60 미만",
                    "next_step": "사업/공시 수동 확인",
                }
            ]
        ).to_csv(profit_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "decision_gate_status": "WAITING_MANUAL_EVIDENCE",
                    "order_status": "NO_ORDER",
                    "gate_reason": "수동 근거 대기: filing_review",
                    "filing_review": "UNKNOWN",
                    "earnings_review": "UNKNOWN",
                    "business_driver_review": "UNKNOWN",
                    "valuation_review": "UNKNOWN",
                    "loss_rule_review": "UNKNOWN",
                    "capital_plan_review": "UNKNOWN",
                    "loss_defense": "TODAY_FOCUS 이탈",
                }
            ]
        ).to_csv(gate_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "latest_price": 410500,
                    "ma20_gap": 0.064,
                    "per": 17.86,
                    "pbr": 1.21,
                    "debt_ratio": 0.505,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                }
            ]
        ).to_csv(research_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "risk_id": "legal_litigation_exposure",
                    "risk_title": "Legal litigation exposure",
                    "source_checks": "litigation_review",
                    "evidence_count": 4,
                    "key_evidence": "소송 충당부채 확인",
                    "fatal_risk": "NO",
                    "gate_opinion": "PASS_CANDIDATE_WITH_MONITORING",
                    "monitoring_rule": "소송 충당부채 변화 확인",
                }
            ]
        ).to_csv(filing_dir / "filing_risk_summary_028260.csv", index=False)
        manual_proposal_csv = decision_dir / "manual_review_proposal.csv"
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
        ).to_csv(manual_proposal_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "capital_plan_review": "PASS_CANDIDATE",
                    "amount_status": "CAPITAL_AMOUNT_REQUIRED",
                    "order_status": "NO_ORDER",
                    "max_position_weight": 0.15,
                    "cash_buffer_weight": 0.25,
                    "first_tranche_pct": 0.30,
                    "second_tranche_pct": 0.30,
                    "final_tranche_pct": 0.40,
                    "add_condition": "Add only if CORE_FOCUS persists",
                    "reduce_condition": "Reduce at -7%",
                    "stop_condition": "Stop at -10%",
                    "immediate_halt_condition": "실적 훼손 시 즉시 중단",
                    "review_notes": "rules fixed before amount",
                }
            ]
        ).to_csv(decision_dir / "capital_plan_review_028260.csv", index=False)

        output = module.run_pre_buy_decision(
            profit_focus_csv=profit_csv,
            decision_gate_csv=gate_csv,
            company_research_csv=research_csv,
            filing_risk_dir=filing_dir,
            output_dir=output_dir,
            manual_proposal_csv=manual_proposal_csv,
            capital_plan_dir=decision_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.report.loc[0, "decision_status"] == "WAIT"
        assert output.report.loc[0, "order_status"] == "NO_ORDER"
        assert output.report.loc[0, "entry_price_low"] == 386000
        assert output.report.loc[0, "entry_price_high"] == 410500
        assert "manual gate not ready" in output.report.loc[0, "buy_ban_reasons"]
        assert output.report.loc[0, "final_action"] == "NO_ORDER"
        assert output.report.loc[0, "manual_proposal_status"] == "READY_FOR_USER_CONFIRMATION"
        assert output.report.loc[0, "capital_status"] == "CAPITAL_AMOUNT_REQUIRED"
        assert "actual manual review config not applied" in output.report.loc[0, "readiness_blockers"]
        assert "capital amount required" in output.report.loc[0, "readiness_blockers"]
        assert "first tranche 30%" in output.report.loc[0, "staged_buy_plan"]
        assert "SMA20 break" in output.report.loc[0, "stop_loss_rule"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Pre-Buy Decision" in markdown
        assert "WAIT" in markdown
        assert "NO_ORDER" in markdown
        assert "READY_FOR_USER_CONFIRMATION" in markdown
        assert "capital amount required" in markdown
        assert "386,000-410,500" in markdown


def test_pre_buy_decision_rejects_fatal_filing_risk_even_if_gate_ready() -> None:
    module = importlib.import_module("quantum_trainer.pre_buy_decision")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        profit_csv = root / "profit_focus.csv"
        gate_csv = root / "decision_gate.csv"
        research_csv = root / "company_research.csv"
        filing_dir = root / "filing_review"
        output_dir = root / "reports"
        filing_dir.mkdir()

        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "sector": "Holding",
                    "profit_focus_status": "CORE_FOCUS",
                    "conviction_score": 82.13,
                    "expected_20d_return": 0.147,
                    "upside_probability": 0.99,
                    "ma20_gap": 0.064,
                    "return_20d": 0.318,
                    "why_profit_candidate": "좋은 후보",
                    "why_not_now": "",
                    "invalidation_rule": "TODAY_FOCUS 이탈",
                    "next_step": "검토",
                }
            ]
        ).to_csv(profit_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "decision_gate_status": "READY_FOR_SIZING_REVIEW",
                    "order_status": "NO_ORDER",
                    "gate_reason": "수동 근거 6개 PASS",
                    "filing_review": "PASS",
                    "earnings_review": "PASS",
                    "business_driver_review": "PASS",
                    "valuation_review": "PASS",
                    "loss_rule_review": "PASS",
                    "capital_plan_review": "PASS",
                    "loss_defense": "TODAY_FOCUS 이탈",
                }
            ]
        ).to_csv(gate_csv, index=False)
        pd.DataFrame([{"symbol": "028260.KS", "latest_price": 410500, "ma20_gap": 0.064}]).to_csv(
            research_csv, index=False
        )
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "risk_id": "fatal",
                    "risk_title": "Fatal filing risk",
                    "source_checks": "filing_review",
                    "evidence_count": 1,
                    "key_evidence": "상장폐지",
                    "fatal_risk": "YES",
                    "gate_opinion": "EXCLUDE",
                    "monitoring_rule": "exclude",
                }
            ]
        ).to_csv(filing_dir / "filing_risk_summary_028260.csv", index=False)

        output = module.run_pre_buy_decision(
            profit_focus_csv=profit_csv,
            decision_gate_csv=gate_csv,
            company_research_csv=research_csv,
            filing_risk_dir=filing_dir,
            output_dir=output_dir,
        )

        assert output.report.loc[0, "decision_status"] == "REJECT"
        assert output.report.loc[0, "order_status"] == "NO_ORDER"
        assert "fatal filing risk" in output.report.loc[0, "buy_ban_reasons"]
