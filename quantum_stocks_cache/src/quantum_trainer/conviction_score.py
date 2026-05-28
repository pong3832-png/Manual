from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd


MARKET_WATCH_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "research_score",
    "watch_status",
    "watch_event",
    "focus_reason",
    "expected_20d_return",
    "upside_probability",
    "return_20d",
    "ma20_gap",
    "drawdown_20d",
    "focus_persistence_count",
    "persistence_label",
    "persistence_score",
    "fundamental_view",
}

COMPANY_RESEARCH_COLUMNS = {
    "symbol",
    "per",
    "pbr",
    "debt_ratio",
    "fundamental_score",
    "fundamental_view",
    "why_summary",
}


@dataclass(frozen=True)
class ConvictionScoreOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, float | int | str]


def run_conviction_score(
    market_watch_csv: Path | str,
    company_research_csv: Path | str,
    output_dir: Path | str,
    include_labels: Sequence[str] = ("PERSISTENT_FOCUS",),
) -> ConvictionScoreOutput:
    if not include_labels:
        raise ValueError("include_labels must not be empty.")

    market_watch = _load_csv(market_watch_csv, MARKET_WATCH_COLUMNS, "market watch")
    company_research = _load_csv(company_research_csv, COMPANY_RESEARCH_COLUMNS, "company research")
    included = {str(label) for label in include_labels}
    candidates = market_watch.loc[market_watch["persistence_label"].isin(included)].copy()

    merged = candidates.merge(
        company_research.loc[
            :, ["symbol", "per", "pbr", "debt_ratio", "fundamental_score", "fundamental_view", "why_summary"]
        ],
        on="symbol",
        how="left",
        suffixes=("", "_research"),
    )
    if "fundamental_view_research" in merged.columns:
        merged["fundamental_view"] = merged["fundamental_view_research"].where(
            merged["fundamental_view_research"].astype(str) != "", merged["fundamental_view"]
        )
        merged = merged.drop(columns=["fundamental_view_research"])

    if merged.empty:
        report = _empty_report()
    else:
        report = merged.copy()
        report["valuation_penalty"] = report.apply(_valuation_penalty, axis=1)
        report["risk_penalty"] = report.apply(_risk_penalty, axis=1)
        report["conviction_score"] = report.apply(_conviction_score, axis=1)
        report["conviction_tier"] = report.apply(_conviction_tier, axis=1)
        report["conviction_reasons"] = report.apply(_conviction_reasons, axis=1)
        report["conviction_risks"] = report.apply(_conviction_risks, axis=1)
        report = report.sort_values(
            ["conviction_score", "research_score"], ascending=[False, False]
        ).reset_index(drop=True)

    output_root = Path(output_dir).resolve() / "conviction"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "conviction_score.csv"
    markdown_path = output_root / "conviction_score.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary: dict[str, float | int | str] = {
        "candidate_count": int(len(report)),
        "high_conviction_count": int(
            (report["conviction_tier"] == "HIGH_CONVICTION_RESEARCH").sum()
            if "conviction_tier" in report.columns
            else 0
        ),
        "include_labels": ",".join(sorted(included)),
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")

    return ConvictionScoreOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
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


def _empty_report() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "symbol",
            "company_name",
            "sector",
            "conviction_score",
            "conviction_tier",
            "conviction_reasons",
            "conviction_risks",
            "persistence_label",
        ]
    )


def _conviction_score(row: pd.Series) -> float:
    expected_return_score = min(max(_number(row.get("expected_20d_return")) * 500.0, 0.0), 100.0)
    trend_score = (
        min(max(_number(row.get("return_20d")) * 120.0, 0.0), 100.0) * 0.55
        + min(max(_number(row.get("ma20_gap")) * 250.0, 0.0), 100.0) * 0.45
    )
    raw = (
        _number(row.get("research_score")) * 0.25
        + _number(row.get("persistence_score")) * 0.30
        + _number(row.get("upside_probability")) * 100.0 * 0.15
        + expected_return_score * 0.10
        + trend_score * 0.10
        + _number(row.get("fundamental_score")) * 0.10
    )
    score = raw - _number(row.get("valuation_penalty")) - _number(row.get("risk_penalty"))
    return round(min(max(score, 0.0), 100.0), 6)


def _conviction_tier(row: pd.Series) -> str:
    score = _number(row.get("conviction_score"))
    label = str(row.get("persistence_label"))
    if label == "PERSISTENT_FOCUS" and score >= 75:
        return "HIGH_CONVICTION_RESEARCH"
    if score >= 60:
        return "DEVELOPING_CONVICTION"
    return "WATCH_CONVICTION"


def _valuation_penalty(row: pd.Series) -> float:
    penalty = 0.0
    if _number(row.get("per")) >= 35:
        penalty += 8.0
    if _number(row.get("pbr")) >= 3:
        penalty += 8.0
    return penalty


def _risk_penalty(row: pd.Series) -> float:
    penalty = 0.0
    if str(row.get("fundamental_view")) == "FUNDAMENTAL_WEAK":
        penalty += 10.0
    if _number(row.get("debt_ratio")) > 1.0:
        penalty += 8.0
    if _number(row.get("drawdown_20d")) < -0.10:
        penalty += 6.0
    return penalty


def _conviction_reasons(row: pd.Series) -> str:
    reasons: list[str] = []
    if str(row.get("persistence_label")) in {"PERSISTENT_FOCUS", "BUILDING_FOCUS"}:
        reasons.append(f"{row.get('persistence_label')}({int(_number(row.get('focus_persistence_count')))})")
    if _number(row.get("research_score")) >= 75:
        reasons.append("research_score high")
    if _number(row.get("upside_probability")) >= 0.6:
        reasons.append("upside probability ok")
    if _number(row.get("ma20_gap")) > 0:
        reasons.append("above SMA20")
    if str(row.get("fundamental_view")) != "FUNDAMENTAL_WEAK":
        reasons.append("fundamental view acceptable")
    return "; ".join(reasons) if reasons else "conviction reasons are limited"


def _conviction_risks(row: pd.Series) -> str:
    risks: list[str] = []
    if _number(row.get("valuation_penalty")) > 0:
        risks.append("밸류에이션 부담")
    if _number(row.get("risk_penalty")) > 0:
        risks.append("risk penalty exists")
    if str(row.get("persistence_label")) != "PERSISTENT_FOCUS":
        risks.append("not persistent yet")
    if _number(row.get("drawdown_20d")) < -0.10:
        risks.append("drawdown deep")
    return "; ".join(risks) if risks else "major quantified risk not flagged"


def _render_markdown(report: pd.DataFrame, summary: dict[str, float | int | str]) -> str:
    lines = [
        "# Conviction Score",
        "",
        "이 리포트는 지속 후보의 리서치 확신도를 정리합니다. 실제 주문 실행 문서가 아닙니다.",
        "",
        "## Summary",
        f"- Candidate count: {summary['candidate_count']}",
        f"- High conviction count: {summary['high_conviction_count']}",
        f"- Included labels: {summary['include_labels']}",
        "",
        "| Rank | Symbol | Company | Tier | Score | Persistence | Risks |",
        "|---:|---|---|---|---:|---|---|",
    ]
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        lines.append(
            f"| {rank} | {row.symbol} | {row.company_name} | {row.conviction_tier} | "
            f"{float(row.conviction_score):.2f} | {row.persistence_label} | {row.conviction_risks} |"
        )
    lines.append("")
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        lines.extend(
            [
                f"## {rank}. {row.symbol} {row.company_name}",
                "",
                f"- Conviction tier: {row.conviction_tier}",
                f"- Conviction score: {float(row.conviction_score):.2f}",
                f"- Persistence: {row.persistence_label} ({int(float(row.focus_persistence_count))})",
                f"- Research score: {float(row.research_score):.2f}",
                f"- PER/PBR: {_fmt(row.per)} / {_fmt(row.pbr)}",
                "",
                "### Conviction Reasons",
                f"- {row.conviction_reasons}",
                "",
                "### Risks",
                f"- {row.conviction_risks}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fmt(value: object) -> str:
    return f"{_number(value):.2f}"
