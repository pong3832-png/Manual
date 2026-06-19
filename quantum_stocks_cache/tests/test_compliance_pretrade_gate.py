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


def test_market_risk_off_blocks_pretrade_review() -> None:
    module = importlib.import_module("quantum_trainer.compliance_pretrade_gate")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        reports = Path(tmp_dir) / "reports"
        _write_common_inputs(reports, market_status="RISK_OFF", market_posture="DEFENSIVE")

        output = module.run_compliance_pretrade_gate(reports_dir=reports)

        row = output.report.set_index("symbol").loc["READY.KS"]
        assert row["final_compliance_status"] == "BLOCK"
        assert row["market_gate"].startswith("BLOCK")
        assert row["primary_blocker"] == "market gate blocked"
        _assert_no_order(output.report)


def test_filing_hold_review_waits_for_evidence_or_blocks() -> None:
    module = importlib.import_module("quantum_trainer.compliance_pretrade_gate")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        reports = Path(tmp_dir) / "reports"
        _write_common_inputs(reports)
        _write_filing_risk(reports, "READY.KS", gate_opinion="HOLD_REVIEW", fatal_risk="NO")

        output = module.run_compliance_pretrade_gate(reports_dir=reports)

        row = output.report.set_index("symbol").loc["READY.KS"]
        assert row["final_compliance_status"] in {"WAIT_EVIDENCE", "BLOCK"}
        assert row["filing_gate"].startswith("WAIT")
        assert "filing" in row["required_next_evidence"]
        _assert_no_order(output.report)


def test_valuation_unknown_waits_for_evidence() -> None:
    module = importlib.import_module("quantum_trainer.compliance_pretrade_gate")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        reports = Path(tmp_dir) / "reports"
        _write_common_inputs(reports, valuation_status="VALUATION_DATA_REQUIRED")

        output = module.run_compliance_pretrade_gate(reports_dir=reports)

        row = output.report.set_index("symbol").loc["READY.KS"]
        assert row["final_compliance_status"] == "WAIT_EVIDENCE"
        assert row["valuation_gate"].startswith("WAIT")
        assert "valuation" in row["required_next_evidence"]
        _assert_no_order(output.report)


def test_all_local_pass_candidates_only_reach_human_review() -> None:
    module = importlib.import_module("quantum_trainer.compliance_pretrade_gate")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        reports = Path(tmp_dir) / "reports"
        _write_common_inputs(reports)

        output = module.run_compliance_pretrade_gate(reports_dir=reports)

        row = output.report.set_index("symbol").loc["READY.KS"]
        assert row["final_compliance_status"] == "READY_FOR_HUMAN_REVIEW"
        assert row["order_status"] == "NO_ORDER"
        assert row["broker_order_requested"] == "NO"
        assert "not order permission" in row["action_summary"]
        _assert_no_order(output.report)


def test_missing_inputs_become_data_required_without_external_api() -> None:
    module = importlib.import_module("quantum_trainer.compliance_pretrade_gate")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        reports = Path(tmp_dir) / "reports"
        reports.mkdir()

        output = module.run_compliance_pretrade_gate(reports_dir=reports)

        assert output.report.iloc[0]["symbol"] == "DATA_REQUIRED"
        assert output.report.iloc[0]["final_compliance_status"] == "WAIT_EVIDENCE"
        assert "DATA_REQUIRED" in output.report.iloc[0]["primary_blocker"]
        assert output.summary["external_api_requested"] == "NO"
        _assert_no_order(output.report)


def _assert_no_order(report: pd.DataFrame) -> None:
    assert set(report["external_api_requested"]) == {"NO"}
    assert set(report["order_status"]) == {"NO_ORDER"}
    assert set(report["broker_order_requested"]) == {"NO"}


def _write_common_inputs(
    reports: Path,
    market_status: str = "RISK_ON",
    market_posture: str = "SELECTIVE_BUY_REVIEW",
    valuation_status: str = "VALUATION_READY",
) -> None:
    _write_market_regime(reports, market_status, market_posture)
    _write_pre_buy(reports)
    _write_decision_gate(reports)
    _write_manual_proposal(reports, actual_config_written="YES")
    _write_valuation(reports, valuation_status)
    _write_rebound(reports)
    _write_tactical(reports)
    _write_filing_risk(reports, "READY.KS")


def _write_market_regime(reports: Path, market_status: str, market_posture: str) -> None:
    path = reports / "market_regime"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "scope": "MARKET",
                "sector": "ALL",
                "regime_status": market_status,
                "risk_posture": market_posture,
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "action_summary": "local market gate",
            },
            {
                "scope": "SECTOR",
                "sector": "Semiconductors",
                "regime_status": "RISK_ON",
                "risk_posture": "SELECTIVE_BUY_REVIEW",
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "action_summary": "local sector gate",
            },
        ]
    ).to_csv(path / "market_regime.csv", index=False)


def _write_pre_buy(reports: Path) -> None:
    path = reports / "pre_buy_decision"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "symbol": "READY.KS",
                "company_name": "Ready Co",
                "decision_status": "BUY_READY",
                "order_status": "NO_ORDER",
                "final_action": "NO_ORDER",
                "manual_proposal_status": "READY_FOR_USER_CONFIRMATION",
                "capital_status": "CAPITAL_PROVIDED",
                "readiness_blockers": "",
                "buy_reasons": "local candidate",
                "buy_ban_reasons": "no automatic buy ban; keep NO_ORDER until user approval",
            }
        ]
    ).to_csv(path / "pre_buy_decision.csv", index=False)


def _write_decision_gate(reports: Path) -> None:
    path = reports / "decision_gate"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "symbol": "READY.KS",
                "company_name": "Ready Co",
                "sector": "Semiconductors",
                "decision_gate_status": "READY_FOR_SIZING_REVIEW",
                "order_status": "NO_ORDER",
                "gate_reason": "manual evidence pass",
                "filing_review": "PASS",
                "earnings_review": "PASS",
                "business_driver_review": "PASS",
                "valuation_review": "PASS",
                "loss_rule_review": "PASS",
                "capital_plan_review": "PASS",
                "review_notes": "local only",
            }
        ]
    ).to_csv(path / "decision_gate.csv", index=False)


def _write_manual_proposal(reports: Path, actual_config_written: str) -> None:
    path = reports / "decision_gate"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "symbol": "READY.KS",
                "proposal_status": "READY_FOR_USER_CONFIRMATION",
                "approval_required": "YES",
                "apply_target": "configs/manual_review.actual.csv",
                "source_action": "DO_NOT_COPY_AUTOMATICALLY",
            }
        ]
    ).to_csv(path / "manual_review_proposal.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "READY.KS",
                "actual_config_written": actual_config_written,
                "blocker": "",
            }
        ]
    ).to_csv(path / "manual_review_apply_plan.csv", index=False)


def _write_valuation(reports: Path, status: str) -> None:
    path = reports / "valuation_data_quality"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "symbol": "READY.KS",
                "company_name": "Ready Co",
                "valuation_status": status,
                "valuation_review_candidate": "PASS_CANDIDATE" if status == "VALUATION_READY" else "UNKNOWN",
                "data_gap": "NO_GAP" if status == "VALUATION_READY" else "VALUATION_DATA_REQUIRED",
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
            }
        ]
    ).to_csv(path / "valuation_data_quality.csv", index=False)


def _write_rebound(reports: Path) -> None:
    path = reports / "panic_rebound_signal"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "symbol": "READY.KS",
                "company_name": "Ready Co",
                "rebound_status": "READY_REBOUND_REVIEW",
                "chase_risk": "LOW",
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "broker_order_requested": "NO",
            }
        ]
    ).to_csv(path / "panic_rebound_signal.csv", index=False)


def _write_tactical(reports: Path) -> None:
    path = reports / "tactical_watchlist"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "symbol": "READY.KS",
                "company_name": "Ready Co",
                "sector": "Semiconductors",
                "tactical_status": "READY_MANUAL_REVIEW",
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "broker_order_requested": "NO",
            }
        ]
    ).to_csv(path / "tactical_watchlist.csv", index=False)


def _write_filing_risk(
    reports: Path,
    symbol: str,
    gate_opinion: str = "PASS",
    fatal_risk: str = "NO",
) -> None:
    path = reports / "filing_review"
    path.mkdir(parents=True, exist_ok=True)
    code = symbol.split(".")[0]
    pd.DataFrame(
        [
            {
                "symbol": symbol,
                "risk_id": "LOCAL",
                "risk_title": "local filing check",
                "fatal_risk": fatal_risk,
                "gate_opinion": gate_opinion,
                "monitoring_rule": "manual review",
            }
        ]
    ).to_csv(path / f"filing_risk_summary_{code}.csv", index=False)
