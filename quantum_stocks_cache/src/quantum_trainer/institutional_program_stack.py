from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


REQUIRED_COLUMNS = [
    "program_id",
    "priority",
    "program_category",
    "public_reference",
    "source_url",
    "institutional_capability",
    "our_current_coverage",
    "local_apply_module",
    "required_local_inputs",
    "blocked_capabilities",
    "implementation_status",
    "validation_gate",
    "next_step",
    "external_api_requested",
    "order_status",
    "broker_order_requested",
]

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
STATUS_ORDER = {"READY_FOR_SPEC": 0, "RESEARCH_BACKLOG": 1, "DATA_REQUIRED": 2, "BLOCKED": 3}


@dataclass(frozen=True)
class InstitutionalProgramStackOutput:
    csv_path: Path
    markdown_path: Path
    summary_path: Path
    report: pd.DataFrame
    summary: pd.DataFrame


def load_institutional_program_stack(path: Path | str) -> pd.DataFrame:
    try:
        source_path = Path(path)
        if not source_path.exists():
            raise FileNotFoundError(f"Institutional program stack CSV not found: {source_path}")
        frame = pd.read_csv(source_path).fillna("")
        missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        if missing:
            raise ValueError(f"Institutional program stack missing columns: {missing}")
        frame = frame[REQUIRED_COLUMNS].copy()
        frame["external_api_requested"] = "NO"
        frame["order_status"] = "NO_ORDER"
        frame["broker_order_requested"] = "NO"
        return frame
    except Exception as exc:
        logger.exception("Failed to load institutional program stack: %s", exc)
        raise


def rank_institutional_program_stack(stack: pd.DataFrame) -> pd.DataFrame:
    try:
        ranked = stack.copy()
        ranked["_priority_rank"] = ranked["priority"].map(PRIORITY_ORDER).fillna(99).astype(int)
        ranked["_status_rank"] = ranked["implementation_status"].map(STATUS_ORDER).fillna(99).astype(int)
        ranked = ranked.sort_values(
            ["_priority_rank", "_status_rank", "program_id"],
            ascending=[True, True, True],
        ).reset_index(drop=True)
        ranked.insert(0, "rank", range(1, len(ranked) + 1))
        return ranked.drop(columns=["_priority_rank", "_status_rank"])
    except Exception as exc:
        logger.exception("Failed to rank institutional program stack: %s", exc)
        raise


def summarize_institutional_program_stack(report: pd.DataFrame) -> pd.DataFrame:
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
                    "ready_for_spec_count": int((report["implementation_status"] == "READY_FOR_SPEC").sum()),
                    "research_backlog_count": int((report["implementation_status"] == "RESEARCH_BACKLOG").sum()),
                    "external_api_requested": "NO",
                    "order_status": "NO_ORDER",
                    "broker_order_requested": "NO",
                }
            ]
        )
    except Exception as exc:
        logger.exception("Failed to summarize institutional program stack: %s", exc)
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
            "program_id",
            "program_category",
            "public_reference",
            "local_apply_module",
            "implementation_status",
            "next_step",
            "order_status",
        ]
    ]
    lines = [
        "# Institutional Program Stack",
        "",
        "Public hedge-fund/quant-platform capabilities mapped to local review-only modules.",
        "",
        f"- row_count: {summary_row['row_count']}",
        f"- P0: {summary_row['p0_count']}",
        f"- P1: {summary_row['p1_count']}",
        f"- P2: {summary_row['p2_count']}",
        f"- ready_for_spec_count: {summary_row['ready_for_spec_count']}",
        f"- research_backlog_count: {summary_row['research_backlog_count']}",
        f"- external_api_requested: {summary_row['external_api_requested']}",
        f"- order_status: {summary_row['order_status']}",
        f"- broker_order_requested: {summary_row['broker_order_requested']}",
        "",
        "## Top Local Application Candidates",
        "",
        _markdown_table(top),
        "",
        "## Full Capability Map",
        "",
        _markdown_table(report),
        "",
    ]
    return "\n".join(lines)


def run_institutional_program_stack(
    stack_csv: Path | str,
    output_dir: Path | str,
) -> InstitutionalProgramStackOutput:
    try:
        stack = load_institutional_program_stack(stack_csv)
        report = rank_institutional_program_stack(stack)
        summary = summarize_institutional_program_stack(report)
        target_dir = Path(output_dir) / "institutional_program_stack"
        target_dir.mkdir(parents=True, exist_ok=True)
        csv_path = target_dir / "institutional_program_stack.csv"
        markdown_path = target_dir / "institutional_program_stack.md"
        summary_path = target_dir / "institutional_program_stack_summary.csv"
        report.to_csv(csv_path, encoding="utf-8-sig", index=False)
        summary.to_csv(summary_path, encoding="utf-8-sig", index=False)
        markdown_path.write_text(_markdown_report(report, summary), encoding="utf-8")
        return InstitutionalProgramStackOutput(
            csv_path=csv_path,
            markdown_path=markdown_path,
            summary_path=summary_path,
            report=report,
            summary=summary,
        )
    except Exception as exc:
        logger.exception("Institutional program stack run failed: %s", exc)
        raise
