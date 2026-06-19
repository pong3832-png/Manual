from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "final_compliance_status",
    "primary_blocker",
    "blocker_count",
    "market_gate",
    "pre_buy_gate",
    "manual_gate",
    "filing_gate",
    "valuation_gate",
    "rebound_gate",
    "tactical_gate",
    "required_next_evidence",
    "action_summary",
    "external_api_requested",
    "order_status",
    "broker_order_requested",
]

SUMMARY_COLUMNS = [
    "row_count",
    "block_count",
    "wait_evidence_count",
    "ready_for_human_review_count",
    "external_api_requested",
    "order_status",
    "broker_order_requested",
]


@dataclass(frozen=True)
class CompliancePretradeGateOutput:
    csv_path: Path
    markdown_path: Path
    summary_csv_path: Path
    report: pd.DataFrame
    summary: dict[str, str | int]


def run_compliance_pretrade_gate(reports_dir: Path | str, output_dir: Path | str | None = None) -> CompliancePretradeGateOutput:
    reports_root = Path(reports_dir).resolve()
    output_root = Path(output_dir).resolve() if output_dir else reports_root

    inputs = _load_inputs(reports_root)
    report = _build_report(reports_root, inputs)

    target_dir = output_root / "compliance_pretrade_gate"
    target_dir.mkdir(parents=True, exist_ok=True)
    csv_path = target_dir / "compliance_pretrade_gate.csv"
    markdown_path = target_dir / "compliance_pretrade_gate.md"
    summary_csv_path = target_dir / "compliance_pretrade_gate_summary.csv"

    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    summary = _summary(report)
    pd.DataFrame([summary], columns=SUMMARY_COLUMNS).to_csv(summary_csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")

    return CompliancePretradeGateOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        summary_csv_path=summary_csv_path,
        report=report,
        summary=summary,
    )


def _load_inputs(reports_root: Path) -> dict[str, pd.DataFrame]:
    return {
        "market": _read_csv(reports_root / "market_regime" / "market_regime.csv"),
        "pre_buy": _read_csv(reports_root / "pre_buy_decision" / "pre_buy_decision.csv"),
        "decision": _read_csv(reports_root / "decision_gate" / "decision_gate.csv"),
        "manual_proposal": _read_csv(reports_root / "decision_gate" / "manual_review_proposal.csv"),
        "manual_apply": _read_csv(reports_root / "decision_gate" / "manual_review_apply_plan.csv"),
        "valuation": _read_csv(reports_root / "valuation_data_quality" / "valuation_data_quality.csv"),
        "rebound": _read_csv(reports_root / "panic_rebound_signal" / "panic_rebound_signal.csv"),
        "tactical": _read_csv(reports_root / "tactical_watchlist" / "tactical_watchlist.csv"),
    }


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def _build_report(reports_root: Path, inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    symbols = _ordered_symbols(
        inputs["pre_buy"],
        inputs["decision"],
        inputs["valuation"],
        inputs["rebound"],
        inputs["tactical"],
    )
    if not symbols:
        return pd.DataFrame([_data_required_row()], columns=OUTPUT_COLUMNS)

    rows: list[dict[str, object]] = []
    for symbol in symbols:
        context = {
            name: _row_for_symbol(frame, symbol)
            for name, frame in inputs.items()
            if name not in {"market"}
        }
        company_name = _first_text(
            context["pre_buy"].get("company_name"),
            context["decision"].get("company_name"),
            context["valuation"].get("company_name"),
            context["rebound"].get("company_name"),
            context["tactical"].get("company_name"),
        )
        sector = _first_text(context["decision"].get("sector"), context["tactical"].get("sector"), context["rebound"].get("sector"))

        gates = {
            "market_gate": _market_gate(inputs["market"], sector),
            "pre_buy_gate": _pre_buy_gate(context["pre_buy"]),
            "manual_gate": _manual_gate(context["decision"], context["manual_proposal"], context["manual_apply"]),
            "filing_gate": _filing_gate(reports_root, symbol),
            "valuation_gate": _valuation_gate(context["valuation"]),
            "rebound_gate": _rebound_gate(context["rebound"]),
            "tactical_gate": _tactical_gate(context["tactical"]),
        }
        order_gate = _order_gate(context)
        final_status, primary, blockers, evidence = _final_status(gates, order_gate)

        rows.append(
            {
                "symbol": symbol,
                "company_name": company_name,
                "final_compliance_status": final_status,
                "primary_blocker": primary,
                "blocker_count": len(blockers),
                **gates,
                "required_next_evidence": "; ".join(dict.fromkeys(evidence)),
                "action_summary": _action_summary(final_status),
                "external_api_requested": "NO",
                "order_status": "NO_ORDER",
                "broker_order_requested": "NO",
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _ordered_symbols(*frames: pd.DataFrame) -> list[str]:
    symbols: list[str] = []
    for frame in frames:
        if frame.empty or "symbol" not in frame.columns:
            continue
        for symbol in frame["symbol"].astype(str):
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    return symbols


def _row_for_symbol(frame: pd.DataFrame, symbol: str) -> pd.Series:
    if frame.empty or "symbol" not in frame.columns:
        return pd.Series(dtype=object)
    row = frame.loc[frame["symbol"].astype(str) == symbol]
    if row.empty:
        return pd.Series(dtype=object)
    return row.iloc[0]


def _market_gate(frame: pd.DataFrame, sector: str) -> str:
    if frame.empty:
        return "WAIT: DATA_REQUIRED market_regime.csv missing"
    market = _market_row(frame, "MARKET", "ALL")
    sector_row = _market_row(frame, "SECTOR", sector) if sector else pd.Series(dtype=object)
    checks = [
        ("market", str(market.get("regime_status", "")), str(market.get("risk_posture", ""))),
        ("sector", str(sector_row.get("regime_status", "")), str(sector_row.get("risk_posture", ""))),
    ]
    waits: list[str] = []
    for label, regime, posture in checks:
        result = _market_status(label, regime, posture)
        if result.startswith("BLOCK"):
            return result
        if result.startswith("WAIT"):
            waits.append(result)
    if waits:
        return waits[0]
    return "PASS: market and sector local gates clear"


def _market_row(frame: pd.DataFrame, scope: str, sector: str) -> pd.Series:
    normalized = frame.copy()
    normalized["scope"] = normalized.get("scope", "").astype(str).str.upper()
    normalized["sector"] = normalized.get("sector", "").astype(str)
    row = normalized.loc[(normalized["scope"] == scope) & (normalized["sector"] == sector)]
    if row.empty:
        return pd.Series(dtype=object)
    return row.iloc[0]


def _market_status(label: str, regime_status: str, risk_posture: str) -> str:
    regime = regime_status.upper()
    posture = risk_posture.upper()
    if regime == "RISK_OFF" or posture == "DEFENSIVE":
        return f"BLOCK: {label} gate blocked by {regime or posture}"
    if regime == "EXTENDED_UPTREND" or posture == "WAIT_PULLBACK":
        return f"BLOCK: {label} gate blocked by extended uptrend/wait pullback"
    if regime in {"RECOVERY_WATCH", "NO_DATA"} or posture in {"WAIT_CONFIRMATION", "DATA_REQUIRED"}:
        return f"WAIT: {label} gate requires confirmation"
    return "PASS"


def _pre_buy_gate(row: pd.Series) -> str:
    if row.empty:
        return "WAIT: DATA_REQUIRED pre_buy_decision.csv missing row"
    status = str(row.get("decision_status", "")).upper()
    blockers = str(row.get("readiness_blockers", "")).strip()
    if status == "REJECT":
        return "BLOCK: pre-buy decision rejected"
    if status == "WAIT" or blockers:
        return f"WAIT: pre-buy blockers {blockers or status}"
    if status == "BUY_READY":
        return "PASS: BUY_READY is review-only, not order permission"
    return "WAIT: pre-buy status unknown"


def _manual_gate(decision: pd.Series, proposal: pd.Series, apply_plan: pd.Series) -> str:
    if decision.empty:
        return "WAIT: DATA_REQUIRED decision_gate.csv missing row"
    status = str(decision.get("decision_gate_status", "")).upper()
    actual_written = str(apply_plan.get("actual_config_written", "NO")).upper()
    proposal_status = str(proposal.get("proposal_status", "NOT_AVAILABLE")).upper()
    if "BLOCKED" in status:
        return "BLOCK: manual review gate failed"
    if status != "READY_FOR_SIZING_REVIEW":
        return f"WAIT: manual gate {status or 'UNKNOWN'}"
    if actual_written != "YES":
        return f"WAIT: actual manual config not applied ({proposal_status})"
    return "PASS: manual review actual config applied"


def _filing_gate(reports_root: Path, symbol: str) -> str:
    path = reports_root / "filing_review" / f"filing_risk_summary_{symbol.split('.')[0]}.csv"
    frame = _read_csv(path)
    if frame.empty:
        return "WAIT: DATA_REQUIRED filing risk summary missing"
    fatal = frame.get("fatal_risk", pd.Series(dtype=object)).astype(str).str.upper()
    opinion = frame.get("gate_opinion", pd.Series(dtype=object)).astype(str).str.upper()
    if (fatal == "YES").any() or (opinion == "EXCLUDE").any():
        return "BLOCK: fatal filing risk"
    if (opinion == "HOLD_REVIEW").any():
        return "WAIT: filing HOLD_REVIEW"
    return "PASS: filing risk has no fatal local blocker"


def _valuation_gate(row: pd.Series) -> str:
    if row.empty:
        return "WAIT: DATA_REQUIRED valuation_data_quality.csv missing row"
    status = str(row.get("valuation_status", "")).upper()
    candidate = str(row.get("valuation_review_candidate", "")).upper()
    if status in {"VALUATION_DATA_REQUIRED", "UNKNOWN", ""} or candidate == "UNKNOWN":
        return f"WAIT: valuation evidence required ({status or 'UNKNOWN'})"
    if status == "PREMIUM_REVIEW_REQUIRED":
        return "WAIT: valuation premium review required"
    return "PASS: valuation local evidence ready"


def _rebound_gate(row: pd.Series) -> str:
    if row.empty:
        return "WAIT: DATA_REQUIRED panic_rebound_signal.csv missing row"
    status = str(row.get("rebound_status", "")).upper()
    chase = str(row.get("chase_risk", "")).upper()
    if status == "CHASE_RISK" or chase == "HIGH":
        return "BLOCK: rebound chase risk"
    if status == "WAIT_CONFIRMATION":
        return "WAIT: rebound confirmation required"
    if status == "READY_REBOUND_REVIEW":
        return "PASS: READY_REBOUND_REVIEW is watch-only"
    return "WAIT: rebound status unknown"


def _tactical_gate(row: pd.Series) -> str:
    if row.empty:
        return "WAIT: DATA_REQUIRED tactical_watchlist.csv missing row"
    status = str(row.get("tactical_status", "")).upper()
    if status == "MARKET_DEFENSIVE_WAIT":
        return "BLOCK: tactical market defensive wait"
    if status in {"PULLBACK_WATCH", "SECTOR_RECOVERY_WATCH"}:
        return f"WAIT: tactical {status}"
    if status == "READY_MANUAL_REVIEW":
        return "PASS: READY_MANUAL_REVIEW is review-only"
    return f"WAIT: tactical {status or 'UNKNOWN'}"


def _order_gate(context: dict[str, pd.Series]) -> str:
    bad: list[str] = []
    for name, row in context.items():
        if row.empty or "order_status" not in row.index:
            continue
        if str(row.get("order_status", "")).upper() != "NO_ORDER":
            bad.append(name)
    if bad:
        return "BLOCK: non-NO_ORDER status in " + ", ".join(bad)
    return "PASS: all local order_status values are NO_ORDER"


def _final_status(gates: dict[str, str], order_gate: str) -> tuple[str, str, list[str], list[str]]:
    all_gates = {**gates, "order_gate": order_gate}
    blocks = [name for name, value in all_gates.items() if value.startswith("BLOCK")]
    waits = [name for name, value in all_gates.items() if value.startswith("WAIT")]
    if blocks:
        return "BLOCK", _primary_blocker(blocks[0]), blocks, _evidence(all_gates, waits)
    if waits:
        return "WAIT_EVIDENCE", _primary_blocker(waits[0]), waits, _evidence(all_gates, waits)
    return "READY_FOR_HUMAN_REVIEW", "no automatic blocker", [], "final human review; manual broker action remains separate".split("; ")


def _primary_blocker(gate_name: str) -> str:
    if gate_name == "market_gate":
        return "market gate blocked"
    if gate_name == "order_gate":
        return "order status not NO_ORDER"
    return gate_name.replace("_", " ") + " blocked"


def _evidence(gates: dict[str, str], waits: list[str]) -> list[str]:
    evidence: list[str] = []
    for name in waits:
        label = name.replace("_gate", "").replace("_", " ")
        evidence.append(f"{label} evidence required: {gates[name]}")
    return evidence


def _data_required_row() -> dict[str, object]:
    gates = {
        "market_gate": "WAIT: DATA_REQUIRED market_regime.csv missing",
        "pre_buy_gate": "WAIT: DATA_REQUIRED pre_buy_decision.csv missing",
        "manual_gate": "WAIT: DATA_REQUIRED decision_gate.csv missing",
        "filing_gate": "WAIT: DATA_REQUIRED filing risk summary missing",
        "valuation_gate": "WAIT: DATA_REQUIRED valuation_data_quality.csv missing",
        "rebound_gate": "WAIT: DATA_REQUIRED panic_rebound_signal.csv missing",
        "tactical_gate": "WAIT: DATA_REQUIRED tactical_watchlist.csv missing",
    }
    return {
        "symbol": "DATA_REQUIRED",
        "company_name": "",
        "final_compliance_status": "WAIT_EVIDENCE",
        "primary_blocker": "DATA_REQUIRED local reports missing",
        "blocker_count": len(gates),
        **gates,
        "required_next_evidence": "local report files required; external APIs not requested",
        "action_summary": _action_summary("WAIT_EVIDENCE"),
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }


def _action_summary(status: str) -> str:
    if status == "BLOCK":
        return "Blocked by at least one local safety gate; no order path exists."
    if status == "WAIT_EVIDENCE":
        return "Waiting for local evidence; do not fetch external data or place orders without approval."
    return "Ready for human review only; not order permission and no broker action is requested."


def _summary(report: pd.DataFrame) -> dict[str, str | int]:
    return {
        "row_count": int(len(report)),
        "block_count": int((report["final_compliance_status"] == "BLOCK").sum()),
        "wait_evidence_count": int((report["final_compliance_status"] == "WAIT_EVIDENCE").sum()),
        "ready_for_human_review_count": int((report["final_compliance_status"] == "READY_FOR_HUMAN_REVIEW").sum()),
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }


def _render_markdown(report: pd.DataFrame, summary: dict[str, str | int]) -> str:
    lines = [
        "# Compliance Pretrade Gate",
        "",
        "Local-only final safety gate. READY_FOR_HUMAN_REVIEW is not buy permission.",
        "",
        f"- BLOCK: {summary['block_count']}",
        f"- WAIT_EVIDENCE: {summary['wait_evidence_count']}",
        f"- READY_FOR_HUMAN_REVIEW: {summary['ready_for_human_review_count']}",
        f"- external_api_requested: {summary['external_api_requested']}",
        f"- order_status: {summary['order_status']}",
        f"- broker_order_requested: {summary['broker_order_requested']}",
        "",
        "| Symbol | Company | Status | Primary blocker | Blockers | Order |",
        "|---|---|---|---|---:|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.company_name} | {row.final_compliance_status} | "
            f"{row.primary_blocker} | {row.blocker_count} | {row.order_status} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _first_text(*values: object) -> str:
    for value in values:
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.lower() not in {"none", "nan"}:
            return text
    return ""
