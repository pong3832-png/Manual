from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.institutional_program_stack import (
    load_institutional_program_stack,
    rank_institutional_program_stack,
    run_institutional_program_stack,
    summarize_institutional_program_stack,
)


def _stack() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "program_id": "P2_EXECUTION",
                "priority": "P2",
                "program_category": "Execution management system",
                "public_reference": "FlexTRADER EMS",
                "source_url": "https://s44885.pcdn.co/products/flextrader-execution-management-system/",
                "institutional_capability": "broker-neutral execution workflow",
                "our_current_coverage": "none",
                "local_apply_module": "execution_risk_review",
                "required_local_inputs": "reports/orders",
                "blocked_capabilities": "broker connectivity",
                "implementation_status": "RESEARCH_BACKLOG",
                "validation_gate": "no order route exists",
                "next_step": "Add execution risk notes",
                "external_api_requested": "YES",
                "order_status": "SEND_ORDER",
                "broker_order_requested": "YES",
            },
            {
                "program_id": "P0_RISK",
                "priority": "P0",
                "program_category": "Factor risk model",
                "public_reference": "MSCI Barra PortfolioManager",
                "source_url": "https://www.msci.com/data-and-analytics/portfolio-management/barra-portfolio-manager",
                "institutional_capability": "risk decomposition and attribution",
                "our_current_coverage": "partial",
                "local_apply_module": "factor_risk_exposure",
                "required_local_inputs": "company_research; prices",
                "blocked_capabilities": "proprietary risk model",
                "implementation_status": "READY_FOR_SPEC",
                "validation_gate": "factor exposure report exists",
                "next_step": "Create factor exposure report",
                "external_api_requested": "NO",
                "order_status": "NO_ORDER",
                "broker_order_requested": "NO",
            },
        ]
    )


def test_load_institutional_program_stack_forces_no_order_safety_fields() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        path = Path(tmp_dir) / "stack.csv"
        _stack().to_csv(path, index=False)

        loaded = load_institutional_program_stack(path)

        assert set(loaded["external_api_requested"]) == {"NO"}
        assert set(loaded["order_status"]) == {"NO_ORDER"}
        assert set(loaded["broker_order_requested"]) == {"NO"}


def test_rank_institutional_program_stack_prioritizes_ready_p0_items() -> None:
    ranked = rank_institutional_program_stack(_stack())

    assert ranked.iloc[0]["program_id"] == "P0_RISK"
    assert ranked.iloc[0]["rank"] == 1
    assert ranked.iloc[1]["priority"] == "P2"


def test_summarize_institutional_program_stack_counts_priorities_and_status() -> None:
    ranked = rank_institutional_program_stack(_stack())
    summary = summarize_institutional_program_stack(ranked)

    row = summary.iloc[0]
    assert int(row["row_count"]) == 2
    assert int(row["p0_count"]) == 1
    assert int(row["p2_count"]) == 1
    assert int(row["ready_for_spec_count"]) == 1
    assert row["order_status"] == "NO_ORDER"


def test_run_institutional_program_stack_writes_reports() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        stack_csv = root / "stack.csv"
        _stack().to_csv(stack_csv, index=False)

        output = run_institutional_program_stack(
            stack_csv=stack_csv,
            output_dir=root / "reports",
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary_path.exists()
        assert int(output.summary.iloc[0]["row_count"]) == 2
        assert set(output.report["order_status"]) == {"NO_ORDER"}
        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Institutional Program Stack" in markdown
        assert "P0_RISK" in markdown
        assert "NO_ORDER" in markdown
