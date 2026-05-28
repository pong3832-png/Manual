from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quantum_trainer.config import load_runtime_config
from quantum_trainer.portfolio_state import check_current_weights

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InvestmentReadinessResult:
    overall_status: str
    summary: pd.DataFrame
    csv_path: Path
    markdown_path: Path
    current_weights_check_path: Path
    config_updated: bool


def find_latest_pretrade_trade_plan(reports_dir: Path | str) -> Path:
    runs_dir = Path(reports_dir).resolve() / "runs"
    candidates = sorted(runs_dir.glob("*/pretrade_checked_trade_plan.csv"))
    if not candidates:
        raise FileNotFoundError(f"No pretrade_checked_trade_plan.csv found under {runs_dir}")
    return candidates[-1]


def run_investment_readiness(
    config_path: Path | str,
    current_weights_csv: Path | str,
    trade_plan_csv: Path | str | None = None,
    alpha_report_csv: Path | str | None = None,
    threshold: float = 0.01,
    reports_dir: Path | str | None = None,
) -> InvestmentReadinessResult:
    runtime_config = load_runtime_config(config_path)
    output_root = Path(reports_dir).resolve() if reports_dir else runtime_config.reports_dir
    resolved_trade_plan = (
        Path(trade_plan_csv).resolve()
        if trade_plan_csv is not None
        else find_latest_pretrade_trade_plan(output_root)
    )
    resolved_alpha_report = (
        Path(alpha_report_csv).resolve()
        if alpha_report_csv is not None
        else output_root / "alpha" / "buy_timing_report.csv"
    )

    current_weights_result = check_current_weights(
        config_path=config_path,
        current_weights_csv=current_weights_csv,
        threshold=threshold,
        reports_dir=output_root,
        write_config=False,
    )
    trade_plan = _load_trade_plan_csv(resolved_trade_plan)
    alpha_report = _load_alpha_report_csv(resolved_alpha_report)

    summary = _build_readiness_summary(
        trade_plan=trade_plan,
        alpha_report=alpha_report,
        current_weights_check=current_weights_result.report,
    )
    overall_status = (
        "BLOCK"
        if (summary["readiness_status"] == "BLOCK").any()
        else "READY_FOR_HUMAN_REVIEW"
    )
    csv_path, markdown_path = _save_readiness_reports(summary, output_root, overall_status)

    return InvestmentReadinessResult(
        overall_status=overall_status,
        summary=summary,
        csv_path=csv_path,
        markdown_path=markdown_path,
        current_weights_check_path=current_weights_result.csv_path,
        config_updated=current_weights_result.config_updated,
    )


def _load_trade_plan_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Trade plan CSV not found: {path}")
    trade_plan = pd.read_csv(path)
    required = {
        "symbol",
        "current_weight",
        "target_weight",
        "delta_weight",
        "action",
        "risk_status",
        "pretrade_status",
        "pretrade_reason_codes",
    }
    missing = required.difference(trade_plan.columns)
    if missing:
        raise ValueError(f"Trade plan CSV missing required columns: {sorted(missing)}")
    return trade_plan


def _load_alpha_report_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Alpha report CSV not found: {path}")
    alpha_report = pd.read_csv(path)
    required = {
        "symbol",
        "expected_20d_return",
        "upside_probability",
        "buy_timing_score",
        "decision",
    }
    missing = required.difference(alpha_report.columns)
    if missing:
        raise ValueError(f"Alpha report CSV missing required columns: {sorted(missing)}")
    return alpha_report.rename(columns={"decision": "alpha_decision"})


def _build_readiness_summary(
    trade_plan: pd.DataFrame,
    alpha_report: pd.DataFrame,
    current_weights_check: pd.DataFrame,
) -> pd.DataFrame:
    weights = current_weights_check.rename(
        columns={
            "status": "current_weights_status",
            "diff": "current_weights_diff",
            "abs_diff": "current_weights_abs_diff",
        }
    )[
        [
            "symbol",
            "current_weights_status",
            "current_weights_diff",
            "current_weights_abs_diff",
        ]
    ]
    merged = trade_plan.merge(weights, on="symbol", how="left").merge(
        alpha_report[
            [
                "symbol",
                "expected_20d_return",
                "upside_probability",
                "buy_timing_score",
                "alpha_decision",
            ]
        ],
        on="symbol",
        how="left",
    )

    rows: list[dict[str, object]] = []
    for row in merged.itertuples(index=False):
        reason_codes = _readiness_reason_codes(row)
        readiness_status = "BLOCK" if reason_codes else "READY_FOR_HUMAN_REVIEW"
        rows.append(
            {
                "symbol": row.symbol,
                "action": row.action,
                "current_weight": float(row.current_weight),
                "target_weight": float(row.target_weight),
                "delta_weight": float(row.delta_weight),
                "risk_status": row.risk_status,
                "pretrade_status": row.pretrade_status,
                "pretrade_reason_codes": row.pretrade_reason_codes,
                "current_weights_status": row.current_weights_status,
                "current_weights_diff": row.current_weights_diff,
                "current_weights_abs_diff": row.current_weights_abs_diff,
                "expected_20d_return": row.expected_20d_return,
                "upside_probability": row.upside_probability,
                "buy_timing_score": row.buy_timing_score,
                "alpha_decision": row.alpha_decision,
                "readiness_status": readiness_status,
                "readiness_reason_codes": ",".join(reason_codes) if reason_codes else "NONE",
            }
        )

    return pd.DataFrame(rows)


def _readiness_reason_codes(row: object) -> list[str]:
    reason_codes: list[str] = []
    if getattr(row, "current_weights_status", None) == "WARN":
        reason_codes.append("CURRENT_WEIGHTS_WARN")
    if getattr(row, "risk_status", None) == "BLOCK":
        reason_codes.append("RISK_BLOCK")
    if getattr(row, "pretrade_status", None) == "BLOCK":
        reason_codes.append("PRETRADE_BLOCK")
    return reason_codes


def _save_readiness_reports(
    summary: pd.DataFrame,
    reports_dir: Path | str,
    overall_status: str,
) -> tuple[Path, Path]:
    output_dir = Path(reports_dir).resolve() / "investment_readiness"
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "investment_readiness.csv"
    markdown_path = output_dir / "investment_readiness.md"
    summary.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(
        _render_readiness_markdown(summary, overall_status),
        encoding="utf-8",
    )
    return csv_path, markdown_path


def _render_readiness_markdown(summary: pd.DataFrame, overall_status: str) -> str:
    lines = [
        "# Investment Readiness Report",
        "",
        f"- Overall Status: {overall_status}",
        "- No broker order or API call was performed.",
        "- This report is a decision-control aid, not an instruction to trade.",
        "",
        "| Symbol | Action | Pre-Trade | Alpha | Delta | Readiness | Reasons |",
        "|---|---|---|---|---:|---|---|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            "| {symbol} | {action} | {pretrade_status} | {alpha_decision} | {delta_weight:+.4f} | {readiness_status} | {reasons} |".format(
                symbol=row.symbol,
                action=row.action,
                pretrade_status=row.pretrade_status,
                alpha_decision=row.alpha_decision,
                delta_weight=float(row.delta_weight),
                readiness_status=row.readiness_status,
                reasons=row.readiness_reason_codes,
            )
        )
    lines.append("")
    return "\n".join(lines)
