from __future__ import annotations

import logging
from datetime import date
from typing import Dict, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def _markdown_table(frame: pd.DataFrame) -> str:
    try:
        table = frame.reset_index().copy()
        columns = [str(column) for column in table.columns]
        rows = table.astype(str).values.tolist()
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        body = ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join([header, separator, *body])
    except Exception as exc:
        logger.exception("Markdown table render failed: %s", exc)
        raise


def _reason_text(codes: Tuple[str, ...]) -> str:
    return ", ".join(codes) if codes else "NONE"


def render_investment_committee_report(
    run_id: str,
    report_date: date,
    data_quality_status: str,
    risk_status: str,
    pretrade_status: str,
    trade_plan: pd.DataFrame,
    reason_codes: Dict[str, Tuple[str, ...]],
) -> str:
    try:
        return "\n".join(
            [
                f"# Investment Committee Report - {report_date.isoformat()}",
                "",
                f"- Run ID: {run_id}",
                f"- Data Quality: {data_quality_status}",
                f"- Risk Gate: {risk_status}",
                f"- Pre-Trade: {pretrade_status}",
                "",
                "## Reason Codes",
                "",
                f"- Data Quality: {_reason_text(reason_codes.get('data_quality', ())) }",
                f"- Risk: {_reason_text(reason_codes.get('risk', ())) }",
                f"- Pre-Trade: {_reason_text(reason_codes.get('pretrade', ())) }",
                "",
                "## Checked Trade Plan",
                "",
                _markdown_table(trade_plan),
                "",
            ]
        )
    except Exception as exc:
        logger.exception("Investment committee report render failed: %s", exc)
        raise
