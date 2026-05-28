from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "symbol",
    "company_name",
    "research_score",
    "research_view",
    "decision",
    "fundamental_view",
    "why_summary",
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
class ResearchFilterOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame


def run_research_filter(
    company_research_csv: Path | str,
    output_dir: Path | str,
    top_n: int = 5,
) -> ResearchFilterOutput:
    if top_n <= 0:
        raise ValueError("top_n must be greater than 0.")

    source_path = Path(company_research_csv).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Company research CSV not found: {source_path}")

    source = pd.read_csv(source_path)
    missing = sorted(REQUIRED_COLUMNS.difference(source.columns))
    if missing:
        raise ValueError(f"Company research CSV missing required columns: {missing}")

    ranked = source.sort_values("research_score", ascending=False).reset_index(drop=True).copy()
    ranked["filter_status"] = ranked.apply(_filter_status, axis=1)
    selected = (ranked.index < top_n) | (ranked["filter_status"] == "PRIORITY_RESEARCH")
    report = ranked.loc[selected].reset_index(drop=True).copy()
    report["filter_status"] = report.apply(_filter_status, axis=1)
    report["buy_case"] = report.apply(_buy_case, axis=1)
    report["wait_reason"] = report.apply(_wait_reason, axis=1)
    report["exclusion_condition"] = report.apply(_exclusion_condition, axis=1)
    report["next_action"] = report.apply(_next_action, axis=1)

    output_root = Path(output_dir).resolve() / "research_filter"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "research_filter.csv"
    markdown_path = output_root / "research_filter.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")

    return ResearchFilterOutput(csv_path=csv_path, markdown_path=markdown_path, report=report)


def _filter_status(row: pd.Series) -> str:
    decision = str(row["decision"])
    research_view = str(row["research_view"])
    fundamental_view = str(row["fundamental_view"])
    if decision == "AVOID" or research_view == "AVOID_FOR_NOW":
        return "EXCLUDE_UNTIL_RESET"
    if (
        research_view == "RESEARCH_CANDIDATE"
        and decision == "BUY_READY"
        and fundamental_view != "FUNDAMENTAL_WEAK"
    ):
        return "PRIORITY_RESEARCH"
    return "WATCH_FOR_CONFIRMATION"


def _buy_case(row: pd.Series) -> str:
    reasons: list[str] = []
    why_summary = str(row["why_summary"])
    if "ALPHA_BUY_READY" in why_summary:
        reasons.append("alpha timing이 BUY_READY입니다")
    if "POSITIVE_EXPECTED_RETURN" in why_summary:
        reasons.append(f"20일 기대수익률이 {_pct(row['expected_20d_return'])}입니다")
    if "UPSIDE_PROBABILITY_OK" in why_summary or _number(row["upside_probability"]) >= 0.6:
        reasons.append(f"상승 확률이 {_pct(row['upside_probability'])}입니다")
    if "POSITIVE_20D_MOMENTUM" in why_summary or _number(row["return_20d"]) > 0:
        reasons.append(f"20일 모멘텀이 {_pct(row['return_20d'])}입니다")
    if "ABOVE_SMA20" in why_summary or _number(row["ma20_gap"]) > 0:
        reasons.append(f"SMA20 대비 {_pct(row['ma20_gap'])} 위에 있습니다")
    if str(row["fundamental_view"]) != "FUNDAMENTAL_WEAK":
        reasons.append(f"재무 상태는 {row['fundamental_view']}입니다")
    return "; ".join(reasons) if reasons else "데이터상 적극 투자 논리는 아직 약합니다"


def _wait_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    if str(row["fundamental_view"]) == "FUNDAMENTAL_WEAK":
        reasons.append("재무 점수 보강 확인 필요")
    if str(row["research_view"]) != "RESEARCH_CANDIDATE":
        reasons.append(f"research_view가 {row['research_view']}입니다")
    if str(row["decision"]) != "BUY_READY":
        reasons.append(f"alpha decision이 {row['decision']}입니다")
    if _number(row["research_score"]) < 70:
        reasons.append("research_score가 70 미만입니다")
    if _number(row["upside_probability"]) < 0.6:
        reasons.append("상승 확률이 60% 미만입니다")
    return "; ".join(reasons) if reasons else "대기 사유는 크지 않지만 사업/공시 수동 확인 필요"


def _exclusion_condition(row: pd.Series) -> str:
    decision = str(row["decision"])
    research_view = str(row["research_view"])
    if decision == "AVOID" or research_view == "AVOID_FOR_NOW":
        return f"decision={decision} 또는 research_view={research_view}가 유지되면 제외"
    return "decision이 AVOID로 바뀌거나 SMA20 이탈/상승 확률 훼손 시 제외"


def _next_action(row: pd.Series) -> str:
    status = str(row["filter_status"])
    if status == "PRIORITY_RESEARCH":
        return "사업 구조, 최근 공시, 실적 컨퍼런스콜을 수동 확인"
    if status == "WATCH_FOR_CONFIRMATION":
        return "재무 점수, 추세 지속성, 밸류에이션 부담 완화 여부를 관찰"
    return "다음 리포트에서 decision/research_view가 회복될 때까지 제외"


def _render_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Candidate Research Filter",
        "",
        "이 리포트는 실제 주문 실행 리포트가 아닙니다. 데이터 기반 리서치 우선순위와 제외 조건만 정리합니다.",
        "",
        "| Rank | Symbol | Company | Status | Score | Decision | Fundamental |",
        "|---:|---|---|---|---:|---|---|",
    ]
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        lines.append(
            "| {rank} | {symbol} | {company} | {status} | {score:.2f} | {decision} | {fundamental} |".format(
                rank=rank,
                symbol=row.symbol,
                company=row.company_name,
                status=row.filter_status,
                score=float(row.research_score),
                decision=row.decision,
                fundamental=row.fundamental_view,
            )
        )
    lines.append("")
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        lines.extend(
            [
                f"## {rank}. {row.symbol} {row.company_name}",
                "",
                f"- Filter status: {row.filter_status}",
                f"- Research score: {float(row.research_score):.2f}",
                f"- PER/PBR: {_fmt(row.per)} / {_fmt(row.pbr)}",
                f"- Debt ratio: {_pct(row.debt_ratio)}",
                "",
                "### 투자 논리",
                f"- {row.buy_case}",
                "",
                "### 대기 사유",
                f"- {row.wait_reason}",
                "",
                "### 제외 조건",
                f"- {row.exclusion_condition}",
                "",
                "### 다음 확인",
                f"- {row.next_action}",
                "",
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


def _fmt(value: object) -> str:
    return f"{_number(value):.2f}"
