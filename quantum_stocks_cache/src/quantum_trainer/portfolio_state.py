from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd
import yaml

from quantum_trainer.config import load_runtime_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CurrentWeightsCheckResult:
    status: str
    report: pd.DataFrame
    csv_path: Path
    markdown_path: Path
    config_updated: bool


def load_current_weights_csv(path: Path | str) -> dict[str, float]:
    csv_path = Path(path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"Current weights CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required_columns = {"symbol", "current_weight"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Current weights CSV missing required columns: {missing}")
    if df.empty:
        raise ValueError("Current weights CSV must include at least one row.")

    normalized = df.loc[:, ["symbol", "current_weight"]].copy()
    normalized["symbol"] = normalized["symbol"].astype(str).str.strip()
    if (normalized["symbol"] == "").any():
        raise ValueError("Current weights CSV contains an empty symbol.")
    if normalized["symbol"].duplicated().any():
        duplicates = normalized.loc[normalized["symbol"].duplicated(), "symbol"].tolist()
        raise ValueError(f"Current weights CSV contains duplicate symbols: {duplicates}")

    normalized["current_weight"] = pd.to_numeric(
        normalized["current_weight"], errors="coerce"
    )
    if normalized["current_weight"].isna().any():
        raise ValueError("Current weights CSV contains non-numeric current_weight values.")
    if (normalized["current_weight"] < 0).any():
        raise ValueError("Current weights CSV contains negative current_weight values.")

    return {
        str(row.symbol): float(row.current_weight)
        for row in normalized.itertuples(index=False)
    }


def compare_current_weights(
    config_weights: Mapping[str, float],
    actual_weights: Mapping[str, float],
    threshold: float,
) -> pd.DataFrame:
    if threshold < 0:
        raise ValueError("threshold must be greater than or equal to 0.")

    symbols = list(config_weights.keys())
    symbols.extend(symbol for symbol in actual_weights.keys() if symbol not in config_weights)

    rows: list[dict[str, object]] = []
    for symbol in symbols:
        config_weight = float(config_weights.get(symbol, 0.0))
        actual_weight = float(actual_weights.get(symbol, 0.0))
        diff = round(actual_weight - config_weight, 10)
        abs_diff = round(abs(diff), 10)
        rows.append(
            {
                "symbol": symbol,
                "config_weight": config_weight,
                "actual_weight": actual_weight,
                "diff": diff,
                "abs_diff": abs_diff,
                "threshold": float(threshold),
                "status": "WARN" if abs_diff >= threshold else "OK",
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "symbol",
            "config_weight",
            "actual_weight",
            "diff",
            "abs_diff",
            "threshold",
            "status",
        ],
    )


def save_current_weights_reports(
    report: pd.DataFrame,
    reports_dir: Path | str,
) -> tuple[Path, Path]:
    output_dir = Path(reports_dir).resolve() / "portfolio_state"
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "current_weights_check.csv"
    markdown_path = output_dir / "current_weights_check.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown_report(report), encoding="utf-8")
    return csv_path, markdown_path


def check_current_weights(
    config_path: Path | str,
    current_weights_csv: Path | str,
    threshold: float = 0.01,
    reports_dir: Path | str | None = None,
    write_config: bool = False,
) -> CurrentWeightsCheckResult:
    runtime_config = load_runtime_config(config_path)
    actual_weights = load_current_weights_csv(current_weights_csv)
    report = compare_current_weights(
        config_weights=runtime_config.current_weights,
        actual_weights=actual_weights,
        threshold=threshold,
    )
    output_dir = Path(reports_dir).resolve() if reports_dir else runtime_config.reports_dir
    csv_path, markdown_path = save_current_weights_reports(report, output_dir)

    config_updated = False
    if write_config:
        _write_current_weights_to_config(Path(config_path), actual_weights)
        config_updated = True

    status = "WARN" if (report["status"] == "WARN").any() else "OK"
    return CurrentWeightsCheckResult(
        status=status,
        report=report,
        csv_path=csv_path,
        markdown_path=markdown_path,
        config_updated=config_updated,
    )


def _write_current_weights_to_config(
    config_path: Path,
    actual_weights: Mapping[str, float],
) -> None:
    resolved = config_path.resolve()
    with resolved.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file) or {}
    if not isinstance(raw_config, dict):
        raise ValueError("Config root must be a mapping.")

    raw_config["current_weights"] = {
        str(symbol): float(weight) for symbol, weight in actual_weights.items()
    }
    with resolved.open("w", encoding="utf-8") as file:
        yaml.safe_dump(raw_config, file, allow_unicode=True, sort_keys=False)


def _render_markdown_report(report: pd.DataFrame) -> str:
    status = "WARN" if (report["status"] == "WARN").any() else "OK"
    threshold = float(report["threshold"].iloc[0]) if not report.empty else 0.0
    lines = [
        "# Current Weights Check",
        "",
        f"- Status: {status}",
        f"- Threshold: {threshold:.4f}",
        "- Config update: not performed unless `--write-config` is used.",
        "",
        "| Symbol | Config Weight | Actual Weight | Diff | Status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            "| {symbol} | {config_weight:.4f} | {actual_weight:.4f} | {diff:+.4f} | {status} |".format(
                symbol=row.symbol,
                config_weight=float(row.config_weight),
                actual_weight=float(row.actual_weight),
                diff=float(row.diff),
                status=row.status,
            )
        )
    lines.append("")
    return "\n".join(lines)
