from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.portfolio_state import (
    check_current_weights,
    load_current_weights_csv,
)


def _write_config(path: Path) -> None:
    path.write_text(
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
                "  000660.KS: 0.60",
                "  005380.KS: 0.40",
                "current_weights:",
                "  000660.KS: 0.60",
                "  005380.KS: 0.40",
            ]
        ),
        encoding="utf-8",
    )


def test_load_current_weights_csv_requires_symbol_and_current_weight() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        csv_path = Path(tmp_dir) / "current_weights.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "symbol,current_weight",
                    "000660.KS,0.55",
                    "005380.KS,0.45",
                ]
            ),
            encoding="utf-8",
        )

        weights = load_current_weights_csv(csv_path)

        assert weights == {"000660.KS": 0.55, "005380.KS": 0.45}


def test_check_current_weights_writes_warning_reports_without_overwriting_config() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_path = tmp_path / "portfolio.yaml"
        csv_path = tmp_path / "current_weights.csv"
        reports_dir = tmp_path / "reports"
        _write_config(config_path)
        original_config = config_path.read_text(encoding="utf-8")
        csv_path.write_text(
            "\n".join(
                [
                    "symbol,current_weight",
                    "000660.KS,0.55",
                    "005380.KS,0.45",
                ]
            ),
            encoding="utf-8",
        )

        result = check_current_weights(
            config_path=config_path,
            current_weights_csv=csv_path,
            reports_dir=reports_dir,
            threshold=0.02,
        )

        assert result.status == "WARN"
        assert result.config_updated is False
        assert config_path.read_text(encoding="utf-8") == original_config
        assert result.csv_path == reports_dir / "portfolio_state" / "current_weights_check.csv"
        assert result.markdown_path == reports_dir / "portfolio_state" / "current_weights_check.md"

        report = pd.read_csv(result.csv_path)
        assert list(report.columns) == [
            "symbol",
            "config_weight",
            "actual_weight",
            "diff",
            "abs_diff",
            "threshold",
            "status",
        ]
        row = report.set_index("symbol").loc["000660.KS"]
        assert row["status"] == "WARN"
        assert row["diff"] == -0.05

        markdown = result.markdown_path.read_text(encoding="utf-8")
        assert "# Current Weights Check" in markdown
        assert "Status: WARN" in markdown
        assert "000660.KS" in markdown


def test_check_current_weights_can_update_config_only_when_explicitly_enabled() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_path = tmp_path / "portfolio.yaml"
        csv_path = tmp_path / "current_weights.csv"
        _write_config(config_path)
        csv_path.write_text(
            "\n".join(
                [
                    "symbol,current_weight",
                    "000660.KS,0.52",
                    "005380.KS,0.48",
                ]
            ),
            encoding="utf-8",
        )

        result = check_current_weights(
            config_path=config_path,
            current_weights_csv=csv_path,
            threshold=0.01,
            write_config=True,
        )

        updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert result.config_updated is True
        assert updated["current_weights"] == {"000660.KS": 0.52, "005380.KS": 0.48}
