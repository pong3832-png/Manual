from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


CONVICTION_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "conviction_score",
    "conviction_tier",
    "persistence_label",
    "conviction_reasons",
    "conviction_risks",
    "expected_20d_return",
    "upside_probability",
    "ma20_gap",
    "drawdown_20d",
    "per",
    "pbr",
}

CHECKLIST_COLUMNS = {
    "symbol",
    "checklist_status",
    "automatic_blockers",
    "manual_checklist",
}


@dataclass(frozen=True)
class ProfitFocusOutput:
    csv_path: Path
    markdown_path: Path
    # One-page operator view: one top candidate, wait reasons, and loss guards.
    today_focus_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_profit_focus(
    conviction_csv: Path | str,
    checklist_csv: Path | str,
    output_dir: Path | str,
    max_core: int = 3,
) -> ProfitFocusOutput:
    if max_core <= 0:
        raise ValueError("max_core must be greater than 0.")

    conviction = _load_csv(conviction_csv, CONVICTION_COLUMNS, "conviction")
    checklist = _load_csv(checklist_csv, CHECKLIST_COLUMNS, "investment checklist")
    checklist = checklist.drop_duplicates(subset=["symbol"]).loc[
        :, ["symbol", "checklist_status", "automatic_blockers", "manual_checklist"]
    ]
    report = conviction.merge(checklist, on="symbol", how="left")
    report[["checklist_status", "automatic_blockers", "manual_checklist"]] = report[
        ["checklist_status", "automatic_blockers", "manual_checklist"]
    ].fillna("")

    report["profit_focus_status"] = report.apply(_profit_focus_status, axis=1)
    report = _cap_core_focus(report=report, max_core=max_core)
    report["why_profit_candidate"] = report.apply(_why_profit_candidate, axis=1)
    report["why_not_now"] = report.apply(_why_not_now, axis=1)
    report["invalidation_rule"] = report.apply(_invalidation_rule, axis=1)
    report["next_step"] = report.apply(_next_step, axis=1)
    report["sort_rank"] = report.apply(_sort_rank, axis=1)
    report = report.sort_values(["sort_rank", "conviction_score"], ascending=[False, False])
    report = report.drop(columns=["sort_rank"]).reset_index(drop=True)

    output_root = Path(output_dir).resolve() / "profit_focus"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "profit_focus.csv"
    markdown_path = output_root / "profit_focus.md"
    today_focus_path = output_root / "today_focus.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "core_count": int((report["profit_focus_status"] == "CORE_FOCUS").sum()),
        "wait_count": int((report["profit_focus_status"] == "WAIT_RISK").sum()),
        "needs_checklist_count": int((report["profit_focus_status"] == "NEEDS_CHECKLIST").sum()),
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    today_focus_path.write_text(_render_today_focus(report, summary), encoding="utf-8")

    return ProfitFocusOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        today_focus_path=today_focus_path,
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


def _profit_focus_status(row: pd.Series) -> str:
    checklist_status = str(row.get("checklist_status", ""))
    blockers = str(row.get("automatic_blockers", ""))
    risks = str(row.get("conviction_risks", ""))
    if not checklist_status:
        return "NEEDS_CHECKLIST"
    if checklist_status != "READY_FOR_MANUAL_REVIEW":
        return "WAIT_RISK"
    if blockers and blockers != "없음":
        return "WAIT_RISK"
    if "밸류에이션 부담" in risks:
        return "WAIT_RISK"
    if _number(row.get("conviction_score")) >= 65:
        return "CORE_FOCUS"
    return "WATCH_ONLY"


def _cap_core_focus(report: pd.DataFrame, max_core: int) -> pd.DataFrame:
    capped = report.copy()
    core = capped.loc[capped["profit_focus_status"] == "CORE_FOCUS"].sort_values(
        "conviction_score", ascending=False
    )
    overflow = core.iloc[max_core:]["symbol"].tolist()
    if overflow:
        capped.loc[capped["symbol"].isin(overflow), "profit_focus_status"] = "WATCH_ONLY"
    return capped


def _why_profit_candidate(row: pd.Series) -> str:
    reasons = [
        f"conviction_score={_number(row.get('conviction_score')):.2f}",
        f"persistence={row.get('persistence_label')}",
        f"expected_20d_return={_pct(row.get('expected_20d_return'))}",
        f"upside_probability={_pct(row.get('upside_probability'))}",
    ]
    if _number(row.get("ma20_gap")) > 0:
        reasons.append(f"SMA20 위 {_pct(row.get('ma20_gap'))}")
    return "; ".join(reasons)


def _why_not_now(row: pd.Series) -> str:
    status = str(row.get("profit_focus_status"))
    blockers = str(row.get("automatic_blockers", ""))
    risks = str(row.get("conviction_risks", ""))
    reasons: list[str] = []
    if status == "CORE_FOCUS":
        return "핵심 후보지만 실제 주문 전 수동 확인 필요"
    if status == "NEEDS_CHECKLIST":
        reasons.append("체크리스트 없음")
    if blockers and blockers != "없음":
        reasons.extend(_split_reasons(blockers))
    if risks and risks != "major quantified risk not flagged":
        reasons.extend(_split_reasons(risks))
    if _number(row.get("conviction_score")) < 65:
        reasons.append("conviction_score 65 미만")
    return "; ".join(dict.fromkeys(reasons)) if reasons else "보류 사유 없음"


def _invalidation_rule(row: pd.Series) -> str:
    return (
        "TODAY_FOCUS 이탈, SMA20 하회, conviction_score 60 미만, "
        "또는 체크리스트 자동 차단 발생 시 제외"
    )


def _next_step(row: pd.Series) -> str:
    status = str(row.get("profit_focus_status"))
    if status == "CORE_FOCUS":
        return "사업/공시 수동 확인 후 투자금이 생길 때만 order_sizer 검토"
    if status == "WAIT_RISK":
        return "리스크가 해소될 때까지 매수 후보에서 제외하고 관찰"
    if status == "NEEDS_CHECKLIST":
        return "candidate brief와 investment checklist를 먼저 생성"
    return "market_watch에서 유지 여부 관찰"


def _sort_rank(row: pd.Series) -> int:
    order = {
        "CORE_FOCUS": 4,
        "WAIT_RISK": 3,
        "NEEDS_CHECKLIST": 2,
        "WATCH_ONLY": 1,
    }
    return order.get(str(row.get("profit_focus_status")), 0)


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Profit Focus",
        "",
        "이 리포트는 수익 후보를 단순화해 보는 문서입니다. 실제 주문 실행 문서가 아닙니다.",
        "",
        "## Summary",
        f"- Core focus: {summary['core_count']}",
        f"- Wait risk: {summary['wait_count']}",
        f"- Needs checklist: {summary['needs_checklist_count']}",
        "",
        "## Core Focus",
    ]
    core = report.loc[report["profit_focus_status"] == "CORE_FOCUS"]
    if core.empty:
        lines.append("")
        lines.append("- No CORE_FOCUS candidate.")
    else:
        for row in core.itertuples(index=False):
            lines.extend(
                [
                    "",
                    f"### {row.symbol} {row.company_name}",
                    f"- Why: {row.why_profit_candidate}",
                    f"- Not now: {row.why_not_now}",
                    f"- Invalidate: {row.invalidation_rule}",
                    f"- Next: {row.next_step}",
                ]
            )
    lines.append("")
    lines.append("## Watch / Wait")
    for row in report.loc[report["profit_focus_status"] != "CORE_FOCUS"].itertuples(index=False):
        lines.extend(
            [
                "",
                f"### {row.symbol} {row.company_name}",
                f"- Status: {row.profit_focus_status}",
                f"- Why not now: {row.why_not_now}",
                f"- Next: {row.next_step}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_today_focus(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Today Focus",
        "",
        "목표는 수익 후보를 한 개로 좁히고, 손실 방어 조건을 먼저 확인하는 것입니다. 수익률 보장이나 주문 실행 문서가 아닙니다.",
        "",
        "## 오늘 1순위",
    ]

    core = report.loc[report["profit_focus_status"] == "CORE_FOCUS"]
    if core.empty:
        lines.extend(
            [
                "",
                "- 오늘 1순위 없음",
                "- 이유: 자동 기준을 통과한 CORE_FOCUS 후보가 없습니다.",
                "- 행동: 새로 사지 않고 market_watch와 checklist를 먼저 갱신합니다.",
            ]
        )
    else:
        top = core.iloc[0]
        lines.extend(
            [
                "",
                f"### {top['symbol']} {top['company_name']}",
                f"- 왜 후보인가: {top['why_profit_candidate']}",
                f"- 아직 매수 버튼을 누르지 않는다: {top['why_not_now']}",
                f"- 손실 방어: {top['invalidation_rule']}",
                f"- 오늘 확인: {top['next_step']}",
            ]
        )

    extra_core = core.iloc[1:]
    if not extra_core.empty:
        lines.append("")
        lines.append("## 추가 핵심 후보")
        for row in extra_core.itertuples(index=False):
            lines.extend(
                [
                    "",
                    f"### {row.symbol} {row.company_name}",
                    f"- 왜 후보인가: {row.why_profit_candidate}",
                    f"- 손실 방어: {row.invalidation_rule}",
                ]
            )

    lines.append("")
    lines.append("## 대기/제외")
    wait = report.loc[report["profit_focus_status"] != "CORE_FOCUS"]
    if wait.empty:
        lines.append("")
        lines.append("- 대기/제외 후보 없음")
    else:
        for row in wait.itertuples(index=False):
            lines.extend(
                [
                    "",
                    f"### {row.symbol} {row.company_name}",
                    f"- 상태: {row.profit_focus_status}",
                    f"- 대기 이유: {row.why_not_now}",
                    f"- 다음 행동: {row.next_step}",
                ]
            )

    lines.extend(
        [
            "",
            "## 운영 원칙",
            f"- 핵심 후보 수: {summary['core_count']}",
            "- 투자금이 정해지지 않았으면 매수 수량 계산보다 후보 유지 여부를 먼저 본다.",
            "- 손실 방어 조건이 발생하면 후보에서 제외하고 새 근거가 나올 때까지 기다린다.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _split_reasons(value: object) -> list[str]:
    return [item.strip() for item in str(value).split(";") if item.strip()]


def _pct(value: object) -> str:
    return f"{_number(value) * 100:.1f}%"
