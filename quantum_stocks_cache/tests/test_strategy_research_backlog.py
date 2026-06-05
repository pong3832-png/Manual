from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.strategy_research_backlog import (
    load_strategy_research_backlog,
    rank_strategy_research_backlog,
    run_strategy_research_backlog,
    summarize_strategy_research_backlog,
)


def _backlog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "research_id": "P2_BOOK",
                "priority": "P2",
                "theme": "Portfolio construction",
                "source_type": "book",
                "source_title": "Active Portfolio Management",
                "authors": "Grinold; Kahn",
                "year": 1999,
                "source_url": "https://books.google.com/books?id=aSDkFQtysy8C",
                "local_feature_module": "order_sizer",
                "required_local_inputs": "reports/pre_buy_decision",
                "blocked_external_inputs": "broker execution",
                "implementation_status": "RESEARCH_BACKLOG",
                "validation_gate": "risk budget review",
                "promotion_rule": "manual gates first",
                "korea_market_note": "review only",
                "next_step": "Add sizing confidence bucket",
                "external_api_requested": "YES",
                "order_status": "BUY",
                "broker_order_requested": "YES",
            },
            {
                "research_id": "P0_KR_FACTOR",
                "priority": "P0",
                "theme": "Korea factor investing",
                "source_type": "paper",
                "source_title": "Enhanced factor investing in the Korean stock market",
                "authors": "Kim et al.",
                "year": 2021,
                "source_url": "https://www.sciencedirect.com/science/article/pii/S0927538X21000652",
                "local_feature_module": "factor_score",
                "required_local_inputs": "fundamentals; prices",
                "blocked_external_inputs": "OpenDART refresh",
                "implementation_status": "RESEARCH_BACKLOG",
                "validation_gate": "walk-forward rank spread",
                "promotion_rule": "beat trend score",
                "korea_market_note": "long-only matters",
                "next_step": "Create factor score",
                "external_api_requested": "NO",
                "order_status": "NO_ORDER",
                "broker_order_requested": "NO",
            },
        ]
    )


def test_load_strategy_research_backlog_forces_review_only_safety_fields() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        path = Path(tmp_dir) / "backlog.csv"
        _backlog().to_csv(path, index=False)

        loaded = load_strategy_research_backlog(path)

        assert set(loaded["external_api_requested"]) == {"NO"}
        assert set(loaded["order_status"]) == {"NO_ORDER"}
        assert set(loaded["broker_order_requested"]) == {"NO"}


def test_rank_strategy_research_backlog_prioritizes_p0_items() -> None:
    ranked = rank_strategy_research_backlog(_backlog())

    assert ranked.iloc[0]["research_id"] == "P0_KR_FACTOR"
    assert ranked.iloc[0]["rank"] == 1
    assert ranked.iloc[1]["priority"] == "P2"


def test_summarize_strategy_research_backlog_counts_priorities_and_statuses() -> None:
    ranked = rank_strategy_research_backlog(_backlog())
    summary = summarize_strategy_research_backlog(ranked)

    row = summary.iloc[0]
    assert int(row["row_count"]) == 2
    assert int(row["p0_count"]) == 1
    assert int(row["p2_count"]) == 1
    assert int(row["research_backlog_count"]) == 2
    assert row["order_status"] == "NO_ORDER"


def test_run_strategy_research_backlog_writes_csv_markdown_and_summary() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        backlog_csv = root / "backlog.csv"
        _backlog().to_csv(backlog_csv, index=False)

        output = run_strategy_research_backlog(
            backlog_csv=backlog_csv,
            output_dir=root / "reports",
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary_path.exists()
        assert int(output.summary.iloc[0]["row_count"]) == 2
        assert set(output.report["order_status"]) == {"NO_ORDER"}
        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Strategy Research Backlog" in markdown
        assert "P0_KR_FACTOR" in markdown
        assert "NO_ORDER" in markdown
