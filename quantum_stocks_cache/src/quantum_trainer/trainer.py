from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from quantum_trainer.config import load_runtime_config
from quantum_trainer.io import load_price_csv, save_backtest_reports
from quantum_trainer.risk import evaluate_risk
from quantum_trainer.sizing import SizingResult, calculate_volatility_adjusted_weights
from quantum_trainer.trade_plan import generate_trade_plan
from quantum_trainer.trend import run_dynamic_trend_backtest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailyTrainerOutput:
    trade_plan_path: Path
    decision_report_path: Path
    sizing_diagnostics_path: Path
    trade_plan: pd.DataFrame


def _as_percent(value: float) -> str:
    return f"{value:.2%}"


def _render_markdown_table(frame: pd.DataFrame) -> str:
    try:
        table = frame.copy()
        columns = [str(column) for column in table.columns]
        rows = table.astype(str).values.tolist()
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        body = ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join([header, separator, *body])
    except Exception as exc:
        logger.exception("Failed to render markdown table: %s", exc)
        raise


def _sizing_diagnostics_frame(sizing: SizingResult) -> pd.DataFrame:
    try:
        rows = []
        for symbol, target_weight in sizing.target_weights.items():
            rows.append(
                {
                    "symbol": symbol,
                    "target_weight": target_weight,
                    "realized_volatility": sizing.realized_volatility.get(symbol),
                    "volatility_scalar": sizing.volatility_scalars.get(symbol),
                }
            )
        return pd.DataFrame(rows).set_index("symbol")
    except Exception as exc:
        logger.exception("Failed to build sizing diagnostics: %s", exc)
        raise


def _render_decision_report(
    report_date: date,
    trade_plan: pd.DataFrame,
    sizing_diagnostics: pd.DataFrame,
    risk_status: str,
    reason_codes: tuple[str, ...],
    risk_metrics: dict[str, float],
    performance_summary: pd.DataFrame,
) -> str:
    try:
        dynamic = performance_summary.loc["dynamic_trend"]
        reason_text = ", ".join(reason_codes) if reason_codes else "NONE"
        lines = [
            f"# Daily Quant Trainer Report - {report_date.isoformat()}",
            "",
            "## Risk Gate",
            "",
            f"- Status: {risk_status}",
            f"- Reason Codes: {reason_text}",
            f"- Current Drawdown: {_as_percent(risk_metrics['current_drawdown'])}",
            f"- Latest Turnover: {_as_percent(risk_metrics['latest_turnover'])}",
            f"- Cash Exposure: {_as_percent(risk_metrics['latest_cash_exposure'])}",
            "",
            "## Performance",
            "",
            f"- Dynamic CAGR: {_as_percent(float(dynamic['CAGR']))}",
            f"- Dynamic MDD: {_as_percent(float(dynamic['MDD']))}",
            f"- Dynamic Volatility: {_as_percent(float(dynamic['Volatility']))}",
            "",
            "## Trade Plan",
            "",
            _render_markdown_table(trade_plan.reset_index()),
            "",
            "## Position Sizing",
            "",
            _render_markdown_table(sizing_diagnostics.reset_index()),
            "",
        ]
        return "\n".join(lines)
    except Exception as exc:
        logger.exception("Failed to render decision report: %s", exc)
        raise


def run_daily_trainer(
    config_path: Path | str,
    as_of: date | None = None,
) -> DailyTrainerOutput:
    try:
        runtime_config = load_runtime_config(config_path)
        prices = load_price_csv(runtime_config.prices_csv)
        result = run_dynamic_trend_backtest(prices, runtime_config.backtest)
        save_backtest_reports(result, runtime_config.reports_dir)

        risk = evaluate_risk(result, runtime_config.risk)
        latest_positions = {
            str(symbol): float(position) for symbol, position in result.positions.iloc[-1].items()
        }
        sizing = calculate_volatility_adjusted_weights(
            prices=prices,
            strategic_weights=runtime_config.backtest.weights,
            latest_positions=latest_positions,
            config=runtime_config.sizing,
            periods_per_year=runtime_config.backtest.periods_per_year,
        )
        sizing_diagnostics = _sizing_diagnostics_frame(sizing)
        trade_plan = generate_trade_plan(
            result=result,
            risk=risk,
            strategic_weights=runtime_config.backtest.weights,
            current_weights=runtime_config.current_weights,
            target_weights=sizing.target_weights,
        )

        report_date = as_of or prices.index[-1].date()
        daily_dir = runtime_config.reports_dir / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)

        trade_plan_path = daily_dir / f"{report_date.isoformat()}_trade_plan.csv"
        decision_report_path = daily_dir / f"{report_date.isoformat()}_decision_report.md"
        sizing_diagnostics_path = daily_dir / f"{report_date.isoformat()}_sizing_diagnostics.csv"

        trade_plan.to_csv(trade_plan_path, encoding="utf-8-sig")
        sizing_diagnostics.to_csv(sizing_diagnostics_path, encoding="utf-8-sig")
        report = _render_decision_report(
            report_date=report_date,
            trade_plan=trade_plan,
            sizing_diagnostics=sizing_diagnostics,
            risk_status=risk.status,
            reason_codes=risk.reason_codes,
            risk_metrics=risk.metrics,
            performance_summary=result.performance_summary,
        )
        decision_report_path.write_text(report, encoding="utf-8")

        return DailyTrainerOutput(
            trade_plan_path=trade_plan_path,
            decision_report_path=decision_report_path,
            sizing_diagnostics_path=sizing_diagnostics_path,
            trade_plan=trade_plan,
        )
    except Exception as exc:
        logger.exception("Daily trainer failed: %s", exc)
        raise
