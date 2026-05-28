from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quantum_trainer.alpha_forecast import AlphaForecastConfig, run_alpha_forecast
from quantum_trainer.buy_timing import score_buy_timing
from quantum_trainer.config import load_runtime_config
from quantum_trainer.io import load_price_csv

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlphaResearchOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    rows = frame.astype(str).values.tolist()
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def run_alpha_research(config_path: Path | str) -> AlphaResearchOutput:
    try:
        runtime_config = load_runtime_config(config_path)
        prices = load_price_csv(runtime_config.prices_csv)
        forecast = run_alpha_forecast(prices, AlphaForecastConfig())
        report = score_buy_timing(forecast)

        output_dir = runtime_config.reports_dir / "alpha"
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "buy_timing_report.csv"
        markdown_path = output_dir / "buy_timing_report.md"
        report.to_csv(csv_path, encoding="utf-8-sig")
        markdown = "\n".join(
            [
                "# Alpha Forecast Buy Timing Report",
                "",
                _markdown_table(report.reset_index()),
                "",
            ]
        )
        markdown_path.write_text(markdown, encoding="utf-8")
        return AlphaResearchOutput(csv_path=csv_path, markdown_path=markdown_path, report=report)
    except Exception as exc:
        logger.exception("Alpha research run failed: %s", exc)
        raise
