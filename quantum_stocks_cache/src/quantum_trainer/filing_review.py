from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_CHECK_COLUMNS = [
    "annual_report_review",
    "quarterly_report_review",
    "litigation_review",
    "contingent_liability_review",
    "related_party_review",
    "project_risk_review",
]
REQUIRED_COLUMNS = {"symbol", *REQUIRED_CHECK_COLUMNS}
VALID_REVIEW_VALUES = {"PASS", "FAIL", "UNKNOWN"}


@dataclass(frozen=True)
class FilingReviewOutput:
    report: pd.DataFrame
    csv_path: Path
    markdown_path: Path
    summary: dict[str, int]


def run_filing_review(input_csv: Path | str, output_dir: Path | str) -> FilingReviewOutput:
    review = _load_review_csv(input_csv)
    report = _build_report(review)
    output_root = Path(output_dir) / "filing_review"
    output_root.mkdir(parents=True, exist_ok=True)

    csv_path = output_root / "filing_review.csv"
    markdown_path = output_root / "filing_review.md"
    report.to_csv(csv_path, index=False)
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")

    summary = {
        "row_count": int(len(report)),
        "pass_count": int((report["filing_review_status"] == "FILING_REVIEW_PASS").sum()),
        "unknown_count": int((report["filing_review_status"] == "FILING_REVIEW_UNKNOWN").sum()),
        "fail_count": int((report["filing_review_status"] == "FILING_REVIEW_FAIL").sum()),
    }
    return FilingReviewOutput(report=report, csv_path=csv_path, markdown_path=markdown_path, summary=summary)


def build_filing_review_input_from_disclosures(symbol: str, disclosures: pd.DataFrame) -> pd.DataFrame:
    report_names = disclosures.get("report_nm", pd.Series(dtype=str)).astype(str)
    annual_reports = report_names[report_names.str.contains("사업보고서", regex=False)]
    quarterly_reports = report_names[
        report_names.str.contains("분기보고서", regex=False)
        | report_names.str.contains("반기보고서", regex=False)
    ]

    annual_value = "PASS" if not annual_reports.empty else "UNKNOWN"
    quarterly_value = "PASS" if not quarterly_reports.empty else "UNKNOWN"
    notes = _render_disclosure_prefill_notes(annual_reports=annual_reports, quarterly_reports=quarterly_reports)
    return pd.DataFrame(
        [
            {
                "symbol": symbol,
                "annual_report_review": annual_value,
                "quarterly_report_review": quarterly_value,
                "litigation_review": "UNKNOWN",
                "contingent_liability_review": "UNKNOWN",
                "related_party_review": "UNKNOWN",
                "project_risk_review": "UNKNOWN",
                "notes": notes,
            }
        ]
    )


def _load_review_csv(path: Path | str) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Filing review CSV not found: {csv_path}")
    review = pd.read_csv(csv_path).fillna("")
    missing = sorted(REQUIRED_COLUMNS.difference(review.columns))
    if missing:
        raise ValueError(f"Filing review CSV missing required columns: {missing}")

    for column in REQUIRED_CHECK_COLUMNS:
        review[column] = review[column].map(_normalize_review_value)
    return review


def _normalize_review_value(value: object) -> str:
    normalized = str(value).strip().upper() or "UNKNOWN"
    if normalized not in VALID_REVIEW_VALUES:
        raise ValueError(f"Review values must be PASS, FAIL, or UNKNOWN. Got: {value}")
    return normalized


def _build_report(review: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for row in review.itertuples(index=False):
        values = {column: getattr(row, column) for column in REQUIRED_CHECK_COLUMNS}
        failed = [column for column, value in values.items() if value == "FAIL"]
        unknown = [column for column, value in values.items() if value == "UNKNOWN"]
        if failed:
            status = "FILING_REVIEW_FAIL"
            manual_value = "FAIL"
            blocking = failed
        elif unknown:
            status = "FILING_REVIEW_UNKNOWN"
            manual_value = "UNKNOWN"
            blocking = unknown
        else:
            status = "FILING_REVIEW_PASS"
            manual_value = "PASS"
            blocking = []

        rows.append(
            {
                "symbol": str(row.symbol),
                "filing_review_status": status,
                "recommended_manual_review_value": manual_value,
                "blocking_checks": "; ".join(blocking),
                "notes": str(getattr(row, "notes", "")),
            }
        )
    return pd.DataFrame(rows)


def _render_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Filing Review",
        "",
        "This report supports the manual `filing_review` gate. It is not an order ticket.",
        "",
        f"- Row count: {len(report)}",
        f"- PASS: {int((report['filing_review_status'] == 'FILING_REVIEW_PASS').sum())}",
        f"- UNKNOWN: {int((report['filing_review_status'] == 'FILING_REVIEW_UNKNOWN').sum())}",
        f"- FAIL: {int((report['filing_review_status'] == 'FILING_REVIEW_FAIL').sum())}",
        "",
        "| Symbol | Status | Manual Review Value | Blocking Checks | Notes |",
        "|---|---|---|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.filing_review_status} | "
            f"{row.recommended_manual_review_value} | {row.blocking_checks or '-'} | {row.notes or '-'} |"
        )
    lines.append("")
    lines.append("Only copy `PASS` into `configs/manual_review.actual.csv` after human confirmation.")
    return "\n".join(lines)


def _render_disclosure_prefill_notes(annual_reports: pd.Series, quarterly_reports: pd.Series) -> str:
    parts: list[str] = []
    if not annual_reports.empty:
        parts.append(f"Found annual filing: {annual_reports.iloc[0]}")
    else:
        parts.append("Annual filing not found in fetched disclosure list.")
    if not quarterly_reports.empty:
        parts.append(f"Found quarterly/semiannual filing: {quarterly_reports.iloc[0]}")
    else:
        parts.append("Quarterly/semiannual filing not found in fetched disclosure list.")
    parts.append(
        "OpenDART list prefill only confirms filing existence; litigation, contingent liability, "
        "related-party, and project-risk checks remain UNKNOWN until human review."
    )
    return " ".join(parts)
