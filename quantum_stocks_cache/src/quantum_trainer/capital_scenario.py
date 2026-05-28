from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from quantum_trainer.io import load_price_csv


CHECKLIST_COLUMNS = {
    "symbol",
    "company_name",
    "checklist_status",
    "automatic_blockers",
    "research_score",
    "decision",
}

CAPITAL_PLAN_COLUMNS = {
    "symbol",
    "max_position_weight",
    "cash_buffer_weight",
    "first_tranche_pct",
    "second_tranche_pct",
    "final_tranche_pct",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "scenario_capital",
    "scenario_status",
    "order_status",
    "execution_mode",
    "latest_price",
    "max_position_weight",
    "cash_buffer_weight",
    "target_position_value",
    "target_position_shares",
    "first_tranche_value",
    "first_tranche_shares",
    "second_tranche_value",
    "second_tranche_shares",
    "final_tranche_value",
    "final_tranche_shares",
]


@dataclass(frozen=True)
class CapitalScenarioOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_capital_scenarios(
    candidate_checklist_csv: Path | str,
    prices_csv: Path | str,
    capital_plan_dir: Path | str,
    output_dir: Path | str,
    scenario_capitals: Sequence[float] = (1_000_000, 3_000_000, 5_000_000, 10_000_000),
    include_statuses: Sequence[str] = ("READY_FOR_MANUAL_REVIEW",),
) -> CapitalScenarioOutput:
    if not scenario_capitals:
        raise ValueError("scenario_capitals must not be empty.")
    if any(float(capital) <= 0 for capital in scenario_capitals):
        raise ValueError("scenario_capitals must be greater than 0.")
    checklist = _load_csv(Path(candidate_checklist_csv), CHECKLIST_COLUMNS, "investment checklist")
    prices = load_price_csv(prices_csv)
    latest_prices = prices.iloc[-1]

    eligible = checklist.loc[checklist["checklist_status"].isin({str(status) for status in include_statuses})].copy()
    eligible = eligible.sort_values("research_score", ascending=False).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for candidate in eligible.to_dict(orient="records"):
        symbol = str(candidate["symbol"])
        price = _price_for_symbol(latest_prices, symbol)
        plan = _load_capital_plan(Path(capital_plan_dir), symbol)
        max_position_weight = _number(plan.get("max_position_weight", 0.15))
        cash_buffer_weight = _number(plan.get("cash_buffer_weight", 0.25))
        first_pct = _number(plan.get("first_tranche_pct", 0.30))
        second_pct = _number(plan.get("second_tranche_pct", 0.30))
        final_pct = _number(plan.get("final_tranche_pct", 0.40))
        for capital in scenario_capitals:
            rows.append(
                _scenario_row(
                    candidate=candidate,
                    price=price,
                    scenario_capital=float(capital),
                    max_position_weight=max_position_weight,
                    cash_buffer_weight=cash_buffer_weight,
                    first_pct=first_pct,
                    second_pct=second_pct,
                    final_pct=final_pct,
                )
            )

    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    output_root = Path(output_dir).resolve() / "orders"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "capital_scenarios.csv"
    markdown_path = output_root / "capital_scenarios.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    summary = {
        "eligible_count": int(len(eligible)),
        "scenario_count": int(len(report)),
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return CapitalScenarioOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame


def _load_capital_plan(capital_plan_dir: Path, symbol: str) -> pd.Series:
    code = symbol.split(".")[0]
    path = capital_plan_dir / f"capital_plan_review_{code}.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, CAPITAL_PLAN_COLUMNS, "capital plan review")
    row = frame.loc[frame["symbol"] == symbol]
    if row.empty:
        return pd.Series(dtype=object)
    return row.iloc[0]


def _scenario_row(
    candidate: dict[str, object],
    price: float,
    scenario_capital: float,
    max_position_weight: float,
    cash_buffer_weight: float,
    first_pct: float,
    second_pct: float,
    final_pct: float,
) -> dict[str, object]:
    target_position_value = round(scenario_capital * max_position_weight)
    first_value = round(target_position_value * first_pct)
    second_value = round(target_position_value * second_pct)
    final_value = round(target_position_value * final_pct)
    target_shares = _shares(target_position_value, price)
    first_shares = _shares(first_value, price)
    scenario_status = "SCENARIO_REVIEW_ONLY" if first_shares > 0 else "INSUFFICIENT_FOR_FIRST_TRANCHE"
    return {
        "symbol": str(candidate["symbol"]),
        "company_name": str(candidate["company_name"]),
        "scenario_capital": int(round(scenario_capital)),
        "scenario_status": scenario_status,
        "order_status": "NO_ORDER",
        "execution_mode": "MANUAL_REVIEW_ONLY",
        "latest_price": float(price),
        "max_position_weight": float(max_position_weight),
        "cash_buffer_weight": float(cash_buffer_weight),
        "target_position_value": int(target_position_value),
        "target_position_shares": int(target_shares),
        "first_tranche_value": int(first_value),
        "first_tranche_shares": int(first_shares),
        "second_tranche_value": int(second_value),
        "second_tranche_shares": int(_shares(second_value, price)),
        "final_tranche_value": int(final_value),
        "final_tranche_shares": int(_shares(final_value, price)),
    }


def _price_for_symbol(latest_prices: pd.Series, symbol: str) -> float:
    if symbol not in latest_prices.index:
        return 0.0
    return _number(latest_prices[symbol])


def _shares(value: float, price: float) -> int:
    if price <= 0:
        return 0
    return int(value // price)


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Capital Scenarios",
        "",
        "이 리포트는 자본금별 분할매수 시나리오이며 실제 주문 실행 문서가 아닙니다.",
        "",
        f"- Eligible names: {summary['eligible_count']}",
        f"- Scenario rows: {summary['scenario_count']}",
        f"- Order status: {summary['order_status']}",
        "",
        "| Symbol | Capital | Status | Target | Target Shares | First | First Shares |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {_money(row.scenario_capital)} | {row.scenario_status} | "
            f"{_money(row.target_position_value)} | {row.target_position_shares} | "
            f"{_money(row.first_tranche_value)} | {row.first_tranche_shares} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _money(value: object) -> str:
    return f"{_number(value):,.0f} KRW"
