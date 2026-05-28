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


def test_capital_scenarios_show_split_buy_shares_without_orders() -> None:
    module = importlib.import_module("quantum_trainer.capital_scenario")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        checklist_csv = root / "investment_checklist.csv"
        prices_csv = root / "prices.csv"
        capital_plan_dir = root / "decision_gate"
        output_dir = root / "reports"
        capital_plan_dir.mkdir()

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "research_score": 75.2,
                    "decision": "BUY_READY",
                },
                {
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "checklist_status": "NEEDS_MANUAL_REVIEW",
                    "automatic_blockers": "밸류에이션 부담",
                    "research_score": 87.5,
                    "decision": "BUY_READY",
                },
            ]
        ).to_csv(checklist_csv, index=False)
        pd.DataFrame([{"date": "2026-05-28", "003550.KS": 116_500, "005930.KS": 80_000}]).to_csv(
            prices_csv, index=False
        )
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
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
        ).to_csv(capital_plan_dir / "capital_plan_review_003550.csv", index=False)

        output = module.run_capital_scenarios(
            candidate_checklist_csv=checklist_csv,
            prices_csv=prices_csv,
            capital_plan_dir=capital_plan_dir,
            output_dir=output_dir,
            scenario_capitals=(1_000_000, 3_000_000),
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["scenario_count"] == 2
        assert output.summary["order_status"] == "NO_ORDER"
        assert list(output.report["symbol"].unique()) == ["003550.KS"]

        one_m = output.report.loc[output.report["scenario_capital"] == 1_000_000].iloc[0]
        assert one_m["scenario_status"] == "INSUFFICIENT_FOR_FIRST_TRANCHE"
        assert one_m["target_position_value"] == 150_000
        assert one_m["first_tranche_value"] == 45_000
        assert one_m["first_tranche_shares"] == 0
        assert one_m["target_position_shares"] == 1
        assert one_m["order_status"] == "NO_ORDER"

        three_m = output.report.loc[output.report["scenario_capital"] == 3_000_000].iloc[0]
        assert three_m["scenario_status"] == "SCENARIO_REVIEW_ONLY"
        assert three_m["target_position_value"] == 450_000
        assert three_m["first_tranche_value"] == 135_000
        assert three_m["first_tranche_shares"] == 1
        assert three_m["target_position_shares"] == 3
        assert three_m["execution_mode"] == "MANUAL_REVIEW_ONLY"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Capital Scenarios" in markdown
        assert "실제 주문 실행 문서가 아닙니다" in markdown
        assert "SCENARIO_REVIEW_ONLY" in markdown
