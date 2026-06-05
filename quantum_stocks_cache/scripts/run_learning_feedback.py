from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.learning_feedback import LearningFeedbackConfig, run_learning_feedback

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append alpha prediction snapshots and evaluate realized forecast error."
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
        help="Path to portfolio YAML config.",
    )
    parser.add_argument(
        "--forecast-csv",
        default=None,
        help="Alpha forecast CSV. Defaults to reports/alpha/buy_timing_report.csv.",
    )
    parser.add_argument(
        "--snapshot-csv",
        default=None,
        help="Prediction snapshot CSV. Defaults to reports/learning_feedback/alpha_prediction_snapshots.csv.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Learning feedback report directory. Defaults to reports/learning_feedback.",
    )
    parser.add_argument("--horizon", type=int, default=20, help="Forward trading-day horizon.")
    parser.add_argument(
        "--min-realized-samples",
        type=int,
        default=20,
        help="Minimum realized samples before recommending feature/threshold changes.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_learning_feedback(
            config_path=Path(args.config),
            forecast_csv=Path(args.forecast_csv) if args.forecast_csv else None,
            snapshot_csv=Path(args.snapshot_csv) if args.snapshot_csv else None,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            feedback_config=LearningFeedbackConfig(
                horizon=args.horizon,
                min_realized_samples=args.min_realized_samples,
            ),
        )
        logger.info("Learning feedback complete.")
        logger.info("Snapshots: %s", output.snapshot_path)
        logger.info("Outcomes: %s", output.outcomes_path)
        logger.info("Summary: %s", output.summary_path)
        print(output.summary.to_string(index=False))
        return 0
    except Exception as exc:
        logger.exception("Learning feedback failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
