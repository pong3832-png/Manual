from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from quantum_trainer.config import load_runtime_config
from quantum_trainer.io import load_price_csv

logger = logging.getLogger(__name__)


SNAPSHOT_COLUMNS = [
    "prediction_date",
    "symbol",
    "expected_20d_return",
    "upside_probability",
    "buy_timing_score",
    "decision",
    "sample_count",
    "model_r2",
    "source_report",
    "order_status",
    "broker_order_requested",
]

OUTCOME_COLUMNS = [
    "prediction_date",
    "outcome_date",
    "symbol",
    "expected_20d_return",
    "realized_20d_return",
    "forecast_error",
    "absolute_error",
    "predicted_upside",
    "realized_upside",
    "direction_correct",
    "decision",
    "status",
    "order_status",
    "broker_order_requested",
]


@dataclass(frozen=True)
class LearningFeedbackConfig:
    horizon: int = 20
    min_realized_samples: int = 20
    min_directional_accuracy: float = 0.52
    max_mae: float = 0.08


@dataclass(frozen=True)
class LearningFeedbackOutput:
    snapshot_path: Path
    outcomes_path: Path
    summary_path: Path
    markdown_path: Path
    snapshots: pd.DataFrame
    outcomes: pd.DataFrame
    summary: pd.DataFrame


def _read_forecast(path: Path | str) -> pd.DataFrame:
    forecast_path = Path(path)
    forecast = pd.read_csv(forecast_path)
    if "symbol" not in forecast.columns:
        first_column = str(forecast.columns[0])
        forecast = forecast.rename(columns={first_column: "symbol"})
    required = {"symbol", "expected_20d_return", "upside_probability"}
    missing = required.difference(forecast.columns)
    if missing:
        raise ValueError(f"Forecast report missing required columns: {sorted(missing)}")
    return forecast


def build_prediction_snapshot(
    forecast: pd.DataFrame,
    prediction_date: pd.Timestamp,
    source_report: Path | str,
) -> pd.DataFrame:
    rows = forecast.copy()
    rows["prediction_date"] = pd.Timestamp(prediction_date).date().isoformat()
    rows["source_report"] = str(Path(source_report))
    rows["order_status"] = "NO_ORDER"
    rows["broker_order_requested"] = "NO"
    for column, default in {
        "buy_timing_score": 0.0,
        "decision": "UNKNOWN",
        "sample_count": 0,
        "model_r2": 0.0,
    }.items():
        if column not in rows.columns:
            rows[column] = default
    return rows[SNAPSHOT_COLUMNS].copy()


def merge_prediction_snapshots(existing: pd.DataFrame, new_snapshot: pd.DataFrame) -> pd.DataFrame:
    if existing.empty:
        combined = new_snapshot.copy()
    else:
        combined = pd.concat([existing, new_snapshot], ignore_index=True)
    combined["prediction_date"] = pd.to_datetime(combined["prediction_date"]).dt.date.astype(str)
    return (
        combined.drop_duplicates(
            subset=["prediction_date", "symbol", "source_report"],
            keep="last",
        )
        .sort_values(["prediction_date", "symbol"])
        .reset_index(drop=True)
    )


def _position_on_or_before(index: pd.DatetimeIndex, date: pd.Timestamp) -> int | None:
    position = int(index.searchsorted(pd.Timestamp(date), side="right")) - 1
    if position < 0:
        return None
    return position


def evaluate_realized_outcomes(
    snapshots: pd.DataFrame,
    prices: pd.DataFrame,
    config: LearningFeedbackConfig | None = None,
) -> pd.DataFrame:
    config = config or LearningFeedbackConfig()
    if snapshots.empty:
        return pd.DataFrame(columns=OUTCOME_COLUMNS)

    price_index = pd.DatetimeIndex(prices.index).sort_values()
    sorted_prices = prices.reindex(price_index)
    rows: list[dict[str, object]] = []
    for _, snapshot in snapshots.iterrows():
        symbol = str(snapshot["symbol"])
        prediction_date = pd.Timestamp(snapshot["prediction_date"])
        start_position = _position_on_or_before(price_index, prediction_date)
        base = {
            "prediction_date": prediction_date.date().isoformat(),
            "outcome_date": "",
            "symbol": symbol,
            "expected_20d_return": float(snapshot.get("expected_20d_return", 0.0)),
            "realized_20d_return": np.nan,
            "forecast_error": np.nan,
            "absolute_error": np.nan,
            "predicted_upside": int(float(snapshot.get("expected_20d_return", 0.0)) > 0.0),
            "realized_upside": "",
            "direction_correct": "",
            "decision": str(snapshot.get("decision", "UNKNOWN")),
            "status": "PENDING",
            "order_status": "NO_ORDER",
            "broker_order_requested": "NO",
        }
        if symbol not in sorted_prices.columns or start_position is None:
            base["status"] = "DATA_REQUIRED"
            rows.append(base)
            continue
        outcome_position = start_position + config.horizon
        if outcome_position >= len(sorted_prices.index):
            rows.append(base)
            continue
        start_price = sorted_prices.iloc[start_position][symbol]
        outcome_price = sorted_prices.iloc[outcome_position][symbol]
        if pd.isna(start_price) or pd.isna(outcome_price) or float(start_price) == 0.0:
            base["status"] = "DATA_REQUIRED"
            rows.append(base)
            continue
        realized = float(outcome_price / start_price - 1.0)
        error = realized - float(base["expected_20d_return"])
        realized_upside = int(realized > 0.0)
        base.update(
            {
                "outcome_date": sorted_prices.index[outcome_position].date().isoformat(),
                "realized_20d_return": realized,
                "forecast_error": error,
                "absolute_error": abs(error),
                "realized_upside": realized_upside,
                "direction_correct": int(realized_upside == int(base["predicted_upside"])),
                "status": "REALIZED",
            }
        )
        rows.append(base)
    return pd.DataFrame(rows, columns=OUTCOME_COLUMNS)


def summarize_learning_feedback(
    outcomes: pd.DataFrame,
    as_of: pd.Timestamp,
    config: LearningFeedbackConfig | None = None,
) -> pd.DataFrame:
    config = config or LearningFeedbackConfig()
    if outcomes.empty:
        realized = outcomes.copy()
    else:
        realized = outcomes[outcomes["status"] == "REALIZED"].copy()
    snapshot_count = int(len(outcomes))
    matured_count = int(len(realized))
    pending_count = int((outcomes["status"] == "PENDING").sum()) if not outcomes.empty else 0
    data_required_count = int((outcomes["status"] == "DATA_REQUIRED").sum()) if not outcomes.empty else 0

    if matured_count == 0:
        mae = rmse = bias = directional_accuracy = np.nan
        buy_ready_directional_accuracy = np.nan
    else:
        errors = realized["forecast_error"].astype(float)
        mae = float(realized["absolute_error"].astype(float).mean())
        rmse = float(np.sqrt(np.mean(np.square(errors))))
        bias = float(errors.mean())
        directional_accuracy = float(realized["direction_correct"].astype(int).mean())
        buy_ready = realized[realized["decision"] == "BUY_READY"]
        buy_ready_directional_accuracy = (
            float(buy_ready["direction_correct"].astype(int).mean()) if not buy_ready.empty else np.nan
        )

    if matured_count < config.min_realized_samples:
        action = "WAIT_FOR_MORE_REALIZED_SAMPLES"
    elif directional_accuracy < config.min_directional_accuracy or mae > config.max_mae:
        action = "REVIEW_FEATURES_AND_THRESHOLDS"
    else:
        action = "KEEP_MODEL"

    return pd.DataFrame(
        [
            {
                "as_of": pd.Timestamp(as_of).date().isoformat(),
                "horizon": config.horizon,
                "snapshot_count": snapshot_count,
                "realized_count": matured_count,
                "pending_count": pending_count,
                "data_required_count": data_required_count,
                "mae": mae,
                "rmse": rmse,
                "bias": bias,
                "directional_accuracy": directional_accuracy,
                "buy_ready_count": int((realized["decision"] == "BUY_READY").sum()) if matured_count else 0,
                "buy_ready_directional_accuracy": buy_ready_directional_accuracy,
                "learning_action": action,
                "external_api_requested": "NO",
                "order_status": "NO_ORDER",
                "broker_order_requested": "NO",
            }
        ]
    )


def _markdown_summary(summary: pd.DataFrame, outcomes: pd.DataFrame) -> str:
    row = summary.iloc[0].to_dict()
    realized = outcomes[outcomes["status"] == "REALIZED"].copy() if not outcomes.empty else outcomes
    lines = [
        "# Learning Feedback Report",
        "",
        f"- as_of: {row['as_of']}",
        f"- horizon: {row['horizon']} trading days",
        f"- snapshots: {row['snapshot_count']}",
        f"- realized: {row['realized_count']}",
        f"- pending: {row['pending_count']}",
        f"- data_required: {row['data_required_count']}",
        f"- mae: {row['mae']}",
        f"- directional_accuracy: {row['directional_accuracy']}",
        f"- learning_action: {row['learning_action']}",
        f"- external_api_requested: {row['external_api_requested']}",
        f"- order_status: {row['order_status']}",
        "",
        "## Recent Realized Outcomes",
        "",
    ]
    if realized.empty:
        lines.append("No realized outcomes yet. Keep collecting prediction snapshots.")
    else:
        preview = realized.sort_values(["prediction_date", "symbol"]).tail(20)
        columns = [str(column) for column in preview.columns]
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        body = ["| " + " | ".join(row) + " |" for row in preview.astype(str).values.tolist()]
        lines.extend([header, separator, *body])
    lines.append("")
    return "\n".join(lines)


def run_learning_feedback(
    config_path: Path | str,
    forecast_csv: Path | str | None = None,
    snapshot_csv: Path | str | None = None,
    output_dir: Path | str | None = None,
    feedback_config: LearningFeedbackConfig | None = None,
) -> LearningFeedbackOutput:
    try:
        feedback_config = feedback_config or LearningFeedbackConfig()
        runtime_config = load_runtime_config(config_path)
        prices = load_price_csv(runtime_config.prices_csv, drop_incomplete=False)
        as_of = pd.Timestamp(prices.index.max())

        target_output_dir = Path(output_dir) if output_dir else runtime_config.reports_dir / "learning_feedback"
        target_output_dir.mkdir(parents=True, exist_ok=True)
        target_forecast_csv = Path(forecast_csv) if forecast_csv else runtime_config.reports_dir / "alpha" / "buy_timing_report.csv"
        target_snapshot_csv = (
            Path(snapshot_csv)
            if snapshot_csv
            else target_output_dir / "alpha_prediction_snapshots.csv"
        )
        outcomes_path = target_output_dir / "alpha_prediction_outcomes.csv"
        summary_path = target_output_dir / "learning_feedback_summary.csv"
        markdown_path = target_output_dir / "learning_feedback.md"

        forecast = _read_forecast(target_forecast_csv)
        new_snapshot = build_prediction_snapshot(forecast, as_of, target_forecast_csv)
        if target_snapshot_csv.exists():
            existing = pd.read_csv(target_snapshot_csv)
        else:
            existing = pd.DataFrame(columns=SNAPSHOT_COLUMNS)
        snapshots = merge_prediction_snapshots(existing, new_snapshot)
        outcomes = evaluate_realized_outcomes(snapshots, prices, feedback_config)
        summary = summarize_learning_feedback(outcomes, as_of, feedback_config)

        snapshots.to_csv(target_snapshot_csv, encoding="utf-8-sig", index=False)
        outcomes.to_csv(outcomes_path, encoding="utf-8-sig", index=False)
        summary.to_csv(summary_path, encoding="utf-8-sig", index=False)
        markdown_path.write_text(_markdown_summary(summary, outcomes), encoding="utf-8")

        return LearningFeedbackOutput(
            snapshot_path=target_snapshot_csv,
            outcomes_path=outcomes_path,
            summary_path=summary_path,
            markdown_path=markdown_path,
            snapshots=snapshots,
            outcomes=outcomes,
            summary=summary,
        )
    except Exception as exc:
        logger.exception("Learning feedback run failed: %s", exc)
        raise
