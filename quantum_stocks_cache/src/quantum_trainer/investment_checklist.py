from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "symbol",
    "company_name",
    "filter_status",
    "research_score",
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
    "fundamental_score",
}


@dataclass(frozen=True)
class InvestmentChecklistOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame


def run_investment_checklist(
    candidate_briefs_csv: Path | str,
    output_dir: Path | str,
) -> InvestmentChecklistOutput:
    source_path = Path(candidate_briefs_csv).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Candidate briefs CSV not found: {source_path}")

    source = pd.read_csv(source_path)
    missing = sorted(REQUIRED_COLUMNS.difference(source.columns))
    if missing:
        raise ValueError(f"Candidate briefs CSV missing required columns: {missing}")

    report = source.copy().reset_index(drop=True)
    report["automatic_passes"] = report.apply(_automatic_passes, axis=1)
    report["automatic_blockers"] = report.apply(_automatic_blockers, axis=1)
    report["automatic_pass_count"] = report["automatic_passes"].map(_count_items)
    report["manual_checklist"] = report.apply(_manual_checklist, axis=1)
    report["checklist_status"] = report.apply(_checklist_status, axis=1)

    output_root = Path(output_dir).resolve() / "investment_checklist"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "investment_checklist.csv"
    markdown_path = output_root / "investment_checklist.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")

    return InvestmentChecklistOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        report=report,
    )


def _automatic_passes(row: pd.Series) -> str:
    checks: list[str] = []
    if str(row["filter_status"]) == "PRIORITY_RESEARCH":
        checks.append("리서치 우선순위 통과")
    if str(row["decision"]) == "BUY_READY":
        checks.append("alpha decision BUY_READY")
    if _number(row["research_score"]) >= 80:
        checks.append("research_score 80 이상")
    if _number(row["expected_20d_return"]) > 0:
        checks.append("기대 20일 수익률 양수")
    if _number(row["upside_probability"]) >= 0.6:
        checks.append("상승 확률 60% 이상")
    if _number(row["return_20d"]) > 0:
        checks.append("20일 모멘텀 양수")
    if _number(row["ma20_gap"]) > 0:
        checks.append("SMA20 상단 유지")
    if _number(row["drawdown_20d"]) >= -0.10:
        checks.append("20일 낙폭 10% 이내")
    if str(row["fundamental_view"]) != "FUNDAMENTAL_WEAK":
        checks.append("재무 view 약세 아님")
    if _number(row["debt_ratio"]) <= 1.0:
        checks.append("부채비율 100% 이하")
    return "; ".join(checks)


def _automatic_blockers(row: pd.Series) -> str:
    blockers: list[str] = []
    if str(row["filter_status"]) != "PRIORITY_RESEARCH":
        blockers.append(f"filter_status={row['filter_status']}")
    if str(row["decision"]) != "BUY_READY":
        blockers.append(f"decision={row['decision']}")
    if _number(row["upside_probability"]) < 0.6:
        blockers.append("상승 확률 60% 미만")
    if _number(row["ma20_gap"]) <= 0:
        blockers.append("SMA20 하회")
    if str(row["fundamental_view"]) == "FUNDAMENTAL_WEAK":
        blockers.append("재무 view 약세")
    if _number(row["debt_ratio"]) > 1.0:
        blockers.append("부채비율 100% 초과")
    if _number(row["per"]) >= 35 or _number(row["pbr"]) >= 3:
        blockers.append("밸류에이션 부담")
    if _number(row["drawdown_20d"]) < -0.10:
        blockers.append("20일 낙폭 10% 초과")
    return "; ".join(blockers) if blockers else "없음"


def _manual_checklist(row: pd.Series) -> str:
    items = [
        "최근 공시 확인",
        "최근 실적 발표와 컨센서스 방향 확인",
        "사업부별 성장 동력과 이익률 훼손 요인 확인",
        "경쟁사 대비 밸류에이션 비교",
        "손절/보류 조건을 투자 전에 문서화",
        "목표 비중은 별도 order sizing에서만 계산",
        "실제 주문 전 current_weights와 현금 비중 재확인",
    ]
    if _number(row["per"]) >= 35 or _number(row["pbr"]) >= 3:
        items.append("높은 PER/PBR을 정당화할 실적 가시성 확인")
    if _number(row["debt_ratio"]) > 1:
        items.append("부채비율 부담과 현금흐름 확인")
    return "; ".join(items)


def _checklist_status(row: pd.Series) -> str:
    blockers = str(row["automatic_blockers"])
    if blockers == "없음":
        return "READY_FOR_MANUAL_REVIEW"
    return "NEEDS_MANUAL_REVIEW"


def _render_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Investment Checklist",
        "",
        "이 리포트는 투자 전 수동 검토를 돕는 체크리스트이며 실제 주문 실행 문서가 아닙니다.",
        "",
        "| Rank | Candidate | Status | Blockers |",
        "|---:|---|---|---|",
    ]
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        lines.append(
            f"| {rank} | {row.symbol} {row.company_name} | {row.checklist_status} | {row.automatic_blockers} |"
        )
    lines.append("")
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        lines.extend(
            [
                f"## {rank}. {row.symbol} {row.company_name}",
                "",
                f"- Checklist status: {row.checklist_status}",
                f"- Research score: {float(row.research_score):.2f}",
                "",
                "### 자동 체크",
                *[f"- {item}" for item in _split_items(row.automatic_passes)],
                "",
                "### 자동 차단/주의",
                *[f"- {item}" for item in _split_items(row.automatic_blockers)],
                "",
                "### 수동 체크리스트",
                *[f"- {item}" for item in _split_items(row.manual_checklist)],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _split_items(value: object) -> list[str]:
    text = str(value)
    return [item.strip() for item in text.split(";") if item.strip()]


def _count_items(value: object) -> int:
    return len(_split_items(value))


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
