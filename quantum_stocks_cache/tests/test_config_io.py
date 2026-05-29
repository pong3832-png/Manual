from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.config import load_runtime_config
from quantum_trainer.io import load_price_csv, save_backtest_reports
from quantum_trainer.trend import run_dynamic_trend_backtest


def test_load_runtime_config_resolves_paths_inside_project() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        tmp_path = Path(tmp_dir)
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
                    "  cost_bps: 7.5",
                    "  periods_per_year: 252",
                    "sizing:",
                    "  enabled: true",
                    "  target_volatility: 0.12",
                    "  realized_vol_window: 20",
                    "  volatility_floor: 0.05",
                    "  max_position_weight: 0.60",
                    "  max_leverage: 1.00",
                    "portfolio:",
                    "  000660.KS: 0.6",
                    "  005380.KS: 0.4",
                ]
            ),
            encoding="utf-8",
        )

        runtime_config = load_runtime_config(config_path)

        assert runtime_config.prices_csv == tmp_path / "prices.csv"
        assert runtime_config.reports_dir == tmp_path / "reports"
        assert runtime_config.backtest.trend_window == 3
        assert runtime_config.backtest.cost_bps == 7.5
        assert runtime_config.sizing.target_volatility == 0.12
        assert runtime_config.sizing.max_position_weight == 0.60
        assert runtime_config.backtest.weights == {"000660.KS": 0.6, "005380.KS": 0.4}


def test_load_price_csv_and_write_reports() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        tmp_path = Path(tmp_dir)
        prices_csv = tmp_path / "prices.csv"
        prices_csv.write_text(
            "\n".join(
                [
                    "date,000660.KS,005380.KS",
                    "2026-01-01,100,200",
                    "2026-01-02,101,202",
                    "2026-01-05,102,204",
                    "2026-01-06,103,206",
                    "2026-01-07,104,208",
                    "2026-01-08,90,207",
                    "2026-01-09,80,206",
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
                    "portfolio:",
                    "  000660.KS: 1.0",
                ]
            ),
            encoding="utf-8",
        )

        runtime_config = load_runtime_config(config_path)
        prices = load_price_csv(runtime_config.prices_csv)
        result = run_dynamic_trend_backtest(prices, runtime_config.backtest)
        paths = save_backtest_reports(result, runtime_config.reports_dir)

        assert list(prices.columns) == ["000660.KS", "005380.KS"]
        assert isinstance(prices.index, pd.DatetimeIndex)
        assert paths["equity_curve"].exists()
        assert paths["position_matrix"].exists()
        assert paths["performance_summary"].exists()


def test_load_price_csv_can_keep_sparse_research_universe_rows() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        tmp_path = Path(tmp_dir)
        prices_csv = tmp_path / "prices.csv"
        prices_csv.write_text(
            "\n".join(
                [
                    "date,005930.KS,477850.KQ",
                    "2026-01-01,100,",
                    "2026-01-02,101,",
                    "2026-05-29,150,20",
                ]
            ),
            encoding="utf-8",
        )

        strict = load_price_csv(prices_csv)
        sparse = load_price_csv(prices_csv, drop_incomplete=False)

        assert len(strict) == 1
        assert len(sparse) == 3
        assert pd.isna(sparse.loc[pd.Timestamp("2026-01-01"), "477850.KQ"])
