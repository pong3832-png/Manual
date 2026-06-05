from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.learning_feedback import (
    LearningFeedbackConfig,
    build_prediction_snapshot,
    evaluate_realized_outcomes,
    merge_prediction_snapshots,
    run_learning_feedback,
    summarize_learning_feedback,
)


def _prices(rows: int = 50) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="B", name="date")
    return pd.DataFrame(
        {
            "000660.KS": [100.0 + i for i in range(rows)],
            "005380.KS": [200.0 - i * 0.5 for i in range(rows)],
        },
        index=dates,
    )


def _forecast() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["000660.KS", "005380.KS"],
            "expected_20d_return": [0.10, -0.05],
            "upside_probability": [0.70, 0.35],
            "buy_timing_score": [80.0, 25.0],
            "decision": ["BUY_READY", "AVOID"],
            "sample_count": [120, 120],
            "model_r2": [0.2, 0.1],
        }
    )


def test_prediction_snapshot_keeps_no_order_safety_fields() -> None:
    snapshot = build_prediction_snapshot(
        forecast=_forecast(),
        prediction_date=pd.Timestamp("2026-01-05"),
        source_report=Path("reports/alpha/buy_timing_report.csv"),
    )

    assert set(snapshot["order_status"]) == {"NO_ORDER"}
    assert set(snapshot["broker_order_requested"]) == {"NO"}
    assert set(snapshot["decision"]) == {"BUY_READY", "AVOID"}


def test_realized_outcomes_measure_forecast_error_after_horizon() -> None:
    snapshot = build_prediction_snapshot(
        forecast=_forecast(),
        prediction_date=pd.Timestamp("2026-01-01"),
        source_report=Path("reports/alpha/buy_timing_report.csv"),
    )

    outcomes = evaluate_realized_outcomes(
        snapshots=snapshot,
        prices=_prices(),
        config=LearningFeedbackConfig(horizon=20, min_realized_samples=1),
    )
    summary = summarize_learning_feedback(
        outcomes=outcomes,
        as_of=pd.Timestamp("2026-03-11"),
        config=LearningFeedbackConfig(horizon=20, min_realized_samples=1),
    )

    assert set(outcomes["status"]) == {"REALIZED"}
    assert outcomes["direction_correct"].astype(int).tolist() == [1, 1]
    assert float(summary.loc[0, "directional_accuracy"]) == 1.0
    assert summary.loc[0, "order_status"] == "NO_ORDER"


def test_merge_prediction_snapshots_deduplicates_same_symbol_date_source() -> None:
    first = build_prediction_snapshot(
        forecast=_forecast(),
        prediction_date=pd.Timestamp("2026-01-01"),
        source_report=Path("reports/alpha/buy_timing_report.csv"),
    )
    second = first.copy()
    second.loc[second["symbol"] == "000660.KS", "expected_20d_return"] = 0.15

    merged = merge_prediction_snapshots(first, second)

    assert len(merged) == 2
    updated = merged[merged["symbol"] == "000660.KS"].iloc[0]
    assert float(updated["expected_20d_return"]) == 0.15


def test_run_learning_feedback_writes_snapshot_outcome_summary_reports() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_path = root / "prices.csv"
        _prices().to_csv(prices_path, encoding="utf-8-sig", index_label="date")
        forecast_path = root / "forecast.csv"
        _forecast().to_csv(forecast_path, encoding="utf-8-sig", index=False)
        snapshot_path = root / "snapshots.csv"
        build_prediction_snapshot(
            forecast=_forecast(),
            prediction_date=pd.Timestamp("2026-01-01"),
            source_report=forecast_path,
        ).to_csv(snapshot_path, encoding="utf-8-sig", index=False)
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

        output = run_learning_feedback(
            config_path=config_path,
            forecast_csv=forecast_path,
            snapshot_csv=snapshot_path,
            output_dir=root / "reports" / "learning_feedback",
            feedback_config=LearningFeedbackConfig(horizon=20, min_realized_samples=1),
        )

        assert output.snapshot_path.exists()
        assert output.outcomes_path.exists()
        assert output.summary_path.exists()
        assert output.markdown_path.exists()
        assert int(output.summary.loc[0, "realized_count"]) == 2
        assert set(output.summary["external_api_requested"]) == {"NO"}
