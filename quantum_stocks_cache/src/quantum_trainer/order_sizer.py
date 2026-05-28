from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from quantum_trainer.io import load_price_csv


REQUIRED_COLUMNS = {
    "symbol",
    "company_name",
    "checklist_status",
    "automatic_blockers",
    "research_score",
    "decision",
}


@dataclass(frozen=True)
class OrderSizerOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, float | int | str]


def run_order_sizer(
    candidate_checklist_csv: Path | str,
    prices_csv: Path | str,
    output_dir: Path | str,
    total_capital: float | None,
    max_position_weight: float = 0.20,
    cash_buffer_weight: float = 0.10,
    include_statuses: Sequence[str] = ("READY_FOR_MANUAL_REVIEW",),
) -> OrderSizerOutput:
    capital_missing = total_capital is None
    if total_capital is not None and total_capital <= 0:
        raise ValueError("total_capital must be greater than 0.")
    if not 0 < max_position_weight <= 1:
        raise ValueError("max_position_weight must be in (0, 1].")
    if not 0 <= cash_buffer_weight < 1:
        raise ValueError("cash_buffer_weight must be in [0, 1).")
    if not include_statuses:
        raise ValueError("include_statuses must not be empty.")

    checklist = _load_checklist(candidate_checklist_csv)
    prices = load_price_csv(prices_csv)
    latest_prices = prices.iloc[-1]
    latest_price_date = str(prices.index[-1].date())

    eligible_statuses = {str(status) for status in include_statuses}
    eligible = checklist.loc[checklist["checklist_status"].isin(eligible_statuses)].copy()
    eligible = eligible.sort_values("research_score", ascending=False).reset_index(drop=True)

    capital_value = 0.0 if capital_missing else float(total_capital)
    investable_capital = capital_value * (1 - cash_buffer_weight)
    equal_weight_cap = (1 - cash_buffer_weight) / max(len(eligible), 1)
    target_weight = 0.0 if capital_missing else min(max_position_weight, equal_weight_cap)
    target_value = capital_value * target_weight

    rows: list[dict[str, object]] = []
    for row in eligible.itertuples(index=False):
        latest_price = _price_for_symbol(latest_prices, str(row.symbol))
        if capital_missing:
            candidate_shares = 0
            estimated_order_value = 0.0
            order_status = "BLOCKED_CAPITAL_REQUIRED"
        elif latest_price <= 0:
            candidate_shares = 0
            estimated_order_value = 0.0
            order_status = "BLOCKED_PRICE_MISSING"
        else:
            candidate_shares = int(target_value // latest_price)
            estimated_order_value = float(candidate_shares * latest_price)
            order_status = "REVIEW_ONLY" if candidate_shares > 0 else "BLOCKED_INSUFFICIENT_CAPITAL"

        rows.append(
            {
                "symbol": row.symbol,
                "company_name": row.company_name,
                "checklist_status": row.checklist_status,
                "automatic_blockers": row.automatic_blockers,
                "research_score": float(row.research_score),
                "decision": row.decision,
                "latest_price_date": latest_price_date,
                "latest_price": latest_price,
                "total_capital": capital_value,
                "capital_status": "CAPITAL_REQUIRED" if capital_missing else "CAPITAL_PROVIDED",
                "cash_buffer_weight": float(cash_buffer_weight),
                "max_position_weight": float(max_position_weight),
                "target_weight": float(target_weight),
                "target_value": float(target_value),
                "candidate_shares": int(candidate_shares),
                "estimated_order_value": float(estimated_order_value),
                "uninvested_target_cash": float(target_value - estimated_order_value),
                "order_status": order_status,
                "execution_mode": "MANUAL_REVIEW_ONLY",
            }
        )

    report = pd.DataFrame(rows)
    total_order_value = float(report["estimated_order_value"].sum()) if not report.empty else 0.0
    summary: dict[str, float | int | str] = {
        "eligible_count": int(len(report)),
        "total_capital": capital_value,
        "capital_status": "CAPITAL_REQUIRED" if capital_missing else "CAPITAL_PROVIDED",
        "investable_capital": float(investable_capital),
        "cash_buffer_weight": float(cash_buffer_weight),
        "estimated_total_order_value": total_order_value,
        "estimated_cash_after_orders": float(capital_value - total_order_value),
        "latest_price_date": latest_price_date,
    }

    output_root = Path(output_dir).resolve() / "orders"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "order_candidates.csv"
    markdown_path = output_root / "order_candidates.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")

    return OrderSizerOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        report=report,
        summary=summary,
    )


def _load_checklist(path: Path | str) -> pd.DataFrame:
    csv_path = Path(path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"Investment checklist CSV not found: {csv_path}")
    checklist = pd.read_csv(csv_path).fillna("")
    missing = sorted(REQUIRED_COLUMNS.difference(checklist.columns))
    if missing:
        raise ValueError(f"Investment checklist CSV missing required columns: {missing}")
    return checklist


def _price_for_symbol(latest_prices: pd.Series, symbol: str) -> float:
    if symbol not in latest_prices.index:
        return 0.0
    try:
        return float(latest_prices[symbol])
    except (TypeError, ValueError):
        return 0.0


def _render_markdown(report: pd.DataFrame, summary: dict[str, float | int | str]) -> str:
    lines = [
        "# Order Candidates",
        "",
        "이 리포트는 수동 검토용 주문 후보표이며 실제 주문 실행 문서가 아닙니다.",
        "증권사 API, 브로커 API, 자동 주문 기능은 포함하지 않습니다.",
        "",
        "## Summary",
        f"- Capital status: {summary['capital_status']}",
        f"- Total capital: {_money(summary['total_capital'])}",
        f"- Cash buffer weight: {float(summary['cash_buffer_weight']) * 100:.1f}%",
        f"- Estimated total order value: {_money(summary['estimated_total_order_value'])}",
        f"- Estimated cash after orders: {_money(summary['estimated_cash_after_orders'])}",
        f"- Latest price date: {summary['latest_price_date']}",
        "",
        "| Symbol | Company | Status | Price | Target Value | Shares | Est. Order Value |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.company_name} | {row.order_status} | "
            f"{_money(row.latest_price)} | {_money(row.target_value)} | {row.candidate_shares} | "
            f"{_money(row.estimated_order_value)} |"
        )
    lines.append("")
    for row in report.itertuples(index=False):
        lines.extend(
            [
                f"## {row.symbol} {row.company_name}",
                "",
                f"- Order status: {row.order_status}",
                f"- Execution mode: {row.execution_mode}",
                f"- Checklist status: {row.checklist_status}",
                f"- Automatic blockers: {row.automatic_blockers}",
                f"- Latest price: {_money(row.latest_price)}",
                f"- Candidate shares: {row.candidate_shares}",
                f"- Estimated order value: {_money(row.estimated_order_value)}",
                f"- Uninvested target cash: {_money(row.uninvested_target_cash)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _money(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number:,.0f} KRW"
