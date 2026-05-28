from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.alpha_forecast import AlphaForecastConfig, run_alpha_forecast
from quantum_trainer.buy_timing import score_buy_timing
from quantum_trainer.features import build_feature_frame, build_forward_labels
from quantum_trainer.io import load_price_csv
from quantum_trainer.scripts_api import run_alpha_research


def _prices(rows: int = 130) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="B", name="date")
    return pd.DataFrame(
        {
            "000660.KS": [100.0 + i * 0.8 + ((i % 7) * 0.2) for i in range(rows)],
            "005380.KS": [200.0 + i * 0.2 - ((i % 11) * 0.1) for i in range(rows)],
        },
        index=dates,
    )


def test_build_feature_frame_outputs_expected_columns() -> None:
    features = build_feature_frame(_prices())

    assert {"symbol", "return_5d", "return_20d", "ma20_gap", "realized_vol_20d"}.issubset(
        features.columns
    )
    assert set(features["symbol"].unique()) == {"000660.KS", "005380.KS"}


def test_build_forward_labels_outputs_forward_return_and_upside() -> None:
    labels = build_forward_labels(_prices(), horizon=20)

    assert {"symbol", "forward_20d_return", "forward_20d_upside"}.issubset(labels.columns)
    assert labels["forward_20d_upside"].dropna().isin([0, 1]).all()


def test_run_alpha_forecast_outputs_expected_return_probability_and_diagnostics() -> None:
    forecast = run_alpha_forecast(
        prices=_prices(),
        config=AlphaForecastConfig(horizon=20, min_samples=20),
    )

    assert {"expected_20d_return", "upside_probability", "sample_count", "model_r2"}.issubset(
        forecast.columns
    )
    assert forecast["upside_probability"].between(0.01, 0.99).all()
    assert (forecast["sample_count"] >= 20).all()


def test_score_buy_timing_maps_forecasts_to_decisions() -> None:
    forecast = pd.DataFrame(
        {
            "expected_20d_return": [0.08, 0.02, -0.03],
            "upside_probability": [0.70, 0.52, 0.35],
            "sample_count": [100, 100, 100],
            "model_r2": [0.2, 0.1, 0.0],
        },
        index=pd.Index(["BUY", "WAIT", "AVOID"], name="symbol"),
    )

    scored = score_buy_timing(forecast)

    assert scored.loc["BUY", "decision"] == "BUY_READY"
    assert scored.loc["WAIT", "decision"] == "WAIT"
    assert scored.loc["AVOID", "decision"] == "AVOID"


def test_alpha_research_writes_csv_and_markdown_reports() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_path = root / "prices.csv"
        _prices().to_csv(prices_path, encoding="utf-8-sig", index_label="date")
        config_path = root / "portfolio.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "data:",
                    "  prices_csv: prices.csv",
                    "reports:",
                    "  output_dir: reports",
                    "strategy:",
                    "  trend_window: 20",
                    "  cost_bps: 5.0",
                    "  periods_per_year: 252",
                    "portfolio:",
                    "  000660.KS: 0.6",
                    "  005380.KS: 0.4",
                ]
            ),
            encoding="utf-8",
        )

        output = run_alpha_research(config_path=config_path)
        report = load_price_csv(prices_path)

        assert report.shape[1] == 2
        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert "buy_timing_score" in output.csv_path.read_text(encoding="utf-8-sig")
