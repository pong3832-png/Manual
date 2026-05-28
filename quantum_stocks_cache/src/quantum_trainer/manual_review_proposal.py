from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REVIEW_STATUS_COLUMNS = [
    "filing_review",
    "earnings_review",
    "business_driver_review",
    "valuation_review",
    "loss_rule_review",
    "capital_plan_review",
]

DRAFT_COLUMNS = {
    "symbol",
    "company_name",
    *REVIEW_STATUS_COLUMNS,
    "recommended_actual_action",
    "review_notes",
}

OUTPUT_COLUMNS = [
    "symbol",
    *REVIEW_STATUS_COLUMNS,
    "review_notes",
    "proposal_status",
    "approval_required",
    "apply_target",
    "source_action",
]


@dataclass(frozen=True)
class ManualReviewProposalOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame


def run_manual_review_proposal(
    manual_review_draft_csv: Path | str,
    output_dir: Path | str,
) -> ManualReviewProposalOutput:
    draft = _load_csv(Path(manual_review_draft_csv), DRAFT_COLUMNS, "manual review draft")
    report = _build_report(draft)

    output_root = Path(output_dir).resolve() / "decision_gate"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "manual_review_proposal.csv"
    markdown_path = output_root / "manual_review_proposal.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")

    for row in report.itertuples(index=False):
        code = str(row.symbol).split(".")[0]
        one = pd.DataFrame([row._asdict()], columns=OUTPUT_COLUMNS)
        one_csv = output_root / f"manual_review_proposal_{code}.csv"
        one_md = output_root / f"manual_review_proposal_{code}.md"
        one.to_csv(one_csv, index=False, encoding="utf-8-sig")
        one_md.write_text(_render_markdown(one), encoding="utf-8")

    return ManualReviewProposalOutput(csv_path=csv_path, markdown_path=markdown_path, report=report)


def _build_report(draft: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in draft.to_dict(orient="records"):
        proposed = {column: _proposal_status(row[column]) for column in REVIEW_STATUS_COLUMNS}
        proposal_status = _proposal_row_status(proposed)
        notes = "; ".join(
            part
            for part in [
                "USER_CONFIRMATION_REQUIRED",
                str(row.get("review_notes", "")).strip(),
            ]
            if part
        )
        rows.append(
            {
                "symbol": str(row["symbol"]),
                **proposed,
                "review_notes": notes,
                "proposal_status": proposal_status,
                "approval_required": "YES",
                "apply_target": "configs/manual_review.actual.csv",
                "source_action": str(row.get("recommended_actual_action", "")),
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _proposal_status(value: object) -> str:
    status = str(value).strip().upper()
    if status == "PASS_CANDIDATE":
        return "PASS"
    if status == "FAIL_CANDIDATE":
        return "FAIL"
    if status in {"PASS", "FAIL", "UNKNOWN"}:
        return status
    return "UNKNOWN"


def _proposal_row_status(row: dict[str, str]) -> str:
    values = list(row.values())
    if "FAIL" in values:
        return "BLOCKED_BY_DRAFT"
    if all(value == "PASS" for value in values):
        return "READY_FOR_USER_CONFIRMATION"
    return "INCOMPLETE_DRAFT"


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame


def _render_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Manual Review Proposal",
        "",
        "Do not copy automatically. This file is a user-confirmation proposal for `configs/manual_review.actual.csv`.",
        "",
        "| Symbol | Proposal | Approval | Filing | Earnings | Driver | Valuation | Loss Rule | Capital Plan |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.proposal_status} | {row.approval_required} | "
            f"{row.filing_review} | {row.earnings_review} | {row.business_driver_review} | "
            f"{row.valuation_review} | {row.loss_rule_review} | {row.capital_plan_review} |"
        )
    for row in report.itertuples(index=False):
        lines.extend(
            [
                "",
                f"## {row.symbol}",
                f"- Proposal status: {row.proposal_status}",
                f"- Approval required: {row.approval_required}",
                f"- Apply target: {row.apply_target}",
                f"- Source action: {row.source_action}",
                f"- Notes: {row.review_notes}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
