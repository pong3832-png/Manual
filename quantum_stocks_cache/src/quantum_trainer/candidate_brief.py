from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd


REQUIRED_COLUMNS = {
    "symbol",
    "company_name",
    "filter_status",
    "research_score",
    "decision",
    "fundamental_view",
    "buy_case",
    "wait_reason",
    "exclusion_condition",
    "next_action",
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
class CandidateBriefOutput:
    csv_path: Path
    index_path: Path
    brief_paths: list[Path]
    report: pd.DataFrame


def run_candidate_briefs(
    research_filter_csv: Path | str,
    output_dir: Path | str,
    statuses: Sequence[str] = ("PRIORITY_RESEARCH",),
    top_n: int | None = None,
) -> CandidateBriefOutput:
    if not statuses:
        raise ValueError("statuses must not be empty.")
    if top_n is not None and top_n <= 0:
        raise ValueError("top_n must be greater than 0 when provided.")

    source_path = Path(research_filter_csv).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Research filter CSV not found: {source_path}")

    source = pd.read_csv(source_path)
    missing = sorted(REQUIRED_COLUMNS.difference(source.columns))
    if missing:
        raise ValueError(f"Research filter CSV missing required columns: {missing}")

    selected_statuses = {str(status) for status in statuses}
    report = source.loc[source["filter_status"].isin(selected_statuses)].copy()
    report = report.sort_values("research_score", ascending=False).reset_index(drop=True)
    if top_n is not None:
        report = report.head(top_n).copy()
    report["brief_file"] = report.apply(_brief_filename, axis=1)

    output_root = Path(output_dir).resolve() / "candidate_briefs"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "candidate_briefs.csv"
    index_path = output_root / "candidate_briefs.md"

    brief_paths: list[Path] = []
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        brief_path = output_root / row.brief_file
        brief_path.write_text(_render_brief(rank, row), encoding="utf-8")
        brief_paths.append(brief_path)

    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    index_path.write_text(_render_index(report), encoding="utf-8")

    return CandidateBriefOutput(
        csv_path=csv_path,
        index_path=index_path,
        brief_paths=brief_paths,
        report=report,
    )


def _brief_filename(row: pd.Series) -> str:
    raw = f"{row['symbol']}_{row['company_name']}".replace(".", "_")
    safe = re.sub(r"[^A-Za-z0-9가-힣_-]+", "_", raw).strip("_")
    return f"{safe}.md"


def _render_index(report: pd.DataFrame) -> str:
    lines = [
        "# Candidate Brief Index",
        "",
        "이 인덱스는 개별 기업 리서치 브리프 목록입니다. 실제 주문 실행 문서가 아닙니다.",
        "",
        "| Rank | Candidate | Status | Score | Brief |",
        "|---:|---|---|---:|---|",
    ]
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        lines.append(
            f"| {rank} | {row.symbol} {row.company_name} | {row.filter_status} | "
            f"{float(row.research_score):.2f} | [{row.brief_file}](./{row.brief_file}) |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_brief(rank: int, row: object) -> str:
    return "\n".join(
        [
            f"# {row.symbol} {row.company_name}",
            "",
            "이 문서는 로컬 가격/재무/필터 리포트 기반 리서치 브리프입니다. 실제 주문 실행 문서가 아닙니다.",
            "",
            "## 요약 판단",
            f"- Rank: {rank}",
            f"- Filter status: {row.filter_status}",
            f"- Research score: {float(row.research_score):.2f}",
            f"- Decision: {row.decision}",
            f"- Fundamental view: {row.fundamental_view}",
            "",
            "## 핵심 데이터",
            f"- Expected 20D return: {_pct(row.expected_20d_return)}",
            f"- Upside probability: {_pct(row.upside_probability)}",
            f"- 20D momentum: {_pct(row.return_20d)}",
            f"- SMA20 gap: {_pct(row.ma20_gap)}",
            f"- 20D drawdown: {_pct(row.drawdown_20d)}",
            f"- PER / PBR: {_fmt(row.per)} / {_fmt(row.pbr)}",
            f"- Debt ratio: {_pct(row.debt_ratio)}",
            f"- Fundamental score: {_fmt(row.fundamental_score)}",
            "",
            "## 투자 논리",
            f"- {row.buy_case}",
            "",
            "## 리스크",
            f"- {row.wait_reason}",
            "",
            "## 매수 보류 조건",
            f"- {row.exclusion_condition}",
            "",
            "## 추가 확인 질문",
            f"- {row.next_action}",
            "- 최근 공시와 사업부별 실적이 위 데이터 논리를 뒷받침하는가?",
            "- 밸류에이션 부담을 정당화할 만큼 실적 개선 가시성이 있는가?",
            "- 현재 가격이 추세 이탈 없이 유지되는가?",
            "",
        ]
    ).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _pct(value: object) -> str:
    return f"{_number(value) * 100:.1f}%"


def _fmt(value: object) -> str:
    return f"{_number(value):.2f}"
