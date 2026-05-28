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

REVIEW_COLUMNS = {
    "symbol",
    "filing_review",
    "earnings_review",
    "business_driver_review",
    "valuation_review",
    "loss_rule_review",
    "capital_plan_review",
    "review_notes",
}

REVIEW_STATUS_COLUMNS = [
    "filing_review",
    "earnings_review",
    "business_driver_review",
    "valuation_review",
    "loss_rule_review",
    "capital_plan_review",
]


@dataclass(frozen=True)
class DecisionGateOutput:
    csv_path: Path
    markdown_path: Path
    template_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_decision_gate(
    investment_memo_csv: Path | str,
    output_dir: Path | str,
    manual_review_csv: Path | str | None = None,
) -> DecisionGateOutput:
    memo = _load_csv(investment_memo_csv, MEMO_COLUMNS, "investment memo")
    review = _load_review_csv(manual_review_csv) if manual_review_csv else _empty_review()
    report = _build_report(memo, review)

    output_root = Path(output_dir).resolve() / "decision_gate"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "decision_gate.csv"
    markdown_path = output_root / "decision_gate.md"
    template_path = output_root / "manual_review_template.csv"

    _write_template(memo, template_path)
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "ready_count": int((report["decision_gate_status"] == "READY_FOR_SIZING_REVIEW").sum()),
        "waiting_count": int((report["decision_gate_status"] == "WAITING_MANUAL_EVIDENCE").sum()),
        "blocked_count": int((report["decision_gate_status"] == "BLOCKED_BY_MANUAL_REVIEW").sum()),
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")

    return DecisionGateOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        template_path=template_path,
        report=report,
        summary=summary,
    )


def _load_csv(path: Path | str, required_columns: set[str], name: str) -> pd.DataFrame:
    csv_path = Path(path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {csv_path}")
    frame = pd.read_csv(csv_path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame


def _load_review_csv(path: Path | str) -> pd.DataFrame:
    return _load_csv(path, REVIEW_COLUMNS, "manual review")


def _empty_review() -> pd.DataFrame:
    return pd.DataFrame(columns=sorted(REVIEW_COLUMNS))


def _build_report(memo: pd.DataFrame, review: pd.DataFrame) -> pd.DataFrame:
    report = memo.merge(review, on="symbol", how="left")
    for column in REVIEW_STATUS_COLUMNS:
        report[column] = report[column].fillna("UNKNOWN").map(_normalize_review_status)
    report["review_notes"] = report["review_notes"].fillna("")
    report["decision_gate_status"] = report.apply(_decision_gate_status, axis=1)
    report["order_status"] = "NO_ORDER"
    report["gate_reason"] = report.apply(_gate_reason, axis=1)

    output_columns = [
        "symbol",
        "company_name",
        "sector",
        "decision_gate_status",
        "order_status",
        "gate_reason",
        *REVIEW_STATUS_COLUMNS,
        "review_notes",
        "core_thesis",
        "evidence",
        "risks",
        "loss_defense",
        "next_action",
    ]
    return report.loc[:, output_columns]


def _normalize_review_status(value: object) -> str:
    status = str(value).strip().upper()
    if status in {"PASS", "FAIL", "UNKNOWN"}:
        return status
    return "UNKNOWN"


def _decision_gate_status(row: pd.Series) -> str:
    statuses = [str(row[column]) for column in REVIEW_STATUS_COLUMNS]
    if "FAIL" in statuses:
        return "BLOCKED_BY_MANUAL_REVIEW"
    if all(status == "PASS" for status in statuses):
        return "READY_FOR_SIZING_REVIEW"
    return "WAITING_MANUAL_EVIDENCE"


def _gate_reason(row: pd.Series) -> str:
    waiting = [column for column in REVIEW_STATUS_COLUMNS if str(row[column]) == "UNKNOWN"]
    failed = [column for column in REVIEW_STATUS_COLUMNS if str(row[column]) == "FAIL"]
    if failed:
        return "manual review failed: " + ", ".join(failed)
    if waiting:
        return "수동 근거 대기: " + ", ".join(waiting)
    return "수동 근거 6개 PASS. 수량 계산 검토는 가능하지만 주문은 아님"


def _write_template(memo: pd.DataFrame, path: Path) -> None:
    rows = []
    for row in memo.itertuples(index=False):
        rows.append(
            {
                "symbol": row.symbol,
                "filing_review": "UNKNOWN",
                "earnings_review": "UNKNOWN",
                "business_driver_review": "UNKNOWN",
                "valuation_review": "UNKNOWN",
                "loss_rule_review": "UNKNOWN",
                "capital_plan_review": "UNKNOWN",
                "review_notes": "Fill PASS/FAIL/UNKNOWN after manual review.",
            }
        )
    pd.DataFrame(rows, columns=["symbol", *REVIEW_STATUS_COLUMNS, "review_notes"]).to_csv(
        path, index=False, encoding="utf-8-sig"
    )


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Decision Gate",
        "",
        "이 문서는 수동 확인 근거를 입력해 수량 계산 검토로 넘어갈 수 있는지 판단합니다. 실제 주문 문서가 아닙니다.",
        "",
        f"- Ready for sizing review: {summary['ready_count']}",
        f"- Waiting manual evidence: {summary['waiting_count']}",
        f"- Blocked by manual review: {summary['blocked_count']}",
        f"- Order status: {summary['order_status']}",
    ]

    if report.empty:
        lines.extend(["", "## No Memo", "", "- 투자 메모가 없어 decision gate를 만들지 않았습니다."])
    else:
        for row in report.itertuples(index=False):
            lines.extend(
                [
                    "",
                    f"## {row.symbol} {row.company_name}",
                    f"- Status: {row.decision_gate_status}",
                    f"- Order: {row.order_status}",
                    f"- Reason: {row.gate_reason}",
                    f"- Filing: {row.filing_review}",
                    f"- Earnings: {row.earnings_review}",
                    f"- Business driver: {row.business_driver_review}",
                    f"- Valuation: {row.valuation_review}",
                    f"- Loss rule: {row.loss_rule_review}",
                    f"- Capital plan: {row.capital_plan_review}",
                    f"- Notes: {row.review_notes}",
                    f"- Loss defense: {row.loss_defense}",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"
