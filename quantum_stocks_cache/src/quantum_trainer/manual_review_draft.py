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
    "fundamental_view",
    "expected_20d_return",
    "upside_probability",
    "return_20d",
    "ma20_gap",
    "drawdown_20d",
    "per",
    "pbr",
    "debt_ratio",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "filing_review",
    "earnings_review",
    "business_driver_review",
    "valuation_review",
    "loss_rule_review",
    "capital_plan_review",
    "recommended_actual_action",
    "review_notes",
]


@dataclass(frozen=True)
class ManualReviewDraftOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame


def run_manual_review_draft(
    investment_memo_csv: Path | str,
    investment_checklist_csv: Path | str,
    company_research_csv: Path | str,
    filing_risk_dir: Path | str,
    output_dir: Path | str,
    capital_plan_dir: Path | str | None = None,
) -> ManualReviewDraftOutput:
    memo = _load_csv(Path(investment_memo_csv), MEMO_COLUMNS, "investment memo")
    checklist = _load_csv(Path(investment_checklist_csv), CHECKLIST_COLUMNS, "investment checklist")
    research = _load_csv(Path(company_research_csv), RESEARCH_COLUMNS, "company research")

    rows: list[dict[str, object]] = []
    for memo_row in memo.to_dict(orient="records"):
        symbol = str(memo_row["symbol"])
        checklist_row = _row_for_symbol(checklist, symbol)
        research_row = _row_for_symbol(research, symbol)
        filing_status, filing_note = _filing_review(symbol, Path(filing_risk_dir))
        capital_status, capital_note = _capital_plan_review(
            symbol,
            Path(capital_plan_dir) if capital_plan_dir else Path(output_dir).resolve() / "decision_gate",
        )
        rows.append(
            {
                "symbol": symbol,
                "company_name": str(memo_row["company_name"]),
                "filing_review": filing_status,
                "earnings_review": _earnings_review(checklist_row, research_row),
                "business_driver_review": _business_driver_review(memo_row, research_row),
                "valuation_review": _valuation_review(checklist_row, research_row),
                "loss_rule_review": _loss_rule_review(memo_row),
                "capital_plan_review": capital_status,
                "recommended_actual_action": "DO_NOT_COPY_AUTOMATICALLY",
                "review_notes": _review_notes(memo_row, checklist_row, research_row, filing_note, capital_note),
            }
        )
    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

    output_root = Path(output_dir).resolve() / "decision_gate"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "manual_review_draft.csv"
    markdown_path = output_root / "manual_review_draft.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")

    for row in report.itertuples(index=False):
        code = str(row.symbol).split(".")[0]
        one = pd.DataFrame([row._asdict()], columns=OUTPUT_COLUMNS)
        one_csv = output_root / f"manual_review_draft_{code}.csv"
        one_md = output_root / f"manual_review_draft_{code}.md"
        one.to_csv(one_csv, index=False, encoding="utf-8-sig")
        one_md.write_text(_render_markdown(one), encoding="utf-8")

    return ManualReviewDraftOutput(csv_path=csv_path, markdown_path=markdown_path, report=report)


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


def _filing_review(symbol: str, filing_risk_dir: Path) -> tuple[str, str]:
    code = symbol.split(".")[0]
    path = filing_risk_dir / f"filing_risk_summary_{code}.csv"
    if not path.exists():
        return "UNKNOWN", "OpenDART filing risk summary not available"
    frame = pd.read_csv(path).fillna("")
    fatal = frame.get("fatal_risk", pd.Series(dtype=object)).astype(str).str.upper()
    opinion = frame.get("gate_opinion", pd.Series(dtype=object)).astype(str).str.upper()
    if (fatal == "YES").any() or (opinion == "EXCLUDE").any():
        return "FAIL_CANDIDATE", "filing risk summary has fatal or exclude opinion"
    return "PASS_CANDIDATE", "filing risk summary has no fatal risk"


def _capital_plan_review(symbol: str, capital_plan_dir: Path) -> tuple[str, str]:
    code = symbol.split(".")[0]
    path = capital_plan_dir / f"capital_plan_review_{code}.csv"
    if not path.exists():
        return "UNKNOWN", "capital_plan review not available"
    frame = pd.read_csv(path).fillna("")
    if "capital_plan_review" not in frame.columns:
        return "UNKNOWN", "capital_plan review missing status"
    status = str(frame["capital_plan_review"].iloc[0])
    amount_status = str(frame["amount_status"].iloc[0]) if "amount_status" in frame.columns else "UNKNOWN"
    return status, f"capital_plan={amount_status}"


def _earnings_review(checklist: pd.Series, research: pd.Series) -> str:
    if str(checklist.get("checklist_status", "")) != "READY_FOR_MANUAL_REVIEW":
        return "UNKNOWN"
    if str(research.get("fundamental_view", "")) == "FUNDAMENTAL_WEAK":
        return "UNKNOWN"
    if _number(research.get("expected_20d_return")) <= 0.0:
        return "UNKNOWN"
    return "PASS_CANDIDATE"


def _business_driver_review(memo: dict[str, object], research: pd.Series) -> str:
    if str(memo.get("memo_status", "")) != "THESIS_REVIEW":
        return "UNKNOWN"
    if str(research.get("research_view", "")) != "RESEARCH_CANDIDATE":
        return "UNKNOWN"
    if str(research.get("decision", "")) != "BUY_READY":
        return "UNKNOWN"
    return "PASS_CANDIDATE"


def _valuation_review(checklist: pd.Series, research: pd.Series) -> str:
    blockers = str(checklist.get("automatic_blockers", ""))
    if "밸류에이션 부담" in blockers:
        return "UNKNOWN"
    per = _number(research.get("per"))
    pbr = _number(research.get("pbr"))
    if per <= 0.0 or pbr <= 0.0:
        return "UNKNOWN"
    if per >= 35.0 or pbr >= 3.0:
        return "UNKNOWN"
    return "PASS_CANDIDATE"


def _loss_rule_review(memo: dict[str, object]) -> str:
    return "PASS_CANDIDATE" if str(memo.get("loss_defense", "")).strip() else "UNKNOWN"


def _review_notes(
    memo: dict[str, object],
    checklist: pd.Series,
    research: pd.Series,
    filing_note: str,
    capital_note: str,
) -> str:
    parts = [
        filing_note,
        capital_note,
        f"checklist_status={checklist.get('checklist_status', 'UNKNOWN')}",
        f"automatic_blockers={checklist.get('automatic_blockers', '')}",
        f"research_score={_number(research.get('research_score')):.2f}",
        f"expected_20d_return={_number(research.get('expected_20d_return')):.3f}",
        f"upside_probability={_number(research.get('upside_probability')):.3f}",
        f"PER={_number(research.get('per')):.2f}",
        f"PBR={_number(research.get('pbr')):.2f}",
        f"loss_defense={memo.get('loss_defense', '')}",
        "capital_plan requires final human confirmation",
    ]
    return "; ".join(str(part) for part in parts if str(part).strip())


def _render_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Manual Review Draft",
        "",
        "This is a decision-support draft only. Do not copy `PASS_CANDIDATE` into `configs/manual_review.actual.csv` without human confirmation.",
        "",
        "| Symbol | Company | Filing | Earnings | Driver | Valuation | Loss Rule | Capital Plan | Action |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            "| {symbol} | {company} | {filing} | {earnings} | {driver} | {valuation} | {loss_rule} | {capital_plan} | {action} |".format(
                symbol=row.symbol,
                company=row.company_name,
                filing=row.filing_review,
                earnings=row.earnings_review,
                driver=row.business_driver_review,
                valuation=row.valuation_review,
                loss_rule=row.loss_rule_review,
                capital_plan=row.capital_plan_review,
                action=row.recommended_actual_action,
            )
        )
    for row in report.itertuples(index=False):
        lines.extend(
            [
                "",
                f"## {row.symbol} {row.company_name}",
                f"- Filing review: {row.filing_review}",
                f"- Earnings review: {row.earnings_review}",
                f"- Business driver review: {row.business_driver_review}",
                f"- Valuation review: {row.valuation_review}",
                f"- Loss rule review: {row.loss_rule_review}",
                f"- Capital plan review: {row.capital_plan_review}",
                f"- Notes: {row.review_notes}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
