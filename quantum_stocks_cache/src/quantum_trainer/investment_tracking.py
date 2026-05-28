from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quantum_trainer.io import load_price_csv


TRADE_JOURNAL_COLUMNS = {
    "symbol",
    "company_name",
    "buy_date",
    "buy_price",
    "shares",
    "thesis",
    "stop_loss_rule",
    "thesis_status",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "tracking_status",
    "buy_date",
    "buy_price",
    "shares",
    "latest_price",
    "latest_price_date",
    "invested_value",
    "current_value",
    "unrealized_pnl",
    "unrealized_return",
    "one_week_check_date",
    "one_month_check_date",
    "quarter_check_date",
    "one_week_due",
    "one_month_due",
    "quarter_due",
    "thesis",
    "thesis_status",
    "stop_loss_rule",
    "review_action",
    "order_status",
    "broker_order_requested",
    "next_step",
]


@dataclass(frozen=True)
class InvestmentTrackingOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_investment_tracking(
    trade_journal_csv: Path | str,
    prices_csv: Path | str,
    output_dir: Path | str,
) -> InvestmentTrackingOutput:
    prices = load_price_csv(prices_csv)
    latest_date = prices.index[-1]
    latest_prices = prices.iloc[-1]
    journal_path = Path(trade_journal_csv).resolve()

    if not journal_path.exists():
        report = pd.DataFrame([_not_started_row(latest_date)], columns=OUTPUT_COLUMNS)
    else:
        journal = _load_journal(journal_path)
        rows = [_tracking_row(row, latest_date, latest_prices) for row in journal.to_dict(orient="records")]
        report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

    output_root = Path(output_dir).resolve() / "performance_tracking"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "performance_tracking.csv"
    markdown_path = output_root / "performance_tracking.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    tracked_positions = int((report["tracking_status"] == "TRACKING_ACTIVE").sum())
    summary = {
        "tracked_positions": tracked_positions,
        "review_due_count": int(report["review_action"].astype(str).str.contains("DUE|STOP|REDUCE").sum()),
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return InvestmentTrackingOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_journal(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path).fillna("")
    missing = sorted(TRADE_JOURNAL_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Trade journal CSV missing required columns: {missing}")
    return frame


def _tracking_row(row: dict[str, object], latest_date: pd.Timestamp, latest_prices: pd.Series) -> dict[str, object]:
    symbol = str(row["symbol"]).strip()
    buy_date = pd.to_datetime(row["buy_date"], errors="raise")
    buy_price = _number(row["buy_price"])
    shares = int(_number(row["shares"]))
    latest_price = _number(latest_prices.get(symbol, 0.0))
    invested_value = int(round(buy_price * shares))
    current_value = int(round(latest_price * shares))
    unrealized_pnl = int(current_value - invested_value)
    unrealized_return = (current_value / invested_value - 1.0) if invested_value > 0 else 0.0
    one_week = buy_date + pd.DateOffset(days=7)
    one_month = buy_date + pd.DateOffset(months=1)
    quarter = buy_date + pd.DateOffset(months=3)
    thesis_status = str(row["thesis_status"]).strip().upper() or "UNKNOWN"

    return {
        "symbol": symbol,
        "company_name": str(row["company_name"]).strip(),
        "tracking_status": "TRACKING_ACTIVE",
        "buy_date": _date(buy_date),
        "buy_price": buy_price,
        "shares": shares,
        "latest_price": latest_price,
        "latest_price_date": _date(latest_date),
        "invested_value": invested_value,
        "current_value": current_value,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_return": unrealized_return,
        "one_week_check_date": _date(one_week),
        "one_month_check_date": _date(one_month),
        "quarter_check_date": _date(quarter),
        "one_week_due": _yes_no(latest_date >= one_week),
        "one_month_due": _yes_no(latest_date >= one_month),
        "quarter_due": _yes_no(latest_date >= quarter),
        "thesis": str(row["thesis"]).strip(),
        "thesis_status": thesis_status,
        "stop_loss_rule": str(row["stop_loss_rule"]).strip(),
        "review_action": _review_action(latest_date, one_week, one_month, quarter, unrealized_return, thesis_status),
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
        "next_step": "점검일마다 thesis 유지 여부와 손익 원인을 기록하세요.",
    }


def _not_started_row(latest_date: pd.Timestamp) -> dict[str, object]:
    return {
        "symbol": "",
        "company_name": "",
        "tracking_status": "NO_TRADE_JOURNAL",
        "buy_date": "",
        "buy_price": 0.0,
        "shares": 0,
        "latest_price": 0.0,
        "latest_price_date": _date(latest_date),
        "invested_value": 0,
        "current_value": 0,
        "unrealized_pnl": 0,
        "unrealized_return": 0.0,
        "one_week_check_date": "",
        "one_month_check_date": "",
        "quarter_check_date": "",
        "one_week_due": "NO",
        "one_month_due": "NO",
        "quarter_due": "NO",
        "thesis": "",
        "thesis_status": "NOT_STARTED",
        "stop_loss_rule": "",
        "review_action": "WRITE_TRADE_JOURNAL_AFTER_BUY",
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
        "next_step": "실제 매수 후 configs/trade_journal.actual.csv에 매수 당시 thesis를 기록하세요.",
    }


def _review_action(
    latest_date: pd.Timestamp,
    one_week: pd.Timestamp,
    one_month: pd.Timestamp,
    quarter: pd.Timestamp,
    unrealized_return: float,
    thesis_status: str,
) -> str:
    if thesis_status == "BROKEN" or unrealized_return <= -0.07:
        return "REDUCE_OR_STOP_REVIEW_DUE"
    if latest_date >= quarter:
        return "QUARTER_REVIEW_DUE"
    if latest_date >= one_month:
        return "ONE_MONTH_REVIEW_DUE"
    if latest_date >= one_week:
        return "ONE_WEEK_REVIEW_DUE"
    return "HOLD_AND_MONITOR"


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Investment Tracking",
        "",
        "실제 매수 후 성과와 thesis 유지 여부를 추적하는 리포트입니다. 실제 주문을 실행하지 않습니다.",
        "",
        f"- Tracked positions: {summary['tracked_positions']}",
        f"- Review due count: {summary['review_due_count']}",
        f"- Order status: {summary['order_status']}",
        "",
        "| Symbol | Status | PnL | Return | Review | Next Step |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.symbol or '-'} | {row.tracking_status} | {_money(row.unrealized_pnl)} | "
            f"{_pct(row.unrealized_return)} | {row.review_action} | {row.next_step} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _date(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _money(value: object) -> str:
    return f"{_number(value):,.0f} KRW"


def _pct(value: object) -> str:
    return f"{_number(value) * 100:.1f}%"
