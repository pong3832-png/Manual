from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


REQUIRED_COLUMNS = [
    "research_id",
    "priority",
    "theme",
    "source_type",
    "source_title",
    "authors",
    "year",
    "source_url",
    "local_feature_module",
    "required_local_inputs",
    "blocked_external_inputs",
    "implementation_status",
    "validation_gate",
    "promotion_rule",
    "korea_market_note",
    "next_step",
    "external_api_requested",
    "order_status",
    "broker_order_requested",
]

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
STATUS_ORDER = {
    "READY_FOR_SPEC": 0,
    "RESEARCH_BACKLOG": 1,
    "DATA_REQUIRED": 2,
    "BLOCKED": 3,
}


@dataclass(frozen=True)
class StrategyResearchBacklogOutput:
    csv_path: Path
    markdown_path: Path
    summary_path: Path
    report: pd.DataFrame
    summary: pd.DataFrame


def load_strategy_research_backlog(path: Path | str) -> pd.DataFrame:
    try:
        backlog_path = Path(path)
        if not backlog_path.exists():
            raise FileNotFoundError(f"Strategy research backlog not found: {backlog_path}")
        frame = pd.read_csv(backlog_path).fillna("")
        missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        if missing:
            raise ValueError(f"Strategy research backlog missing columns: {missing}")
        frame = frame[REQUIRED_COLUMNS].copy()
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").fillna(0).astype(int)
        frame["external_api_requested"] = "NO"
        frame["order_status"] = "NO_ORDER"
        frame["broker_order_requested"] = "NO"
        return frame
    except Exception as exc:
        logger.exception("Failed to load strategy research backlog: %s", exc)
        raise


def rank_strategy_research_backlog(backlog: pd.DataFrame) -> pd.DataFrame:
    try:
        ranked = backlog.copy()
        ranked["_priority_rank"] = ranked["priority"].map(PRIORITY_ORDER).fillna(99).astype(int)
        ranked["_status_rank"] = (
            ranked["implementation_status"].map(STATUS_ORDER).fillna(99).astype(int)
        )
        ranked = ranked.sort_values(
            ["_priority_rank", "_status_rank", "year", "research_id"],
            ascending=[True, True, False, True],
        ).reset_index(drop=True)
        ranked.insert(0, "rank", range(1, len(ranked) + 1))
        ranked = ranked.drop(columns=["_priority_rank", "_status_rank"])
        return ranked
    except Exception as exc:
        logger.exception("Failed to rank strategy research backlog: %s", exc)
        raise


def summarize_strategy_research_backlog(report: pd.DataFrame) -> pd.DataFrame:
    try:
        if report.empty:
            return pd.DataFrame(
                [
                    {
                        "row_count": 0,
                        "p0_count": 0,
                        "p1_count": 0,
                        "p2_count": 0,
                        "ready_for_spec_count": 0,
                        "research_backlog_count": 0,
                        "data_required_count": 0,
                        "blocked_count": 0,
                        "external_api_requested": "NO",
                        "order_status": "NO_ORDER",
                        "broker_order_requested": "NO",
                    }
                ]
            )
        return pd.DataFrame(
            [
                {
                    "row_count": int(len(report)),
                    "p0_count": int((report["priority"] == "P0").sum()),
                    "p1_count": int((report["priority"] == "P1").sum()),
                    "p2_count": int((report["priority"] == "P2").sum()),
                    "ready_for_spec_count": int(
                        (report["implementation_status"] == "READY_FOR_SPEC").sum()
                    ),
                    "research_backlog_count": int(
                        (report["implementation_status"] == "RESEARCH_BACKLOG").sum()
                    ),
                    "data_required_count": int(
                        (report["implementation_status"] == "DATA_REQUIRED").sum()
                    ),
                    "blocked_count": int((report["implementation_status"] == "BLOCKED").sum()),
                    "external_api_requested": "NO",
                    "order_status": "NO_ORDER",
                    "broker_order_requested": "NO",
                }
            ]
        )
    except Exception as exc:
        logger.exception("Failed to summarize strategy research backlog: %s", exc)
        raise


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    columns = [str(column) for column in frame.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in frame.astype(str).values.tolist()]
    return "\n".join([header, separator, *body])


def _markdown_report(report: pd.DataFrame, summary: pd.DataFrame) -> str:
    summary_row = summary.iloc[0].to_dict()
    top = report.head(10)[
        [
            "rank",
            "priority",
            "research_id",
            "theme",
            "local_feature_module",
            "implementation_status",
            "next_step",
            "order_status",
        ]
    ]
    lines = [
        "# Strategy Research Backlog",
        "",
        f"- row_count: {summary_row['row_count']}",
        f"- P0: {summary_row['p0_count']}",
        f"- P1: {summary_row['p1_count']}",
        f"- P2: {summary_row['p2_count']}",
        f"- research_backlog_count: {summary_row['research_backlog_count']}",
        f"- external_api_requested: {summary_row['external_api_requested']}",
        f"- order_status: {summary_row['order_status']}",
        "",
        "## Top Implementation Candidates",
        "",
        _markdown_table(top),
        "",
        "## Full Backlog",
        "",
        _markdown_table(report),
        "",
    ]
    return "\n".join(lines)


def run_strategy_research_backlog(
    backlog_csv: Path | str,
    output_dir: Path | str,
) -> StrategyResearchBacklogOutput:
    try:
        backlog = load_strategy_research_backlog(backlog_csv)
        report = rank_strategy_research_backlog(backlog)
        summary = summarize_strategy_research_backlog(report)
        target_dir = Path(output_dir) / "strategy_research_backlog"
        target_dir.mkdir(parents=True, exist_ok=True)
        csv_path = target_dir / "strategy_research_backlog.csv"
        markdown_path = target_dir / "strategy_research_backlog.md"
        summary_path = target_dir / "strategy_research_backlog_summary.csv"
        report.to_csv(csv_path, encoding="utf-8-sig", index=False)
        summary.to_csv(summary_path, encoding="utf-8-sig", index=False)
        markdown_path.write_text(_markdown_report(report, summary), encoding="utf-8")
        return StrategyResearchBacklogOutput(
            csv_path=csv_path,
            markdown_path=markdown_path,
            summary_path=summary_path,
            report=report,
            summary=summary,
        )
    except Exception as exc:
        logger.exception("Strategy research backlog run failed: %s", exc)
        raise
