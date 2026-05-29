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


def test_operating_status_reports_not_done_with_current_blockers() -> None:
    module = importlib.import_module("quantum_trainer.operating_status")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        reports = Path(tmp_dir) / "reports"
        _write_pre_buy(reports, decision_status="WAIT", capital_status="CAPITAL_AMOUNT_REQUIRED")
        _write_decision_gate(reports, status="WAITING_MANUAL_EVIDENCE")
        _write_manual_apply_plan(reports, actual_written="NO")
        _write_universe_coverage(reports, universe_status="PASS_CANDIDATE", price_status="PRICE_COVERAGE_READY")
        _write_order_candidates(reports, order_status="BLOCKED_CAPITAL_REQUIRED")

        output = module.run_operating_status(reports_dir=reports)

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        row = output.report.iloc[0]
        assert row["completion_status"] == "NOT_DONE"
        assert row["usage_status"] == "READY_FOR_REVIEW_USE"
        assert row["order_status"] == "NO_ORDER"
        assert row["broker_order_requested"] == "NO"
        assert "decision gate waiting manual evidence" in row["blockers"]
        assert "actual manual review config not applied" in row["blockers"]
        assert "capital amount required" in row["blockers"]
        assert "manual review" in row["next_step"]
        assert "capital" in row["next_step"]


def test_operating_status_reports_done_only_after_manual_and_capital_gates() -> None:
    module = importlib.import_module("quantum_trainer.operating_status")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        reports = Path(tmp_dir) / "reports"
        _write_pre_buy(reports, decision_status="BUY_READY", capital_status="CAPITAL_READY", blockers="")
        _write_decision_gate(reports, status="READY_FOR_SIZING_REVIEW")
        _write_manual_apply_plan(reports, actual_written="YES")
        _write_universe_coverage(reports, universe_status="PASS_CANDIDATE", price_status="PRICE_COVERAGE_READY")
        _write_order_candidates(reports, order_status="REVIEW_ONLY", capital_status="CAPITAL_READY")

        output = module.run_operating_status(reports_dir=reports)

        row = output.report.iloc[0]
        assert row["completion_status"] == "DONE"
        assert row["usage_status"] == "READY_FOR_REVIEW_USE"
        assert row["order_status"] == "NO_ORDER"
        assert row["done_message"] == "DONE: 끝. Review dashboard is ready; broker order still requires manual action."
        assert row["blockers"] == ""


def test_operating_status_ignores_pre_buy_user_approval_note_as_blocker() -> None:
    module = importlib.import_module("quantum_trainer.operating_status")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        reports = Path(tmp_dir) / "reports"
        _write_pre_buy(
            reports,
            decision_status="BUY_READY",
            capital_status="CAPITAL_PROVIDED",
            blockers="no automatic blocker; user approval still required",
        )
        _write_decision_gate(reports, status="READY_FOR_SIZING_REVIEW")
        _write_manual_apply_plan(reports, actual_written="YES")
        _write_universe_coverage(reports, universe_status="PASS_CANDIDATE", price_status="PRICE_COVERAGE_READY")
        _write_order_candidates(reports, order_status="REVIEW_ONLY", capital_status="CAPITAL_PROVIDED")

        output = module.run_operating_status(reports_dir=reports)

        row = output.report.iloc[0]
        assert row["completion_status"] == "DONE"
        assert row["blockers"] == ""


def test_operating_status_accepts_partial_full_universe_price_coverage() -> None:
    module = importlib.import_module("quantum_trainer.operating_status")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        reports = Path(tmp_dir) / "reports"
        _write_pre_buy(reports, decision_status="BUY_READY", capital_status="CAPITAL_PROVIDED", blockers="")
        _write_decision_gate(reports, status="READY_FOR_SIZING_REVIEW")
        _write_manual_apply_plan(reports, actual_written="YES")
        _write_universe_coverage(reports, universe_status="PASS_CANDIDATE", price_status="PRICE_COVERAGE_PARTIAL")
        _write_order_candidates(reports, order_status="REVIEW_ONLY", capital_status="CAPITAL_PROVIDED")

        output = module.run_operating_status(reports_dir=reports)

        row = output.report.iloc[0]
        assert row["completion_status"] == "DONE"
        assert "price coverage not ready" not in row["blockers"]


def _write_pre_buy(
    reports: Path,
    decision_status: str,
    capital_status: str,
    blockers: str = "actual manual review config not applied; capital amount required",
) -> None:
    path = reports / "pre_buy_decision"
    path.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "symbol": "028260.KS",
                "company_name": "Samsung C&T",
                "decision_status": decision_status,
                "order_status": "NO_ORDER",
                "final_action": "NO_ORDER",
                "manual_proposal_status": "READY_FOR_USER_CONFIRMATION",
                "capital_status": capital_status,
                "readiness_blockers": blockers,
                "buy_reasons": "conviction_score=77.01",
                "buy_ban_reasons": "manual gate not ready",
                "entry_price_low": 386000,
                "entry_price_high": 410500,
                "staged_buy_plan": "first tranche 30%",
                "stop_loss_rule": "SMA20 break",
                "next_review_date": "2026-05-29",
            }
        ]
    ).to_csv(path / "pre_buy_decision.csv", index=False)


def _write_decision_gate(reports: Path, status: str) -> None:
    path = reports / "decision_gate"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "symbol": "028260.KS",
                "company_name": "Samsung C&T",
                "decision_gate_status": status,
                "order_status": "NO_ORDER",
                "gate_reason": "manual evidence",
                "filing_review": "PASS",
                "earnings_review": "PASS",
                "business_driver_review": "PASS",
                "valuation_review": "PASS",
                "loss_rule_review": "PASS",
                "capital_plan_review": "PASS",
                "loss_defense": "SMA20 break",
            }
        ]
    ).to_csv(path / "decision_gate.csv", index=False)


def _write_manual_apply_plan(reports: Path, actual_written: str) -> None:
    path = reports / "decision_gate"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "symbol": "028260.KS",
                "apply_mode": "CONFIRMED_WRITE" if actual_written == "YES" else "DRY_RUN",
                "ready_to_apply": "YES",
                "confirm_required": "YES",
                "actual_config_written": actual_written,
                "actual_output_csv": "configs/manual_review.actual.csv",
                "blocker": "" if actual_written == "YES" else "waiting for explicit user confirmation",
                "candidate_source": "manual_review_proposal.csv",
            }
        ]
    ).to_csv(path / "manual_review_apply_plan.csv", index=False)


def _write_universe_coverage(reports: Path, universe_status: str, price_status: str) -> None:
    path = reports / "universe_coverage"
    path.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "universe_status": universe_status,
                "universe_count": 35,
                "min_count": 20,
                "max_count": 50,
                "count_status": "READY",
                "sector_count": 8,
                "required_symbol_count": 6,
                "required_missing_count": 0,
                "required_missing_symbols": "",
                "price_coverage_status": price_status,
                "price_missing_count": 0,
                "price_missing_symbols": "",
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "next_step": "universe ready",
            }
        ]
    ).to_csv(path / "universe_coverage.csv", index=False)


def _write_order_candidates(
    reports: Path,
    order_status: str,
    capital_status: str = "CAPITAL_REQUIRED",
) -> None:
    path = reports / "orders"
    path.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "symbol": "028260.KS",
                "company_name": "Samsung C&T",
                "order_status": order_status,
                "candidate_shares": 0,
                "estimated_order_value": 0,
                "capital_status": capital_status,
                "latest_price": 410500,
                "target_value": 0,
                "execution_mode": "MANUAL_REVIEW_ONLY",
            }
        ]
    ).to_csv(path / "order_candidates.csv", index=False)
