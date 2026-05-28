from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.investment_readiness import run_investment_readiness


def _write_config(path: Path, reports_dir: str = "reports") -> None:
    path.write_text(
        "\n".join(
            [
                "data:",
                "  prices_csv: prices.csv",
                "reports:",
                f"  output_dir: {reports_dir}",
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


def _write_trade_plan(path: Path, pretrade_status: str) -> None:
    path.write_text(
        "\n".join(
            [
                "symbol,position,current_weight,target_weight,delta_weight,action,risk_status,pretrade_status,pretrade_reason_codes",
                f"000660.KS,1.0,0.60,0.55,-0.05,REDUCE_TO_TARGET,PASS,{pretrade_status},NONE",
                f"005380.KS,1.0,0.40,0.45,0.05,BUY_TO_TARGET,PASS,{pretrade_status},NONE",
            ]
        ),
        encoding="utf-8",
    )


def _write_alpha_report(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "symbol,expected_20d_return,upside_probability,sample_count,model_r2,buy_timing_score,decision",
                "000660.KS,0.05,0.55,120,0.10,72.5,WAIT",
                "005380.KS,0.08,0.64,120,0.12,91.0,BUY_READY",
            ]
        ),
        encoding="utf-8",
    )


def test_investment_readiness_blocks_when_weights_or_pretrade_warn() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_path = tmp_path / "portfolio.yaml"
        weights_csv = tmp_path / "current_weights.csv"
        trade_plan_csv = tmp_path / "pretrade_checked_trade_plan.csv"
        alpha_csv = tmp_path / "buy_timing_report.csv"
        _write_config(config_path)
        weights_csv.write_text(
            "\n".join(
                [
                    "symbol,current_weight",
                    "000660.KS,0.50",
                    "005380.KS,0.50",
                ]
            ),
            encoding="utf-8",
        )
        _write_trade_plan(trade_plan_csv, pretrade_status="BLOCK")
        _write_alpha_report(alpha_csv)

        result = run_investment_readiness(
            config_path=config_path,
            current_weights_csv=weights_csv,
            trade_plan_csv=trade_plan_csv,
            alpha_report_csv=alpha_csv,
            threshold=0.02,
        )

        assert result.overall_status == "BLOCK"
        assert result.csv_path.exists()
        assert result.markdown_path.exists()
        assert result.current_weights_check_path.exists()
        assert result.config_updated is False

        summary = pd.read_csv(result.csv_path)
        row = summary.set_index("symbol").loc["005380.KS"]
        assert row["readiness_status"] == "BLOCK"
        assert "CURRENT_WEIGHTS_WARN" in row["readiness_reason_codes"]
        assert "PRETRADE_BLOCK" in row["readiness_reason_codes"]

        markdown = result.markdown_path.read_text(encoding="utf-8")
        assert "Overall Status: BLOCK" in markdown
        assert "No broker order or API call was performed." in markdown


def test_investment_readiness_marks_ready_for_review_when_controls_pass() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_path = tmp_path / "portfolio.yaml"
        weights_csv = tmp_path / "current_weights.csv"
        trade_plan_csv = tmp_path / "pretrade_checked_trade_plan.csv"
        alpha_csv = tmp_path / "buy_timing_report.csv"
        _write_config(config_path)
        weights_csv.write_text(
            "\n".join(
                [
                    "symbol,current_weight",
                    "000660.KS,0.60",
                    "005380.KS,0.40",
                ]
            ),
            encoding="utf-8",
        )
        _write_trade_plan(trade_plan_csv, pretrade_status="PASS")
        _write_alpha_report(alpha_csv)

        result = run_investment_readiness(
            config_path=config_path,
            current_weights_csv=weights_csv,
            trade_plan_csv=trade_plan_csv,
            alpha_report_csv=alpha_csv,
            threshold=0.02,
        )

        assert result.overall_status == "READY_FOR_HUMAN_REVIEW"
        summary = pd.read_csv(result.csv_path)
        assert set(summary["readiness_status"]) == {"READY_FOR_HUMAN_REVIEW"}
