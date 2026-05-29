from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from quantum_trainer.trend import BacktestResult

logger = logging.getLogger(__name__)


def load_price_csv(path: Path | str, drop_incomplete: bool = True) -> pd.DataFrame:
    try:
        csv_path = Path(path).resolve()
        if not csv_path.exists():
            raise FileNotFoundError(f"Price CSV not found: {csv_path}")

        df = pd.read_csv(csv_path)
        if "date" not in df.columns:
            raise ValueError("Price CSV must include a 'date' column.")

        df["date"] = pd.to_datetime(df["date"], errors="raise")
        prices = df.set_index("date").sort_index()
        if prices.empty or len(prices.columns) == 0:
            raise ValueError("Price CSV must include at least one price column.")

        drop_mode = "any" if drop_incomplete else "all"
        prices = prices.apply(pd.to_numeric, errors="coerce").ffill().dropna(how=drop_mode)
        if prices.empty:
            raise ValueError("Price data became empty after numeric conversion.")
        return prices
    except Exception as exc:
        logger.exception("Failed to load price CSV: %s", exc)
        raise


def save_backtest_reports(result: BacktestResult, reports_dir: Path | str) -> dict[str, Path]:
    try:
        output_dir = Path(reports_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = {
            "equity_curve": output_dir / "equity_curve.csv",
            "position_matrix": output_dir / "position_matrix.csv",
            "signal_matrix": output_dir / "signal_matrix.csv",
            "performance_summary": output_dir / "performance_summary.csv",
        }

        result.equity_curve.to_csv(paths["equity_curve"], encoding="utf-8-sig")
        result.positions.to_csv(paths["position_matrix"], encoding="utf-8-sig")
        result.signals.to_csv(paths["signal_matrix"], encoding="utf-8-sig")
        result.performance_summary.to_csv(paths["performance_summary"], encoding="utf-8-sig")
        return paths
    except Exception as exc:
        logger.exception("Failed to save backtest reports: %s", exc)
        raise
