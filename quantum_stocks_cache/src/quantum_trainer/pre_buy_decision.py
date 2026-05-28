from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


PROFIT_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "profit_focus_status",
    "conviction_score",
    "expected_20d_return",
    "upside_probability",
    "ma20_gap",
    "return_20d",
    "why_profit_candidate",
    "why_not_now",
    "invalidation_rule",
    "next_step",
}

GATE_COLUMNS = {
    "symbol",
    "company_name",
    "decision_gate_status",
    "order_status",
    "gate_reason",
    "loss_defense",
}

RESEARCH_COLUMNS = {"symbol", "latest_price", "ma20_gap"}

FILING_RISK_COLUMNS = {
    "symbol",
    "risk_id",
    "risk_title",
    "fatal_risk",
    "gate_opinion",
    "monitoring_rule",
}

MANUAL_PROPOSAL_COLUMNS = {
    "symbol",
    "proposal_status",
    "approval_required",
    "apply_target",
}

CAPITAL_PLAN_COLUMNS = {
    "symbol",
    "amount_status",
    "order_status",
}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "decision_status",
    "order_status",
    "final_action",
    "manual_proposal_status",
    "capital_status",
    "readiness_blockers",
    "buy_reasons",
    "buy_ban_reasons",
    "entry_price_low",
    "entry_price_high",
    "staged_buy_plan",
    "stop_loss_rule",
    "next_review_date",
]


@dataclass(frozen=True)
class PreBuyDecisionOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int]


def run_pre_buy_decision(
    profit_focus_csv: Path | str,
    decision_gate_csv: Path | str,
    company_research_csv: Path | str,
    filing_risk_dir: Path | str,
    output_dir: Path | str,
    manual_proposal_csv: Path | str | None = None,
    capital_plan_dir: Path | str | None = None,
) -> PreBuyDecisionOutput:
    profit = _load_csv(Path(profit_focus_csv), PROFIT_COLUMNS, "profit focus")
    gate = _load_csv(Path(decision_gate_csv), GATE_COLUMNS, "decision gate")
    research = _load_csv(Path(company_research_csv), RESEARCH_COLUMNS, "company research")
    manual_proposal = _load_optional_csv(Path(manual_proposal_csv) if manual_proposal_csv else None, MANUAL_PROPOSAL_COLUMNS)
    report = _build_report(
        profit=profit,
        gate=gate,
        research=research,
        filing_risk_dir=Path(filing_risk_dir),
        manual_proposal=manual_proposal,
        capital_plan_dir=Path(capital_plan_dir) if capital_plan_dir else None,
    )

    output_root = Path(output_dir).resolve() / "pre_buy_decision"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "pre_buy_decision.csv"
    markdown_path = output_root / "pre_buy_decision.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "buy_ready_count": int((report["decision_status"] == "BUY_READY").sum()),
        "wait_count": int((report["decision_status"] == "WAIT").sum()),
        "reject_count": int((report["decision_status"] == "REJECT").sum()),
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return PreBuyDecisionOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame


def _load_optional_csv(path: Path | None, required_columns: set[str]) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=sorted(required_columns))
    return _load_csv(path, required_columns, path.stem.replace("_", " "))


def _build_report(
    profit: pd.DataFrame,
    gate: pd.DataFrame,
    research: pd.DataFrame,
    filing_risk_dir: Path,
    manual_proposal: pd.DataFrame,
    capital_plan_dir: Path | None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    ordered = profit.copy().sort_values(["profit_focus_status", "conviction_score"], ascending=[True, False])
    for row in ordered.to_dict(orient="records"):
        symbol = str(row["symbol"])
        gate_row = _row_for_symbol(gate, symbol)
        research_row = _row_for_symbol(research, symbol)
        filing_risk = _load_filing_risk(filing_risk_dir, symbol)
        proposal_row = _row_for_symbol(manual_proposal, symbol)
        capital_row = _load_capital_plan(capital_plan_dir, symbol)

        decision_status = _decision_status(row, gate_row, filing_risk)
        latest_price = _number(research_row.get("latest_price", 0))
        ma20_gap = _number(research_row.get("ma20_gap", row.get("ma20_gap", 0)))
        entry_low, entry_high = _entry_band(latest_price=latest_price, ma20_gap=ma20_gap)
        capital_status = str(capital_row.get("amount_status", "UNKNOWN"))

        rows.append(
            {
                "symbol": symbol,
                "company_name": row["company_name"],
                "decision_status": decision_status,
                "order_status": "NO_ORDER",
                "final_action": "NO_ORDER",
                "manual_proposal_status": str(proposal_row.get("proposal_status", "NOT_AVAILABLE")),
                "capital_status": capital_status,
                "readiness_blockers": _readiness_blockers(
                    decision_status=decision_status,
                    gate=gate_row,
                    manual_proposal=proposal_row,
                    capital_plan=capital_row,
                ),
                "buy_reasons": _buy_reasons(row, filing_risk),
                "buy_ban_reasons": _buy_ban_reasons(row, gate_row, filing_risk),
                "entry_price_low": entry_low,
                "entry_price_high": entry_high,
                "staged_buy_plan": _staged_buy_plan(),
                "stop_loss_rule": _stop_loss_rule(str(gate_row.get("loss_defense", row.get("invalidation_rule", "")))),
                "next_review_date": _next_review_date(),
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _row_for_symbol(frame: pd.DataFrame, symbol: str) -> pd.Series:
    row = frame.loc[frame["symbol"] == symbol]
    if row.empty:
        return pd.Series(dtype=object)
    return row.iloc[0]


def _load_filing_risk(filing_risk_dir: Path, symbol: str) -> pd.DataFrame:
    code = symbol.split(".")[0]
    path = filing_risk_dir / f"filing_risk_summary_{code}.csv"
    if not path.exists():
        return pd.DataFrame(columns=sorted(FILING_RISK_COLUMNS))
    return _load_csv(path, FILING_RISK_COLUMNS, "filing risk summary")


def _load_capital_plan(capital_plan_dir: Path | None, symbol: str) -> pd.Series:
    if capital_plan_dir is None:
        return pd.Series(dtype=object)
    code = symbol.split(".")[0]
    path = capital_plan_dir / f"capital_plan_review_{code}.csv"
    if not path.exists():
        return pd.Series(dtype=object)
    frame = _load_csv(path, CAPITAL_PLAN_COLUMNS, "capital plan review")
    return _row_for_symbol(frame, symbol)


def _decision_status(row: dict[str, object], gate: pd.Series, filing_risk: pd.DataFrame) -> str:
    gate_status = str(gate.get("decision_gate_status", "WAITING_MANUAL_EVIDENCE"))
    if _has_fatal_filing_risk(filing_risk) or "BLOCKED" in gate_status:
        return "REJECT"
    if gate_status == "READY_FOR_SIZING_REVIEW" and row.get("profit_focus_status") == "CORE_FOCUS":
        return "BUY_READY"
    return "WAIT"


def _readiness_blockers(
    decision_status: str,
    gate: pd.Series,
    manual_proposal: pd.Series,
    capital_plan: pd.Series,
) -> str:
    blockers: list[str] = []
    gate_status = str(gate.get("decision_gate_status", "WAITING_MANUAL_EVIDENCE"))
    proposal_status = str(manual_proposal.get("proposal_status", "NOT_AVAILABLE"))
    if decision_status == "REJECT":
        blockers.append("rejected by risk gate")
    if gate_status != "READY_FOR_SIZING_REVIEW":
        if proposal_status == "READY_FOR_USER_CONFIRMATION":
            blockers.append("actual manual review config not applied")
        else:
            blockers.append("manual gate not ready")
    if str(capital_plan.get("amount_status", "")).upper() == "CAPITAL_AMOUNT_REQUIRED":
        blockers.append("capital amount required")
    return "; ".join(dict.fromkeys(blockers)) if blockers else "no automatic blocker; user approval still required"


def _buy_reasons(row: dict[str, object], filing_risk: pd.DataFrame) -> str:
    reasons = [
        str(row.get("why_profit_candidate", "")),
        f"expected_20d_return={_pct(row.get('expected_20d_return'))}",
        f"upside_probability={_pct(row.get('upside_probability'))}",
    ]
    if not filing_risk.empty and not _has_fatal_filing_risk(filing_risk):
        reasons.append("filing risk summary has no fatal risk")
    return "; ".join(reason for reason in reasons if reason)


def _buy_ban_reasons(row: dict[str, object], gate: pd.Series, filing_risk: pd.DataFrame) -> str:
    reasons: list[str] = []
    gate_status = str(gate.get("decision_gate_status", "WAITING_MANUAL_EVIDENCE"))
    if gate_status != "READY_FOR_SIZING_REVIEW":
        reasons.append("manual gate not ready")
    if _has_fatal_filing_risk(filing_risk):
        reasons.append("fatal filing risk")
    if _number(row.get("return_20d")) >= 0.25:
        reasons.append("20D price move already stretched")
    why_not_now = str(row.get("why_not_now", "")).strip()
    if why_not_now:
        reasons.append(why_not_now)
    return "; ".join(dict.fromkeys(reasons)) if reasons else "no automatic buy ban; keep NO_ORDER until user approval"


def _has_fatal_filing_risk(filing_risk: pd.DataFrame) -> bool:
    if filing_risk.empty:
        return False
    fatal = filing_risk["fatal_risk"].astype(str).str.upper()
    opinions = filing_risk["gate_opinion"].astype(str).str.upper()
    return bool((fatal == "YES").any() or (opinions == "EXCLUDE").any())


def _entry_band(latest_price: float, ma20_gap: float) -> tuple[int, int]:
    if latest_price <= 0:
        return 0, 0
    high = int(round(latest_price / 100) * 100)
    if ma20_gap <= -0.95:
        low = high
    else:
        low = int(round((latest_price / (1 + ma20_gap)) / 1000) * 1000)
    return low, high


def _staged_buy_plan() -> str:
    return (
        "first tranche 30% of target position; add 30% only if CORE_FOCUS, SMA20, and conviction stay intact; "
        "final 40% only after next earnings or filing check confirms the thesis"
    )


def _stop_loss_rule(base_rule: str) -> str:
    return (
        "SMA20 break plus -7% from average cost: reduce 50%; -10% or conviction_score below 60: review full exit; "
        f"also stop on {base_rule}"
    )


def _next_review_date() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


def _render_markdown(report: pd.DataFrame, summary: dict[str, int]) -> str:
    lines = [
        "# Pre-Buy Decision",
        "",
        "This report is a pre-order judgment sheet. It never places orders and always keeps `order_status=NO_ORDER`.",
        "",
        f"- BUY_READY: {summary['buy_ready_count']}",
        f"- WAIT: {summary['wait_count']}",
        f"- REJECT: {summary['reject_count']}",
    ]
    for row in report.itertuples(index=False):
        lines.extend(
            [
                "",
                f"## {row.symbol} {row.company_name}",
                f"- Decision: {row.decision_status}",
                f"- Order: {row.order_status}",
                f"- Final action: {row.final_action}",
                f"- Manual proposal: {row.manual_proposal_status}",
                f"- Capital status: {row.capital_status}",
                f"- Readiness blockers: {row.readiness_blockers}",
                f"- Buy reasons: {row.buy_reasons}",
                f"- Buy ban reasons: {row.buy_ban_reasons}",
                f"- Entry band: {int(row.entry_price_low):,}-{int(row.entry_price_high):,}",
                f"- Staged plan: {row.staged_buy_plan}",
                f"- Stop loss: {row.stop_loss_rule}",
                f"- Next review: {row.next_review_date}",
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
