from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "profit_focus_status",
    "conviction_score",
    "expected_20d_return",
    "upside_probability",
    "ma20_gap",
    "return_20d",
    "per",
    "pbr",
    "debt_ratio",
    "fundamental_view",
    "why_profit_candidate",
    "why_not_now",
    "invalidation_rule",
    "next_step",
    "checklist_status",
    "automatic_blockers",
    "manual_checklist",
    "conviction_risks",
}

OUTPUT_COLUMNS = [
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
]


@dataclass(frozen=True)
class InvestmentMemoOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_investment_memo(
    profit_focus_csv: Path | str,
    output_dir: Path | str,
    max_memos: int = 1,
) -> InvestmentMemoOutput:
    if max_memos <= 0:
        raise ValueError("max_memos must be greater than 0.")

    profit_focus = _load_profit_focus(profit_focus_csv)
    core = profit_focus.loc[profit_focus["profit_focus_status"] == "CORE_FOCUS"].copy()
    core = core.sort_values("conviction_score", ascending=False).head(max_memos)

    report = _build_report(core)

    output_root = Path(output_dir).resolve() / "investment_memo"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "investment_memo.csv"
    markdown_path = output_root / "investment_memo.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "memo_count": int(len(report)),
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")

    return InvestmentMemoOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        report=report,
        summary=summary,
    )


def _load_profit_focus(path: Path | str) -> pd.DataFrame:
    csv_path = Path(path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"Profit focus CSV not found: {csv_path}")
    frame = pd.read_csv(csv_path).fillna("")
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Profit focus CSV missing required columns: {missing}")
    return frame


def _build_report(core: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in core.to_dict(orient="records"):
        rows.append(
            {
                "symbol": row["symbol"],
                "company_name": row["company_name"],
                "sector": row["sector"],
                "memo_status": "THESIS_REVIEW",
                "order_status": "NO_ORDER",
                "core_thesis": _core_thesis(row),
                "evidence": _evidence(row),
                "risks": _risks(row),
                "manual_checks": row["manual_checklist"],
                "loss_defense": row["invalidation_rule"],
                "next_action": row["next_step"],
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _core_thesis(row: dict[str, object]) -> str:
    return (
        f"{row['company_name']}는 {row['why_profit_candidate']} 근거로 CORE_FOCUS에 올랐습니다. "
        f"주문으로 해석하지 않는다: {row['why_not_now']}."
    )


def _evidence(row: dict[str, object]) -> str:
    return (
        f"conviction_score={_number(row['conviction_score']):.2f}; "
        f"expected_20d_return={_pct(row['expected_20d_return'])}; "
        f"upside_probability={_pct(row['upside_probability'])}; "
        f"return_20d={_pct(row['return_20d'])}; "
        f"ma20_gap={_pct(row['ma20_gap'])}; "
        f"PER={_number(row['per']):.2f}; "
        f"PBR={_number(row['pbr']):.2f}; "
        f"debt_ratio={_pct(row['debt_ratio'])}; "
        f"fundamental_view={row['fundamental_view']}"
    )


def _risks(row: dict[str, object]) -> str:
    risks = _split_reasons(row.get("conviction_risks", ""))
    blockers = _split_reasons(row.get("automatic_blockers", ""))
    combined = [item for item in risks + blockers if item and item != "없음"]
    return "; ".join(dict.fromkeys(combined)) if combined else "자동 차단 리스크 없음"


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Investment Memo",
        "",
        "이 문서는 핵심 후보를 사람의 투자 논리 검토 대상으로 정리합니다. 실제 주문 문서가 아닙니다.",
        "",
        f"- Memo count: {summary['memo_count']}",
        f"- Order status: {summary['order_status']}",
    ]

    if report.empty:
        lines.extend(
            [
                "",
                "## No Core Candidate",
                "",
                "- CORE_FOCUS 후보가 없어 투자 메모를 만들지 않았습니다.",
            ]
        )
    else:
        for row in report.itertuples(index=False):
            lines.extend(
                [
                    "",
                    f"## {row.symbol} {row.company_name}",
                    "",
                    "### 핵심 판단",
                    f"- {row.core_thesis}",
                    "",
                    "### 근거",
                    f"- {row.evidence}",
                    "",
                    "### 리스크",
                    f"- {row.risks}",
                    "",
                    "### 수동 확인",
                    f"- {row.manual_checks}",
                    "",
                    "### 손실 방어",
                    f"- {row.loss_defense}",
                    "",
                    "### 다음 행동",
                    f"- {row.next_action}",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _pct(value: object) -> str:
    return f"{_number(value) * 100:.1f}%"


def _split_reasons(value: object) -> list[str]:
    return [item.strip() for item in str(value).split(";") if item.strip()]
