from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


PRE_BUY_COLUMNS = {
    "symbol",
    "company_name",
    "decision_status",
    "order_status",
    "final_action",
    "capital_status",
    "readiness_blockers",
}

GATE_COLUMNS = {
    "symbol",
    "decision_gate_status",
    "order_status",
}

MANUAL_APPLY_COLUMNS = {
    "symbol",
    "actual_config_written",
}

UNIVERSE_COVERAGE_COLUMNS = {
    "universe_status",
    "price_coverage_status",
    "order_status",
    "external_api_requested",
}

ORDER_CANDIDATE_COLUMNS = {
    "symbol",
    "order_status",
    "capital_status",
}

OUTPUT_COLUMNS = [
    "completion_status",
    "usage_status",
    "done_message",
    "top_symbol",
    "company_name",
    "decision_status",
    "decision_gate_status",
    "manual_actual_written",
    "capital_status",
    "universe_status",
    "price_coverage_status",
    "order_candidate_status",
    "order_status",
    "external_api_requested",
    "broker_order_requested",
    "blockers",
    "next_step",
    "dashboard_path",
]


@dataclass(frozen=True)
class OperatingStatusOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, str | int]


def run_operating_status(
    reports_dir: Path | str,
    output_dir: Path | str | None = None,
    dashboard_path: Path | str | None = None,
) -> OperatingStatusOutput:
    reports_root = Path(reports_dir).resolve()
    output_root = Path(output_dir).resolve() if output_dir else reports_root / "operating_status"
    output_root.mkdir(parents=True, exist_ok=True)

    pre_buy = _load_csv(reports_root / "pre_buy_decision" / "pre_buy_decision.csv", PRE_BUY_COLUMNS, "pre-buy decision")
    gate = _load_csv(reports_root / "decision_gate" / "decision_gate.csv", GATE_COLUMNS, "decision gate")
    manual_apply = _load_csv(
        reports_root / "decision_gate" / "manual_review_apply_plan.csv",
        MANUAL_APPLY_COLUMNS,
        "manual review apply plan",
    )
    universe = _load_csv(
        reports_root / "universe_coverage" / "universe_coverage.csv",
        UNIVERSE_COVERAGE_COLUMNS,
        "universe coverage",
    )
    order_candidates = _load_csv(
        reports_root / "orders" / "order_candidates.csv",
        ORDER_CANDIDATE_COLUMNS,
        "order candidates",
    )

    report = _build_report(
        pre_buy=pre_buy,
        gate=gate,
        manual_apply=manual_apply,
        universe=universe,
        order_candidates=order_candidates,
        dashboard_path=str(Path(dashboard_path) if dashboard_path else reports_root / "dashboard" / "index.html"),
    )

    csv_path = output_root / "operating_status.csv"
    markdown_path = output_root / "operating_status.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")

    row = report.iloc[0] if not report.empty else pd.Series(dtype=object)
    summary = {
        "completion_status": str(row.get("completion_status", "NOT_DONE")),
        "usage_status": str(row.get("usage_status", "BLOCKED_MISSING_REPORTS")),
        "top_symbol": str(row.get("top_symbol", "")),
        "order_status": str(row.get("order_status", "NO_ORDER")),
        "broker_order_requested": str(row.get("broker_order_requested", "NO")),
    }
    return OperatingStatusOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_csv(path: Path, required_columns: set[str], name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name.title()} CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{name.title()} CSV missing required columns: {missing}")
    return frame


def _build_report(
    pre_buy: pd.DataFrame,
    gate: pd.DataFrame,
    manual_apply: pd.DataFrame,
    universe: pd.DataFrame,
    order_candidates: pd.DataFrame,
    dashboard_path: str,
) -> pd.DataFrame:
    top = pre_buy.iloc[0]
    symbol = str(top["symbol"])
    gate_row = _row_for_symbol(gate, symbol)
    apply_row = _row_for_symbol(manual_apply, symbol)
    universe_row = universe.iloc[0] if not universe.empty else pd.Series(dtype=object)
    order_row = _row_for_symbol(order_candidates, symbol)

    decision_status = str(top.get("decision_status", "WAIT"))
    gate_status = str(gate_row.get("decision_gate_status", "WAITING_MANUAL_EVIDENCE"))
    manual_actual_written = str(apply_row.get("actual_config_written", "NO")).upper()
    capital_status = str(top.get("capital_status", order_row.get("capital_status", "UNKNOWN")))
    universe_status = str(universe_row.get("universe_status", "UNKNOWN"))
    price_coverage_status = str(universe_row.get("price_coverage_status", "UNKNOWN"))
    order_candidate_status = str(order_row.get("order_status", "NO_ORDER"))
    external_api_requested = str(universe_row.get("external_api_requested", "NO"))

    blockers = _blockers(
        decision_status=decision_status,
        gate_status=gate_status,
        manual_actual_written=manual_actual_written,
        capital_status=capital_status,
        universe_status=universe_status,
        price_coverage_status=price_coverage_status,
        readiness_blockers=str(top.get("readiness_blockers", "")),
    )
    completion_status = "DONE" if not blockers else "NOT_DONE"
    done_message = (
        "DONE: 끝. Review dashboard is ready; broker order still requires manual action."
        if completion_status == "DONE"
        else "NOT_DONE: 아직 끝 아님. Resolve blockers before real buy review."
    )

    row = {
        "completion_status": completion_status,
        "usage_status": "READY_FOR_REVIEW_USE",
        "done_message": done_message,
        "top_symbol": symbol,
        "company_name": str(top.get("company_name", "")),
        "decision_status": decision_status,
        "decision_gate_status": gate_status,
        "manual_actual_written": manual_actual_written,
        "capital_status": capital_status,
        "universe_status": universe_status,
        "price_coverage_status": price_coverage_status,
        "order_candidate_status": order_candidate_status,
        "order_status": "NO_ORDER",
        "external_api_requested": external_api_requested,
        "broker_order_requested": "NO",
        "blockers": "; ".join(blockers),
        "next_step": _next_step(blockers),
        "dashboard_path": dashboard_path,
    }
    return pd.DataFrame([row], columns=OUTPUT_COLUMNS)


def _row_for_symbol(frame: pd.DataFrame, symbol: str) -> pd.Series:
    if frame.empty or "symbol" not in frame.columns:
        return pd.Series(dtype=object)
    row = frame.loc[frame["symbol"] == symbol]
    if row.empty:
        return pd.Series(dtype=object)
    return row.iloc[0]


def _blockers(
    decision_status: str,
    gate_status: str,
    manual_actual_written: str,
    capital_status: str,
    universe_status: str,
    price_coverage_status: str,
    readiness_blockers: str,
) -> list[str]:
    blockers: list[str] = []
    if decision_status != "BUY_READY":
        blockers.append(f"pre-buy decision is {decision_status}")
    if gate_status != "READY_FOR_SIZING_REVIEW":
        blockers.append(_gate_blocker(gate_status))
    if manual_actual_written != "YES":
        blockers.append("actual manual review config not applied")
    if _capital_required(capital_status):
        blockers.append("capital amount required")
    if universe_status not in {"PASS_CANDIDATE", "UNIVERSE_READY"}:
        blockers.append("universe coverage not ready")
    if price_coverage_status != "PRICE_COVERAGE_READY":
        blockers.append("price coverage not ready")

    for blocker in [part.strip() for part in readiness_blockers.split(";")]:
        if blocker:
            if blocker == "no automatic blocker" or blocker == "user approval still required":
                continue
            if blocker == "no automatic blocker; user approval still required":
                continue
            blockers.append(blocker)
    return list(dict.fromkeys(blockers))


def _gate_blocker(gate_status: str) -> str:
    if gate_status == "WAITING_MANUAL_EVIDENCE":
        return "decision gate waiting manual evidence"
    if gate_status == "BLOCKED_BY_MANUAL_REVIEW":
        return "decision gate blocked by manual review"
    return f"decision gate not ready: {gate_status}"


def _capital_required(capital_status: str) -> bool:
    return capital_status.upper() in {"", "UNKNOWN", "CAPITAL_AMOUNT_REQUIRED", "CAPITAL_REQUIRED"}


def _next_step(blockers: list[str]) -> str:
    if not blockers:
        return "Use dashboard for final human review. Broker order remains manual only."

    steps: list[str] = []
    joined = "; ".join(blockers)
    if "manual review" in joined or "decision gate" in joined:
        steps.append("manual review confirmation")
    if "capital" in joined:
        steps.append("capital amount input")
    if "universe" in joined:
        steps.append("expand universe coverage")
    if "price coverage" in joined:
        steps.append("refresh cached prices after explicit approval")
    if not steps:
        steps.append("review blockers")
    return "Resolve: " + "; ".join(dict.fromkeys(steps)) + "."


def _render_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Operating Status",
        "",
        "This is the final local status report for the review workflow. It never places orders.",
        "",
    ]
    for row in report.itertuples(index=False):
        lines.extend(
            [
                f"## {row.completion_status}",
                f"- Message: {row.done_message}",
                f"- Usage: {row.usage_status}",
                f"- Top symbol: {row.top_symbol} {row.company_name}",
                f"- Pre-buy decision: {row.decision_status}",
                f"- Decision gate: {row.decision_gate_status}",
                f"- Manual actual written: {row.manual_actual_written}",
                f"- Capital: {row.capital_status}",
                f"- Universe: {row.universe_status}",
                f"- Price coverage: {row.price_coverage_status}",
                f"- Order candidate: {row.order_candidate_status}",
                f"- Order status: {row.order_status}",
                f"- Broker order requested: {row.broker_order_requested}",
                f"- Blockers: {row.blockers}",
                f"- Next step: {row.next_step}",
                f"- Dashboard: {row.dashboard_path}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
