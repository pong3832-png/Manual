from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.data_quality import DataQualityConfig, validate_price_data
from quantum_trainer.institutional_trainer import run_institutional_trainer
from quantum_trainer.investment_committee import render_investment_committee_report
from quantum_trainer.model_registry import register_model_run
from quantum_trainer.pretrade import PreTradeConfig, apply_pretrade_checks
from quantum_trainer.research_ledger import append_ledger_entry


def _prices() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "000660.KS": [100.0, 101.0, 102.0, 103.0, 104.0],
            "005380.KS": [200.0, 201.0, 202.0, 203.0, 204.0],
        },
        index=pd.date_range("2026-05-20", periods=5, freq="B", name="date"),
    )


def test_data_quality_fails_when_required_symbol_is_missing() -> None:
    result = validate_price_data(
        prices=_prices()[["000660.KS"]],
        required_symbols=["000660.KS", "005380.KS"],
        config=DataQualityConfig(max_stale_days=10),
        as_of=date(2026, 5, 26),
    )

    assert result.status == "FAIL"
    assert "MISSING_SYMBOLS" in result.reason_codes


def test_data_quality_fails_when_prices_are_stale() -> None:
    result = validate_price_data(
        prices=_prices(),
        required_symbols=["000660.KS", "005380.KS"],
        config=DataQualityConfig(max_stale_days=1),
        as_of=date(2026, 6, 5),
    )

    assert result.status == "FAIL"
    assert "STALE_DATA" in result.reason_codes


def test_data_quality_passes_for_clean_prices() -> None:
    result = validate_price_data(
        prices=_prices(),
        required_symbols=["000660.KS", "005380.KS"],
        config=DataQualityConfig(max_stale_days=10),
        as_of=date(2026, 5, 26),
    )

    assert result.status == "PASS"
    assert result.reason_codes == ()


def test_pretrade_blocks_excessive_order_delta() -> None:
    trade_plan = pd.DataFrame(
        {
            "current_weight": [0.0],
            "target_weight": [0.6],
            "delta_weight": [0.6],
            "action": ["BUY_TO_TARGET"],
            "risk_status": ["PASS"],
        },
        index=pd.Index(["000660.KS"], name="symbol"),
    )

    result = apply_pretrade_checks(
        trade_plan=trade_plan,
        config=PreTradeConfig(max_order_delta=0.25, max_gross_exposure=1.0),
    )

    assert result.status == "BLOCK"
    assert "MAX_ORDER_DELTA" in result.reason_codes
    assert result.checked_trade_plan.loc["000660.KS", "pretrade_status"] == "BLOCK"


def test_pretrade_passes_clean_trade_plan() -> None:
    trade_plan = pd.DataFrame(
        {
            "current_weight": [0.1],
            "target_weight": [0.2],
            "delta_weight": [0.1],
            "action": ["BUY_TO_TARGET"],
            "risk_status": ["PASS"],
        },
        index=pd.Index(["000660.KS"], name="symbol"),
    )

    result = apply_pretrade_checks(
        trade_plan=trade_plan,
        config=PreTradeConfig(max_order_delta=0.25, max_gross_exposure=1.0),
    )

    assert result.status == "PASS"
    assert result.reason_codes == ()


def test_registry_and_ledger_write_audit_records() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        registry_path = register_model_run(
            registry_dir=root / "models" / "registry",
            run_id="run-1",
            strategy_name="dynamic_trend_v1",
            config_text="portfolio: {}",
            symbols=["000660.KS", "005380.KS"],
            artifact_paths={"trade_plan": root / "trade_plan.csv"},
            statuses={"data_quality": "PASS", "pretrade": "PASS"},
        )
        ledger_path = append_ledger_entry(
            ledger_path=root / "ledger" / "research_ledger.csv",
            row={
                "run_id": "run-1",
                "data_quality_status": "PASS",
                "pretrade_status": "PASS",
                "risk_status": "PASS",
            },
        )

        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        ledger = pd.read_csv(ledger_path)
        assert registry["run_id"] == "run-1"
        assert registry["config_hash"]
        assert ledger.iloc[0]["run_id"] == "run-1"


def test_investment_committee_report_contains_governance_sections() -> None:
    report = render_investment_committee_report(
        run_id="run-1",
        report_date=date(2026, 5, 26),
        data_quality_status="PASS",
        risk_status="PASS",
        pretrade_status="PASS",
        trade_plan=pd.DataFrame({"action": ["HOLD"]}, index=pd.Index(["000660.KS"], name="symbol")),
        reason_codes={"data_quality": (), "risk": (), "pretrade": ()},
    )

    assert "Investment Committee Report" in report
    assert "Data Quality: PASS" in report
    assert "Pre-Trade: PASS" in report


def test_institutional_trainer_writes_run_artifacts() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_csv = root / "prices.csv"
        prices_csv.write_text(
            "\n".join(
                [
                    "date,000660.KS",
                    "2026-01-01,10",
                    "2026-01-02,11",
                    "2026-01-05,12",
                    "2026-01-06,13",
                    "2026-01-07,14",
                    "2026-01-08,13",
                    "2026-01-09,12",
                    "2026-01-12,11",
                    "2026-01-13,12",
                    "2026-01-14,13",
                    "2026-01-15,14",
                    "2026-01-16,15",
                    "2026-01-19,16",
                    "2026-01-20,17",
                    "2026-01-21,18",
                    "2026-01-22,19",
                    "2026-01-23,20",
                    "2026-01-26,21",
                    "2026-01-27,22",
                    "2026-01-28,23",
                    "2026-01-29,24",
                ]
            ),
            encoding="utf-8",
        )
        config_path = root / "portfolio.yaml"
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
                    "risk:",
                    "  max_portfolio_mdd: -0.50",
                    "  max_daily_turnover: 1.0",
                    "  max_cash_exposure: 1.0",
                    "sizing:",
                    "  enabled: true",
                    "  target_volatility: 0.15",
                    "  realized_vol_window: 5",
                    "  volatility_floor: 0.05",
                    "  max_position_weight: 1.0",
                    "  max_leverage: 1.0",
                    "data_quality:",
                    "  max_stale_days: 10",
                    "  max_abs_daily_return: 1.0",
                    "pretrade:",
                    "  max_order_delta: 1.0",
                    "  max_gross_exposure: 1.0",
                    "portfolio:",
                    "  000660.KS: 1.0",
                    "current_weights:",
                    "  000660.KS: 0.0",
                ]
            ),
            encoding="utf-8",
        )

        output = run_institutional_trainer(
            config_path=config_path,
            as_of=date(2026, 1, 29),
            update_market_data=False,
        )

        assert output.run_dir.exists()
        assert output.ic_report_path.exists()
        assert output.registry_path.exists()
        assert output.ledger_path.exists()
        assert output.checked_trade_plan_path.exists()
