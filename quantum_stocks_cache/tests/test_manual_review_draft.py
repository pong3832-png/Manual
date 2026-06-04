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


def test_manual_review_draft_creates_human_gate_candidates_without_actual_pass() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_draft")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        memo_csv = root / "investment_memo.csv"
        checklist_csv = root / "investment_checklist.csv"
        research_csv = root / "company_research.csv"
        filing_dir = root / "filing_review"
        output_dir = root / "reports"
        filing_dir.mkdir()

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "sector": "Holding",
                    "memo_status": "THESIS_REVIEW",
                    "order_status": "NO_ORDER",
                    "core_thesis": "LG Corp is CORE_FOCUS from local data.",
                    "evidence": "conviction_score=68.64; PER=17.96; PBR=0.59",
                    "risks": "자동 차단 리스크 없음",
                    "manual_checks": "최근 공시 확인; 손절 조건 문서화; 실제 주문 전 current_weights 확인",
                    "loss_defense": "TODAY_FOCUS 이탈, SMA20 하회, conviction_score 60 미만",
                    "next_action": "수동 확인 후 투자금이 생길 때만 order_sizer 검토",
                }
            ]
        ).to_csv(memo_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "manual_checklist": "최근 공시 확인; 목표 비중은 별도 order sizing에서만 계산",
                }
            ]
        ).to_csv(checklist_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "research_score": 75.18,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "expected_20d_return": 0.057,
                    "upside_probability": 0.629,
                    "return_20d": 0.15,
                    "ma20_gap": 0.057,
                    "drawdown_20d": -0.03,
                    "per": 17.96,
                    "pbr": 0.59,
                    "debt_ratio": 0.4,
                }
            ]
        ).to_csv(research_csv, index=False)

        output = module.run_manual_review_draft(
            investment_memo_csv=memo_csv,
            investment_checklist_csv=checklist_csv,
            company_research_csv=research_csv,
            filing_risk_dir=filing_dir,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert (output_dir / "decision_gate" / "manual_review_draft_003550.csv").exists()
        assert (output_dir / "decision_gate" / "manual_review_draft_003550.md").exists()

        row = output.report.iloc[0]
        assert row["symbol"] == "003550.KS"
        assert row["filing_review"] == "UNKNOWN"
        assert row["earnings_review"] == "PASS_CANDIDATE"
        assert row["business_driver_review"] == "PASS_CANDIDATE"
        assert row["valuation_review"] == "PASS_CANDIDATE"
        assert row["loss_rule_review"] == "PASS_CANDIDATE"
        assert row["capital_plan_review"] == "UNKNOWN"
        assert row["recommended_actual_action"] == "DO_NOT_COPY_AUTOMATICALLY"
        assert "OpenDART filing risk summary not available" in row["review_notes"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Manual Review Draft" in markdown
        assert "003550.KS LG Corp" in markdown
        assert "PASS_CANDIDATE" in markdown
        assert "Do not copy" in markdown


def test_manual_review_draft_uses_capital_plan_review_as_candidate_evidence() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_draft")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        memo_csv = root / "investment_memo.csv"
        checklist_csv = root / "investment_checklist.csv"
        research_csv = root / "company_research.csv"
        filing_dir = root / "filing_review"
        capital_dir = root / "decision_gate"
        output_dir = root / "reports"
        filing_dir.mkdir()
        capital_dir.mkdir()

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "sector": "Holding",
                    "memo_status": "THESIS_REVIEW",
                    "order_status": "NO_ORDER",
                    "core_thesis": "LG Corp is CORE_FOCUS from local data.",
                    "evidence": "conviction_score=68.64; PER=17.96; PBR=0.59",
                    "risks": "자동 차단 리스크 없음",
                    "manual_checks": "최근 공시 확인; 손절 조건 문서화; 실제 주문 전 current_weights 확인",
                    "loss_defense": "TODAY_FOCUS 이탈, SMA20 하회, conviction_score 60 미만",
                    "next_action": "수동 확인 후 투자금이 생길 때만 order_sizer 검토",
                }
            ]
        ).to_csv(memo_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "manual_checklist": "최근 공시 확인; 목표 비중은 별도 order sizing에서만 계산",
                }
            ]
        ).to_csv(checklist_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "research_score": 75.18,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "expected_20d_return": 0.057,
                    "upside_probability": 0.629,
                    "return_20d": 0.15,
                    "ma20_gap": 0.057,
                    "drawdown_20d": -0.03,
                    "per": 17.96,
                    "pbr": 0.59,
                    "debt_ratio": 0.4,
                }
            ]
        ).to_csv(research_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "capital_plan_review": "PASS_CANDIDATE",
                    "amount_status": "CAPITAL_AMOUNT_REQUIRED",
                    "order_status": "NO_ORDER",
                }
            ]
        ).to_csv(capital_dir / "capital_plan_review_003550.csv", index=False)

        output = module.run_manual_review_draft(
            investment_memo_csv=memo_csv,
            investment_checklist_csv=checklist_csv,
            company_research_csv=research_csv,
            filing_risk_dir=filing_dir,
            output_dir=output_dir,
            capital_plan_dir=capital_dir,
        )

        row = output.report.iloc[0]
        assert row["capital_plan_review"] == "PASS_CANDIDATE"
        assert "capital_plan=CAPITAL_AMOUNT_REQUIRED" in row["review_notes"]


def test_manual_review_draft_keeps_filing_unknown_when_summary_has_hold_review() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_draft")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        memo_csv = root / "investment_memo.csv"
        checklist_csv = root / "investment_checklist.csv"
        research_csv = root / "company_research.csv"
        filing_dir = root / "filing_review"
        output_dir = root / "reports"
        filing_dir.mkdir()

        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "Komico",
                    "sector": "Equipment",
                    "memo_status": "THESIS_REVIEW",
                    "order_status": "NO_ORDER",
                    "core_thesis": "Komico is CORE_FOCUS from local data.",
                    "evidence": "conviction_score=74.83",
                    "risks": "filing hold review",
                    "manual_checks": "최근 공시 확인",
                    "loss_defense": "TODAY_FOCUS exit",
                    "next_action": "수동 확인",
                }
            ]
        ).to_csv(memo_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "manual_checklist": "최근 공시 확인",
                }
            ]
        ).to_csv(checklist_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "research_score": 69.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "expected_20d_return": 0.2,
                    "upside_probability": 0.99,
                    "return_20d": 0.21,
                    "ma20_gap": 0.11,
                    "drawdown_20d": -0.09,
                    "per": 20.0,
                    "pbr": 1.5,
                    "debt_ratio": 0.4,
                }
            ]
        ).to_csv(research_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "risk_id": "regulatory_accounting_litigation_overhang",
                    "risk_title": "Regulatory/accounting litigation overhang",
                    "source_checks": "",
                    "evidence_count": 0,
                    "key_evidence": "keyword hit 부족",
                    "fatal_risk": "NO",
                    "gate_opinion": "HOLD_REVIEW",
                    "monitoring_rule": "추가 확인",
                }
            ]
        ).to_csv(filing_dir / "filing_risk_summary_183300.csv", index=False)

        output = module.run_manual_review_draft(
            investment_memo_csv=memo_csv,
            investment_checklist_csv=checklist_csv,
            company_research_csv=research_csv,
            filing_risk_dir=filing_dir,
            output_dir=output_dir,
        )

        row = output.report.iloc[0]
        assert row["filing_review"] == "UNKNOWN"
        assert "filing risk summary has hold-review opinion" in row["review_notes"]


def test_manual_review_draft_keeps_premium_valuation_unknown_with_explicit_reason() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_draft")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        memo_csv = root / "investment_memo.csv"
        checklist_csv = root / "investment_checklist.csv"
        research_csv = root / "company_research.csv"
        filing_dir = root / "filing_review"
        output_dir = root / "reports"
        filing_dir.mkdir()

        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "Komico",
                    "sector": "Equipment",
                    "memo_status": "THESIS_REVIEW",
                    "order_status": "NO_ORDER",
                    "core_thesis": "Komico remains the strongest research candidate.",
                    "evidence": "conviction_score=74.83; PER=40.08; PBR=4.75",
                    "risks": "premium valuation and semiconductor cycle risk",
                    "manual_checks": "valuation premium 확인",
                    "loss_defense": "TODAY_FOCUS exit",
                    "next_action": "wait for pullback",
                }
            ]
        ).to_csv(memo_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "manual_checklist": "높은 PER/PBR 확인",
                }
            ]
        ).to_csv(checklist_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "research_score": 69.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "expected_20d_return": 0.2,
                    "upside_probability": 0.99,
                    "return_20d": 0.21,
                    "ma20_gap": 0.11,
                    "drawdown_20d": -0.09,
                    "per": 40.08,
                    "pbr": 4.75,
                    "debt_ratio": 2.145,
                }
            ]
        ).to_csv(research_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "risk_id": "regulatory_accounting_litigation_overhang",
                    "risk_title": "Regulatory/accounting litigation overhang",
                    "source_checks": "manual_resolution",
                    "evidence_count": 0,
                    "key_evidence": "HOLD_REVIEW resolved as keyword-evidence gap",
                    "fatal_risk": "NO",
                    "gate_opinion": "PASS_CANDIDATE_WITH_MONITORING",
                    "monitoring_rule": "audit opinion, restatement, sanction, litigation",
                }
            ]
        ).to_csv(filing_dir / "filing_risk_summary_183300.csv", index=False)

        output = module.run_manual_review_draft(
            investment_memo_csv=memo_csv,
            investment_checklist_csv=checklist_csv,
            company_research_csv=research_csv,
            filing_risk_dir=filing_dir,
            output_dir=output_dir,
        )

        row = output.report.iloc[0]
        assert row["valuation_review"] == "UNKNOWN"
        assert "valuation premium: PER=40.08, PBR=4.75" in row["review_notes"]


def test_manual_review_draft_uses_memo_valuation_when_research_metrics_are_blank() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_draft")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        memo_csv = root / "investment_memo.csv"
        checklist_csv = root / "investment_checklist.csv"
        research_csv = root / "company_research.csv"
        filing_dir = root / "filing_review"
        output_dir = root / "reports"
        filing_dir.mkdir()

        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "Komico",
                    "sector": "Equipment",
                    "memo_status": "THESIS_REVIEW",
                    "order_status": "NO_ORDER",
                    "core_thesis": "Komico remains a WAIT candidate.",
                    "evidence": "PER=40.08; PBR=4.75; ROE=19.69%; total_liabilities_to_equity=214.5%",
                    "risks": "premium valuation requires review",
                    "manual_checks": "valuation premium 확인",
                    "loss_defense": "TODAY_FOCUS exit",
                    "next_action": "wait for pullback",
                }
            ]
        ).to_csv(memo_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "manual_checklist": "높은 PER/PBR 확인",
                }
            ]
        ).to_csv(checklist_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "research_score": 69.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "expected_20d_return": 0.2,
                    "upside_probability": 0.99,
                    "return_20d": 0.21,
                    "ma20_gap": 0.11,
                    "drawdown_20d": -0.09,
                    "per": "",
                    "pbr": "",
                    "debt_ratio": "",
                }
            ]
        ).to_csv(research_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "risk_id": "regulatory_accounting_litigation_overhang",
                    "risk_title": "Regulatory/accounting litigation overhang",
                    "source_checks": "manual_resolution",
                    "evidence_count": 0,
                    "key_evidence": "HOLD_REVIEW resolved as keyword-evidence gap",
                    "fatal_risk": "NO",
                    "gate_opinion": "PASS_CANDIDATE_WITH_MONITORING",
                    "monitoring_rule": "audit opinion, restatement, sanction, litigation",
                }
            ]
        ).to_csv(filing_dir / "filing_risk_summary_183300.csv", index=False)

        output = module.run_manual_review_draft(
            investment_memo_csv=memo_csv,
            investment_checklist_csv=checklist_csv,
            company_research_csv=research_csv,
            filing_risk_dir=filing_dir,
            output_dir=output_dir,
        )

        row = output.report.iloc[0]
        assert row["valuation_review"] == "UNKNOWN"
        assert "PER=40.08" in row["review_notes"]
        assert "PBR=4.75" in row["review_notes"]
        assert "valuation premium: PER=40.08, PBR=4.75" in row["review_notes"]
