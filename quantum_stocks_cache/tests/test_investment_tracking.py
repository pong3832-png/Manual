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


def test_investment_tracking_calculates_pnl_and_review_dates_without_orders() -> None:
    module = importlib.import_module("quantum_trainer.investment_tracking")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        journal_csv = root / "trade_journal.actual.csv"
        prices_csv = root / "prices.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG",
                    "buy_date": "2026-05-28",
                    "buy_price": 116000,
                    "shares": 5,
                    "thesis": "지주 가치 재평가와 배당 매력",
                    "stop_loss_rule": "-7% 손실 또는 thesis 훼손 시 축소",
                    "thesis_status": "INTACT",
                }
            ]
        ).to_csv(journal_csv, index=False)
        pd.DataFrame(
            [
                {"date": "2026-05-28", "003550.KS": 116000},
                {"date": "2026-06-04", "003550.KS": 121800},
            ]
        ).to_csv(prices_csv, index=False)

        output = module.run_investment_tracking(
            trade_journal_csv=journal_csv,
            prices_csv=prices_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["tracked_positions"] == 1
        assert output.summary["order_status"] == "NO_ORDER"

        row = output.report.iloc[0]
        assert row["tracking_status"] == "TRACKING_ACTIVE"
        assert row["latest_price_date"] == "2026-06-04"
        assert row["invested_value"] == 580000
        assert row["current_value"] == 609000
        assert row["unrealized_pnl"] == 29000
        assert round(float(row["unrealized_return"]), 4) == 0.05
        assert row["one_week_check_date"] == "2026-06-04"
        assert row["one_month_check_date"] == "2026-06-28"
        assert row["quarter_check_date"] == "2026-08-28"
        assert row["one_week_due"] == "YES"
        assert row["one_month_due"] == "NO"
        assert row["review_action"] == "ONE_WEEK_REVIEW_DUE"
        assert row["order_status"] == "NO_ORDER"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "실제 주문을 실행하지 않습니다" in markdown
        assert "003550.KS" in markdown


def test_investment_tracking_handles_missing_journal_as_not_started() -> None:
    module = importlib.import_module("quantum_trainer.investment_tracking")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_csv = root / "prices.csv"
        pd.DataFrame([{"date": "2026-06-04", "003550.KS": 121800}]).to_csv(prices_csv, index=False)

        output = module.run_investment_tracking(
            trade_journal_csv=root / "trade_journal.actual.csv",
            prices_csv=prices_csv,
            output_dir=root / "reports",
        )

        row = output.report.iloc[0]
        assert row["tracking_status"] == "NO_TRADE_JOURNAL"
        assert row["order_status"] == "NO_ORDER"
        assert output.summary["tracked_positions"] == 0
