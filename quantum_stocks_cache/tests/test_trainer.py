from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.trainer import run_daily_trainer


def test_daily_trainer_writes_trade_plan_and_decision_report() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        tmp_path = Path(tmp_dir)
        prices_csv = tmp_path / "prices.csv"
        prices_csv.write_text(
            "\n".join(
                [
                    "date,000660.KS",
                    "2026-01-01,10",
                    "2026-01-02,11",
                    "2026-01-05,12",
                    "2026-01-06,13",
                    "2026-01-07,14",
                    "2026-01-08,13",
                    "2026-01-09,12",
                    "2026-01-12,11",
                ]
            ),
            encoding="utf-8",
        )
        config_path = tmp_path / "portfolio.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "data:",
                    "  prices_csv: prices.csv",
                    "reports:",
                    "  output_dir: reports",
                    "strategy:",
                    "  trend_window: 3",
                    "  cost_bps: 0.0",
                    "  periods_per_year: 252",
                    "risk:",
                    "  max_portfolio_mdd: -0.12",
                    "  max_daily_turnover: 1.0",
                    "  max_cash_exposure: 1.0",
                    "portfolio:",
                    "  000660.KS: 1.0",
                    "current_weights:",
                    "  000660.KS: 1.0",
                ]
            ),
            encoding="utf-8",
        )

        output = run_daily_trainer(config_path=config_path, as_of=date(2026, 1, 12))

        assert output.trade_plan_path == tmp_path / "reports" / "daily" / "2026-01-12_trade_plan.csv"
        assert output.decision_report_path == tmp_path / "reports" / "daily" / "2026-01-12_decision_report.md"
        assert output.sizing_diagnostics_path == tmp_path / "reports" / "daily" / "2026-01-12_sizing_diagnostics.csv"
        assert output.trade_plan_path.exists()
        assert output.decision_report_path.exists()
        assert output.sizing_diagnostics_path.exists()
        assert "SELL_TO_CASH" in output.trade_plan_path.read_text(encoding="utf-8-sig")
        assert "Risk Gate" in output.decision_report_path.read_text(encoding="utf-8")
