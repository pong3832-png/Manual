from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


CONFIRM_TOKEN = "I_CONFIRM_MANUAL_REVIEW"

REVIEW_STATUS_COLUMNS = [
    "filing_review",
    "earnings_review",
    "business_driver_review",
    "valuation_review",
    "loss_rule_review",
    "capital_plan_review",
]

PROPOSAL_COLUMNS = {
    "symbol",
    *REVIEW_STATUS_COLUMNS,
    "review_notes",
    "proposal_status",
    "approval_required",
    "apply_target",
    "source_action",
}

ACTUAL_COLUMNS = [
    "symbol",
    *REVIEW_STATUS_COLUMNS,
    "review_notes",
]

PLAN_COLUMNS = [
    "symbol",
    "apply_mode",
    "ready_to_apply",
    "confirm_required",
    "actual_config_written",
    "actual_output_csv",
    "blocker",
    "candidate_source",
]


@dataclass(frozen=True)
class ManualReviewApplyPlanOutput:
    plan_csv_path: Path
    candidate_csv_path: Path
    markdown_path: Path
    plan: pd.DataFrame
    candidate: pd.DataFrame


def run_manual_review_apply_plan(
    manual_review_proposal_csv: Path | str,
    output_dir: Path | str,
    actual_output_csv: Path | str,
    confirm_token: str | None = None,
) -> ManualReviewApplyPlanOutput:
    proposal_path = Path(manual_review_proposal_csv).resolve()
    actual_path = Path(actual_output_csv).resolve()
    proposal = _load_csv(proposal_path, PROPOSAL_COLUMNS, "manual review proposal")
    candidate = _build_candidate(proposal)

    can_write = _all_ready(proposal) and confirm_token == CONFIRM_TOKEN
    actual_matches = _actual_matches_candidate(actual_path, candidate)
    output_root = Path(output_dir).resolve() / "decision_gate"
    output_root.mkdir(parents=True, exist_ok=True)

    if can_write:
        actual_path.parent.mkdir(parents=True, exist_ok=True)
        candidate.to_csv(actual_path, index=False, encoding="utf-8-sig")
        actual_written = "YES"
        apply_mode = "CONFIRMED_WRITE"
    elif actual_matches:
        actual_written = "YES"
        apply_mode = "EXISTING_ACTUAL"
    else:
        actual_written = "NO"
        apply_mode = "DRY_RUN"

    plan = _build_plan(
        proposal=proposal,
        proposal_path=proposal_path,
        actual_output_csv=actual_path,
        actual_config_written=actual_written,
        apply_mode=apply_mode,
    )

    plan_csv_path = output_root / "manual_review_apply_plan.csv"
    candidate_csv_path = output_root / "manual_review_actual_candidate.csv"
    markdown_path = output_root / "manual_review_apply_plan.md"
    plan.to_csv(plan_csv_path, index=False, encoding="utf-8-sig")
    candidate.to_csv(candidate_csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(plan, candidate), encoding="utf-8")

    return ManualReviewApplyPlanOutput(
        plan_csv_path=plan_csv_path,
        candidate_csv_path=candidate_csv_path,
        markdown_path=markdown_path,
        plan=plan,
        candidate=candidate,
    )


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame


def _actual_matches_candidate(actual_path: Path, candidate: pd.DataFrame) -> bool:
    if not actual_path.exists():
        return False
    actual = _load_csv(actual_path, set(ACTUAL_COLUMNS), "actual manual review")
    compare_columns = ["symbol", *REVIEW_STATUS_COLUMNS]
    left = actual.loc[:, compare_columns].copy().sort_values("symbol").reset_index(drop=True)
    right = candidate.loc[:, compare_columns].copy().sort_values("symbol").reset_index(drop=True)
    for column in REVIEW_STATUS_COLUMNS:
        left[column] = left[column].map(_status)
        right[column] = right[column].map(_status)
    return left.equals(right)


def _build_candidate(proposal: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in proposal.to_dict(orient="records"):
        notes = "; ".join(
            part
            for part in [
                str(row.get("review_notes", "")).strip(),
                "SOURCE=manual_review_proposal",
                "FINAL_USER_CONFIRMATION_REQUIRED",
            ]
            if part
        )
        rows.append(
            {
                "symbol": str(row["symbol"]),
                **{column: _status(row[column]) for column in REVIEW_STATUS_COLUMNS},
                "review_notes": notes,
            }
        )
    return pd.DataFrame(rows, columns=ACTUAL_COLUMNS)


def _build_plan(
    proposal: pd.DataFrame,
    proposal_path: Path,
    actual_output_csv: Path,
    actual_config_written: str,
    apply_mode: str,
) -> pd.DataFrame:
    rows = []
    for row in proposal.to_dict(orient="records"):
        ready = _row_ready(row)
        rows.append(
            {
                "symbol": str(row["symbol"]),
                "apply_mode": apply_mode,
                "ready_to_apply": "YES" if ready else "NO",
                "confirm_required": "YES",
                "actual_config_written": actual_config_written if ready else "NO",
                "actual_output_csv": str(actual_output_csv),
                "blocker": "" if actual_config_written == "YES" and ready else _blocker(row),
                "candidate_source": proposal_path.name,
            }
        )
    return pd.DataFrame(rows, columns=PLAN_COLUMNS)


def _row_ready(row: dict[str, object]) -> bool:
    return (
        str(row.get("proposal_status", "")).upper() == "READY_FOR_USER_CONFIRMATION"
        and str(row.get("approval_required", "")).upper() == "YES"
    )


def _all_ready(proposal: pd.DataFrame) -> bool:
    return bool(len(proposal)) and all(_row_ready(row) for row in proposal.to_dict(orient="records"))


def _blocker(row: dict[str, object]) -> str:
    if not _row_ready(row):
        return "proposal not ready for actual config"
    return "waiting for explicit user confirmation"


def _status(value: object) -> str:
    status = str(value).strip().upper()
    if status in {"PASS", "FAIL", "UNKNOWN"}:
        return status
    return "UNKNOWN"


def _render_markdown(plan: pd.DataFrame, candidate: pd.DataFrame) -> str:
    lines = [
        "# Manual Review Apply Plan",
        "",
        "This is an audit plan for manual review config. It does not place orders.",
        "",
        "| Symbol | Mode | Ready | Confirm Required | Actual Written | Target | Blocker |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in plan.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.apply_mode} | {row.ready_to_apply} | {row.confirm_required} | "
            f"{row.actual_config_written} | {row.actual_output_csv} | {row.blocker} |"
        )
    lines.extend(["", "## Candidate Rows", ""])
    for row in candidate.itertuples(index=False):
        lines.extend(
            [
                f"### {row.symbol}",
                f"- Filing: {row.filing_review}",
                f"- Earnings: {row.earnings_review}",
                f"- Business driver: {row.business_driver_review}",
                f"- Valuation: {row.valuation_review}",
                f"- Loss rule: {row.loss_rule_review}",
                f"- Capital plan: {row.capital_plan_review}",
                f"- Notes: {row.review_notes}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
