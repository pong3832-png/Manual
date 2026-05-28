from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


MEMO_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "memo_status",
    "order_status",
    "core_thesis",
    "evidence",
    "risks",
    "manual_checks",
    "loss_defense",
    "next_action",
}

CHECKLIST_COLUMNS = {
    "symbol",
    "checklist_status",
    "automatic_blockers",
    "manual_checklist",
}

RESEARCH_COLUMNS = {
    "symbol",
    "research_score",
    "research_view",
    "decision",
    "expected_20d_return",
    "upside_probability",
    "ma20_gap",
    "return_20d",
    "drawdown_20d",
    "per",
    "pbr",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "capital_plan_review",
    "amount_status",
    "order_status",
    "total_capital",
    "max_position_weight",
    "cash_buffer_weight",
    "first_tranche_pct",
    "second_tranche_pct",
    "final_tranche_pct",
    "add_condition",
    "reduce_condition",
    "stop_condition",
    "immediate_halt_condition",
    "review_notes",
]


@dataclass(frozen=True)
class CapitalPlanReviewOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame


def run_capital_plan_review(
    investment_memo_csv: Path | str,
    investment_checklist_csv: Path | str,
    company_research_csv: Path | str,
    output_dir: Path | str,
    total_capital: float | None = None,
) -> CapitalPlanReviewOutput:
    if total_capital is not None and total_capital <= 0:
        raise ValueError("total_capital must be greater than 0.")
    memo = _load_csv(Path(investment_memo_csv), MEMO_COLUMNS, "investment memo")
    checklist = _load_csv(Path(investment_checklist_csv), CHECKLIST_COLUMNS, "investment checklist")
    research = _load_csv(Path(company_research_csv), RESEARCH_COLUMNS, "company research")

    rows: list[dict[str, object]] = []
    for memo_row in memo.to_dict(orient="records"):
        symbol = str(memo_row["symbol"])
        checklist_row = _row_for_symbol(checklist, symbol)
        research_row = _row_for_symbol(research, symbol)
        rows.append(_capital_plan_row(memo_row, checklist_row, research_row, total_capital))

    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    output_root = Path(output_dir).resolve() / "decision_gate"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "capital_plan_review.csv"
    markdown_path = output_root / "capital_plan_review.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")

    for row in report.itertuples(index=False):
        code = str(row.symbol).split(".")[0]
        one = pd.DataFrame([row._asdict()], columns=OUTPUT_COLUMNS)
        one_csv = output_root / f"capital_plan_review_{code}.csv"
        one_md = output_root / f"capital_plan_review_{code}.md"
        one.to_csv(one_csv, index=False, encoding="utf-8-sig")
        one_md.write_text(_render_markdown(one), encoding="utf-8")

    return CapitalPlanReviewOutput(csv_path=csv_path, markdown_path=markdown_path, report=report)


def _capital_plan_row(
    memo: dict[str, object],
    checklist: pd.Series,
    research: pd.Series,
    total_capital: float | None,
) -> dict[str, object]:
    status = _capital_plan_status(memo, checklist)
    capital_value = 0.0 if total_capital is None else float(total_capital)
    return {
        "symbol": str(memo["symbol"]),
        "company_name": str(memo["company_name"]),
        "capital_plan_review": status,
        "amount_status": "CAPITAL_AMOUNT_REQUIRED" if total_capital is None else "CAPITAL_PROVIDED",
        "order_status": "NO_ORDER",
        "total_capital": capital_value,
        "max_position_weight": 0.15,
        "cash_buffer_weight": 0.25,
        "first_tranche_pct": 0.30,
        "second_tranche_pct": 0.30,
        "final_tranche_pct": 0.40,
        "add_condition": (
            "Add only if CORE_FOCUS persists, SMA20 holds, conviction_score >= 60, "
            "no new filing/earnings blocker appears, and manual gate remains clean."
        ),
        "reduce_condition": "If SMA20 breaks and average cost drawdown reaches -7%, reduce 50% of the position.",
        "stop_condition": (
            "If drawdown reaches -10%, conviction_score 60 미만, TODAY_FOCUS 이탈, "
            "or a checklist blocker appears, stop new buys and review full exit."
        ),
        "immediate_halt_condition": (
            "실적 훼손, fatal filing risk, manual gate FAIL, or thesis break stops all additional buys immediately."
        ),
        "review_notes": _review_notes(memo, checklist, research, status, total_capital),
    }


def _capital_plan_status(memo: dict[str, object], checklist: pd.Series) -> str:
    if str(memo.get("memo_status", "")) != "THESIS_REVIEW":
        return "UNKNOWN"
    if not str(memo.get("loss_defense", "")).strip():
        return "UNKNOWN"
    if str(checklist.get("checklist_status", "")) != "READY_FOR_MANUAL_REVIEW":
        return "UNKNOWN"
    return "PASS_CANDIDATE"


def _review_notes(
    memo: dict[str, object],
    checklist: pd.Series,
    research: pd.Series,
    status: str,
    total_capital: float | None,
) -> str:
    parts = [
        f"capital_plan_review={status}",
        (
            "rules fixed before amount; sizing remains blocked until total capital is provided"
            if total_capital is None
            else f"total_capital={int(total_capital)}; sizing can be reviewed without placing orders"
        ),
        f"checklist_status={checklist.get('checklist_status', 'UNKNOWN')}",
        f"automatic_blockers={checklist.get('automatic_blockers', '')}",
        f"research_score={_number(research.get('research_score')):.2f}",
        f"expected_20d_return={_number(research.get('expected_20d_return')):.3f}",
        f"upside_probability={_number(research.get('upside_probability')):.3f}",
        f"loss_defense={memo.get('loss_defense', '')}",
    ]
    return "; ".join(str(part) for part in parts if str(part).strip())


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame


def _row_for_symbol(frame: pd.DataFrame, symbol: str) -> pd.Series:
    row = frame.loc[frame["symbol"] == symbol]
    if row.empty:
        return pd.Series(dtype=object)
    return row.iloc[0]


def _render_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Capital Plan Review",
        "",
        "이 리포트는 투자금이 불규칙할 때 감정 매수를 막기 위한 규칙표입니다. 실제 주문 실행 문서가 아닙니다.",
        "",
        "| Symbol | Company | Review | Amount | Max Weight | First | Add | Stop |",
        "|---|---|---|---|---:|---:|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.company_name} | {row.capital_plan_review} | {row.amount_status} | "
            f"{float(row.max_position_weight) * 100:.1f}% | {float(row.first_tranche_pct) * 100:.1f}% | "
            f"{row.add_condition} | {row.stop_condition} |"
        )
    for row in report.itertuples(index=False):
        lines.extend(
            [
                "",
                f"## {row.symbol} {row.company_name}",
                f"- Order status: {row.order_status}",
                f"- Total capital: {_money(row.total_capital)}",
                f"- Cash buffer: {float(row.cash_buffer_weight) * 100:.1f}%",
                f"- Tranches: {float(row.first_tranche_pct) * 100:.1f}% / {float(row.second_tranche_pct) * 100:.1f}% / {float(row.final_tranche_pct) * 100:.1f}%",
                f"- Reduce: {row.reduce_condition}",
                f"- Immediate halt: {row.immediate_halt_condition}",
                f"- Notes: {row.review_notes}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _money(value: object) -> str:
    return f"{_number(value):,.0f} KRW"
