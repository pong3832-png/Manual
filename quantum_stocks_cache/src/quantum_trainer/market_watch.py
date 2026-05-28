from __future__ import annotations

from datetime import date
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
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
}


@dataclass(frozen=True)
class MarketWatchOutput:
    csv_path: Path
    markdown_path: Path
    history_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_market_watch(
    company_research_csv: Path | str,
    output_dir: Path | str,
    previous_watch_csv: Path | str | None = None,
    top_n: int = 15,
    as_of: str | None = None,
) -> MarketWatchOutput:
    if top_n <= 0:
        raise ValueError("top_n must be greater than 0.")

    output_root = Path(output_dir).resolve() / "market_watch"
    default_previous = output_root / "market_watch.csv"
    history_path = output_root / "market_watch_history.csv"
    previous_path = Path(previous_watch_csv).resolve() if previous_watch_csv else default_previous

    current = _load_company_research(company_research_csv)
    previous = _load_previous_watch(previous_path)
    history = _load_watch_history(history_path)
    report = _build_watch_report(current=current, previous=previous)
    report = _add_persistence(report=report, history=history)
    report = report.sort_values(
        ["persistence_score", "watch_priority", "research_score"], ascending=[False, False, False]
    ).head(top_n)
    report = report.reset_index(drop=True)

    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "market_watch.csv"
    markdown_path = output_root / "market_watch.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    _append_history(report=report, history_path=history_path, as_of=as_of or date.today().isoformat())

    summary: dict[str, int | str] = {
        "row_count": int(len(report)),
        "focus_count": int((report["watch_status"] == "TODAY_FOCUS").sum()),
        "upgrade_count": int(report["watch_event"].str.startswith("UPGRADED").sum()),
        "downgrade_count": int(report["watch_event"].str.startswith("DOWNGRADED").sum()),
        "persistent_focus_count": int((report["persistence_label"] == "PERSISTENT_FOCUS").sum()),
        "previous_source": str(previous_path) if previous is not None else "none",
        "history_path": str(history_path),
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")

    return MarketWatchOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        history_path=history_path,
        report=report,
        summary=summary,
    )


def _append_history(report: pd.DataFrame, history_path: Path, as_of: str) -> None:
    history = report.copy()
    history.insert(0, "as_of", as_of)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        existing = pd.read_csv(history_path).fillna("")
        history = pd.concat([existing, history], ignore_index=True, sort=False)
    history.to_csv(history_path, index=False, encoding="utf-8-sig")


def _load_company_research(path: Path | str) -> pd.DataFrame:
    csv_path = Path(path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"Company research CSV not found: {csv_path}")
    report = pd.read_csv(csv_path).fillna("")
    missing = sorted(REQUIRED_COLUMNS.difference(report.columns))
    if missing:
        raise ValueError(f"Company research CSV missing required columns: {missing}")
    return report


def _load_previous_watch(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    previous = pd.read_csv(path).fillna("")
    if "symbol" not in previous.columns:
        return None
    return previous


def _load_watch_history(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    history = pd.read_csv(path).fillna("")
    if "symbol" not in history.columns or "watch_status" not in history.columns:
        return None
    return history


def _build_watch_report(current: pd.DataFrame, previous: pd.DataFrame | None) -> pd.DataFrame:
    previous_by_symbol = (
        previous.drop_duplicates(subset=["symbol"]).set_index("symbol") if previous is not None else None
    )
    rows: list[dict[str, object]] = []
    for row in current.itertuples(index=False):
        symbol = str(row.symbol)
        previous_row = previous_by_symbol.loc[symbol] if previous_by_symbol is not None and symbol in previous_by_symbol.index else None
        previous_score = _previous_value(previous_row, "research_score", 0.0)
        previous_view = str(_previous_value(previous_row, "research_view", "NEW"))
        previous_decision = str(_previous_value(previous_row, "decision", "NEW"))
        current_score = _number(row.research_score)
        score_delta = round(current_score - _number(previous_score), 6)
        watch_status = _watch_status(row)
        watch_event = _watch_event(
            current_view=str(row.research_view),
            current_decision=str(row.decision),
            current_score=current_score,
            previous_view=previous_view,
            previous_decision=previous_decision,
            score_delta=score_delta,
        )
        rows.append(
            {
                "symbol": row.symbol,
                "company_name": row.company_name,
                "sector": row.sector,
                "research_score": current_score,
                "previous_research_score": _number(previous_score),
                "score_delta": score_delta,
                "research_view": row.research_view,
                "previous_research_view": previous_view,
                "decision": row.decision,
                "previous_decision": previous_decision,
                "fundamental_view": row.fundamental_view,
                "watch_status": watch_status,
                "watch_event": watch_event,
                "watch_priority": _watch_priority(watch_status, watch_event, current_score),
                "focus_reason": _focus_reason(row, watch_event),
                "expected_20d_return": _number(row.expected_20d_return),
                "upside_probability": _number(row.upside_probability),
                "return_20d": _number(row.return_20d),
                "ma20_gap": _number(row.ma20_gap),
                "drawdown_20d": _number(row.drawdown_20d),
                "why_summary": row.why_summary,
            }
        )
    return pd.DataFrame(rows)


def _add_persistence(report: pd.DataFrame, history: pd.DataFrame | None) -> pd.DataFrame:
    enriched = report.copy()
    counts: list[int] = []
    labels: list[str] = []
    scores: list[float] = []
    for row in enriched.itertuples(index=False):
        count = _focus_persistence_count(symbol=str(row.symbol), current_status=str(row.watch_status), history=history)
        label = _persistence_label(count=count, current_status=str(row.watch_status))
        score = _persistence_score(count=count, current_score=float(row.research_score), current_status=str(row.watch_status))
        counts.append(count)
        labels.append(label)
        scores.append(score)
    enriched["focus_persistence_count"] = counts
    enriched["persistence_label"] = labels
    enriched["persistence_score"] = scores
    return enriched


def _focus_persistence_count(symbol: str, current_status: str, history: pd.DataFrame | None) -> int:
    if current_status != "TODAY_FOCUS":
        return 0
    count = 1
    if history is None or history.empty:
        return count
    symbol_history = history.loc[history["symbol"].astype(str) == symbol].copy()
    if symbol_history.empty:
        return count
    if "as_of" in symbol_history.columns:
        symbol_history["_as_of_sort"] = pd.to_datetime(symbol_history["as_of"], errors="coerce")
        symbol_history = symbol_history.sort_values(["_as_of_sort"])
    for history_row in reversed(list(symbol_history.itertuples(index=False))):
        status = str(getattr(history_row, "watch_status", ""))
        if status != "TODAY_FOCUS":
            break
        count += 1
    return count


def _persistence_label(count: int, current_status: str) -> str:
    if current_status != "TODAY_FOCUS":
        return "NOT_FOCUS"
    if count >= 3:
        return "PERSISTENT_FOCUS"
    if count == 2:
        return "BUILDING_FOCUS"
    return "NEW_FOCUS"


def _persistence_score(count: int, current_score: float, current_status: str) -> float:
    if current_status != "TODAY_FOCUS":
        return 0.0
    return min(100.0, 40.0 + count * 15.0 + max(0.0, current_score - 70.0) * 0.5)


def _watch_status(row: object) -> str:
    research_view = str(row.research_view)
    decision = str(row.decision)
    fundamental_view = str(row.fundamental_view)
    if decision == "AVOID" or research_view == "AVOID_FOR_NOW":
        return "AVOID_MONITOR"
    if research_view == "RESEARCH_CANDIDATE" and decision == "BUY_READY":
        return "TODAY_FOCUS"
    if decision == "BUY_READY" or _number(row.research_score) >= 75:
        if fundamental_view == "FUNDAMENTAL_WEAK":
            return "WATCH_FOR_CONFIRMATION"
        return "WATCH_RISING"
    return "BACKGROUND_MONITOR"


def _watch_event(
    current_view: str,
    current_decision: str,
    current_score: float,
    previous_view: str,
    previous_decision: str,
    score_delta: float,
) -> str:
    if previous_view == "NEW":
        if current_view == "RESEARCH_CANDIDATE" and current_decision == "BUY_READY":
            return "NEW_RESEARCH_CANDIDATE"
        return "NEW_SYMBOL"
    if current_decision == "AVOID" or current_view == "AVOID_FOR_NOW":
        if previous_decision != "AVOID" and previous_view != "AVOID_FOR_NOW":
            return "DOWNGRADED_TO_AVOID"
        return "STABLE_AVOID"
    if (
        current_view == "RESEARCH_CANDIDATE"
        and current_decision == "BUY_READY"
        and (previous_view != "RESEARCH_CANDIDATE" or previous_decision != "BUY_READY")
    ):
        return "UPGRADED_TO_RESEARCH_CANDIDATE"
    if score_delta >= 10:
        return "SCORE_UP_STRONG"
    if score_delta <= -10:
        return "SCORE_DOWN_STRONG"
    if current_view == "RESEARCH_CANDIDATE" and current_decision == "BUY_READY":
        return "STABLE_PRIORITY"
    return "UNCHANGED"


def _watch_priority(watch_status: str, watch_event: str, research_score: float) -> float:
    priority = research_score
    if watch_status == "TODAY_FOCUS":
        priority += 100
    elif watch_status == "WATCH_FOR_CONFIRMATION":
        priority += 60
    elif watch_status == "WATCH_RISING":
        priority += 50
    elif watch_status == "AVOID_MONITOR":
        priority += 20
    if watch_event.startswith("UPGRADED"):
        priority += 50
    elif watch_event.startswith("DOWNGRADED"):
        priority += 45
    elif watch_event == "NEW_RESEARCH_CANDIDATE":
        priority += 40
    elif watch_event in {"SCORE_UP_STRONG", "SCORE_DOWN_STRONG"}:
        priority += 25
    return priority


def _focus_reason(row: object, watch_event: str) -> str:
    reasons = [watch_event]
    if str(row.decision) == "BUY_READY":
        reasons.append("BUY_READY")
    if _number(row.expected_20d_return) > 0:
        reasons.append(f"expected_20d_return={_pct(row.expected_20d_return)}")
    if _number(row.upside_probability) >= 0.6:
        reasons.append(f"upside_probability={_pct(row.upside_probability)}")
    if _number(row.ma20_gap) > 0:
        reasons.append(f"above_sma20={_pct(row.ma20_gap)}")
    if str(row.fundamental_view) == "FUNDAMENTAL_WEAK":
        reasons.append("fundamental confirmation needed")
    return "; ".join(reasons)


def _previous_value(previous_row: pd.Series | None, column: str, default: object) -> object:
    if previous_row is None or column not in previous_row.index:
        return default
    return previous_row[column]


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Market Watch",
        "",
        "투자금 없이 동향을 감시하는 리포트입니다. 실제 주문 실행 문서가 아닙니다.",
        "",
        "## Summary",
        f"- Focus count: {summary['focus_count']}",
        f"- Upgrades: {summary['upgrade_count']}",
        f"- Downgrades: {summary['downgrade_count']}",
        f"- Persistent focus: {summary['persistent_focus_count']}",
        f"- Previous source: {summary['previous_source']}",
        f"- History: {summary['history_path']}",
        "",
        "| Rank | Symbol | Company | Status | Event | Persistence | Score | Delta |",
        "|---:|---|---|---|---|---|---:|---:|",
    ]
    for rank, row in enumerate(report.itertuples(index=False), start=1):
        lines.append(
            f"| {rank} | {row.symbol} | {row.company_name} | {row.watch_status} | "
            f"{row.watch_event} | {row.persistence_label} ({row.focus_persistence_count}) | "
            f"{float(row.research_score):.2f} | {float(row.score_delta):.2f} |"
        )
    lines.append("")
    lines.append("## Today Focus")
    focus = report.loc[report["watch_status"] == "TODAY_FOCUS"]
    if focus.empty:
        lines.append("")
        lines.append("- No TODAY_FOCUS names.")
    else:
        for row in focus.itertuples(index=False):
            lines.extend(
                [
                    "",
                    f"### {row.symbol} {row.company_name}",
                    f"- Event: {row.watch_event}",
                    f"- Persistence: {row.persistence_label} ({row.focus_persistence_count})",
                    f"- Reason: {row.focus_reason}",
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
