from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from quantum_trainer.config import load_runtime_config
from quantum_trainer.data_quality import validate_price_data
from quantum_trainer.institutional_trainer_helpers import copy_artifact
from quantum_trainer.investment_committee import render_investment_committee_report
from quantum_trainer.io import load_price_csv
from quantum_trainer.market_data import fetch_market_prices, write_price_cache
from quantum_trainer.model_registry import register_model_run
from quantum_trainer.pretrade import apply_pretrade_checks
from quantum_trainer.research_ledger import append_ledger_entry
from quantum_trainer.trainer import run_daily_trainer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InstitutionalTrainerOutput:
    run_id: str
    run_dir: Path
    ic_report_path: Path
    registry_path: Path
    ledger_path: Path
    checked_trade_plan_path: Path


def _run_id(report_date: date) -> str:
    timestamp = datetime.now().strftime("%H%M%S")
    return f"{report_date.isoformat()}-{timestamp}"


def run_institutional_trainer(
    config_path: Path | str,
    as_of: date | None = None,
    update_market_data: bool = True,
) -> InstitutionalTrainerOutput:
    try:
        config_file = Path(config_path).resolve()
        runtime_config = load_runtime_config(config_file)

        if update_market_data:
            symbols = list(runtime_config.backtest.weights.keys())
            market_prices = fetch_market_prices(symbols=symbols, config=runtime_config.market_data)
            write_price_cache(market_prices, runtime_config.prices_csv)

        prices = load_price_csv(runtime_config.prices_csv)
        report_date = as_of or prices.index[-1].date()
        run_id = _run_id(report_date)
        run_dir = runtime_config.reports_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        data_quality = validate_price_data(
            prices=prices,
            required_symbols=list(runtime_config.backtest.weights.keys()),
            config=runtime_config.data_quality,
            as_of=report_date,
        )

        daily_output = run_daily_trainer(config_path=config_file, as_of=report_date)
        risk_status = str(daily_output.trade_plan["risk_status"].iloc[0])
        risk_reasons = (risk_status,) if risk_status not in {"PASS", "REVIEW"} else ()

        pretrade = apply_pretrade_checks(daily_output.trade_plan, runtime_config.pretrade)

        trade_plan_path = copy_artifact(daily_output.trade_plan_path, run_dir / "trade_plan.csv")
        checked_trade_plan_path = run_dir / "pretrade_checked_trade_plan.csv"
        pretrade.checked_trade_plan.to_csv(checked_trade_plan_path, encoding="utf-8-sig")

        ic_report = render_investment_committee_report(
            run_id=run_id,
            report_date=report_date,
            data_quality_status=data_quality.status,
            risk_status=risk_status,
            pretrade_status=pretrade.status,
            trade_plan=pretrade.checked_trade_plan,
            reason_codes={
                "data_quality": data_quality.reason_codes,
                "risk": risk_reasons,
                "pretrade": pretrade.reason_codes,
            },
        )
        ic_report_path = run_dir / "investment_committee_report.md"
        ic_report_path.write_text(ic_report, encoding="utf-8")

        config_text = config_file.read_text(encoding="utf-8")
        registry_path = register_model_run(
            registry_dir=runtime_config.reports_dir.parent / "models" / "registry",
            run_id=run_id,
            strategy_name="dynamic_trend_vol_target_control_plane_v1",
            config_text=config_text,
            symbols=list(runtime_config.backtest.weights.keys()),
            artifact_paths={
                "trade_plan": trade_plan_path,
                "checked_trade_plan": checked_trade_plan_path,
                "investment_committee_report": ic_report_path,
            },
            statuses={
                "data_quality": data_quality.status,
                "risk": risk_status,
                "pretrade": pretrade.status,
            },
        )

        ledger_path = append_ledger_entry(
            ledger_path=runtime_config.reports_dir.parent / "ledger" / "research_ledger.csv",
            row={
                "run_id": run_id,
                "report_date": report_date.isoformat(),
                "data_quality_status": data_quality.status,
                "risk_status": risk_status,
                "pretrade_status": pretrade.status,
                "trade_plan_path": str(trade_plan_path),
                "ic_report_path": str(ic_report_path),
            },
        )

        return InstitutionalTrainerOutput(
            run_id=run_id,
            run_dir=run_dir,
            ic_report_path=ic_report_path,
            registry_path=registry_path,
            ledger_path=ledger_path,
            checked_trade_plan_path=checked_trade_plan_path,
        )
    except Exception as exc:
        logger.exception("Institutional trainer failed: %s", exc)
        raise
