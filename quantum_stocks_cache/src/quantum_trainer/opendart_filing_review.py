from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quantum_trainer.filing_review import build_filing_review_input_from_disclosures
from quantum_trainer.opendart_client import (
    RequestGet,
    extract_disclosure_rows,
    fetch_corp_code_map,
    fetch_disclosure_list,
)


@dataclass(frozen=True)
class OpendartFilingReviewOutput:
    disclosures: pd.DataFrame
    review_input: pd.DataFrame
    disclosures_csv_path: Path
    review_input_csv_path: Path
    markdown_path: Path
    summary: dict[str, Any]


def fetch_opendart_filing_review(
    symbol: str,
    api_key: str,
    begin_date: str,
    end_date: str,
    output_dir: Path | str,
    requester: RequestGet | None = None,
) -> OpendartFilingReviewOutput:
    stock_code = _stock_code_from_symbol(symbol)
    corp_code_map = fetch_corp_code_map(api_key=api_key, requester=requester)
    corp_code = corp_code_map.get(stock_code)
    if not corp_code:
        raise ValueError(f"No OpenDART corp_code found for {symbol}.")

    payload = fetch_disclosure_list(
        api_key=api_key,
        corp_code=corp_code,
        begin_date=begin_date,
        end_date=end_date,
        requester=requester,
    )
    disclosures = extract_disclosure_rows(symbol=symbol, payload=payload)
    review_input = build_filing_review_input_from_disclosures(symbol=symbol, disclosures=disclosures)

    output_root = Path(output_dir) / "filing_review"
    output_root.mkdir(parents=True, exist_ok=True)
    file_stem = stock_code
    disclosures_csv_path = output_root / f"opendart_filings_{file_stem}.csv"
    review_input_csv_path = output_root / f"opendart_filing_review_{file_stem}.csv"
    markdown_path = output_root / f"opendart_filing_review_{file_stem}.md"

    disclosures.to_csv(disclosures_csv_path, index=False, encoding="utf-8-sig")
    review_input.to_csv(review_input_csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(
        _render_opendart_filing_review_markdown(
            symbol=symbol,
            corp_code=corp_code,
            begin_date=begin_date,
            end_date=end_date,
            disclosures=disclosures,
            review_input=review_input,
        ),
        encoding="utf-8",
    )
    return OpendartFilingReviewOutput(
        disclosures=disclosures,
        review_input=review_input,
        disclosures_csv_path=disclosures_csv_path,
        review_input_csv_path=review_input_csv_path,
        markdown_path=markdown_path,
        summary={
            "symbol": symbol,
            "corp_code": corp_code,
            "disclosure_count": int(len(disclosures)),
            "review_input_count": int(len(review_input)),
        },
    )


def _render_opendart_filing_review_markdown(
    symbol: str,
    corp_code: str,
    begin_date: str,
    end_date: str,
    disclosures: pd.DataFrame,
    review_input: pd.DataFrame,
) -> str:
    lines = [
        "# OpenDART Filing Review Draft",
        "",
        "This draft pre-fills filing review inputs from OpenDART disclosure list metadata.",
        "It is not an order ticket and does not update `configs/manual_review.actual.csv`.",
        "",
        f"- Symbol: {symbol}",
        f"- OpenDART corp_code: {corp_code}",
        f"- Period: {begin_date} to {end_date}",
        f"- Disclosure count: {len(disclosures)}",
        "",
        "## Prefill",
        "",
        "| Symbol | Annual | Quarterly/Semiannual | Litigation | Contingent Liability | Related Party | Project Risk |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in review_input.itertuples(index=False):
        lines.append(
            f"| {row.symbol} | {row.annual_report_review} | {row.quarterly_report_review} | "
            f"{row.litigation_review} | {row.contingent_liability_review} | "
            f"{row.related_party_review} | {row.project_risk_review} |"
        )
    lines.extend(
        [
            "",
            "## Disclosures",
            "",
            "| Date | Report | Receipt No |",
            "|---|---|---|",
        ]
    )
    if disclosures.empty:
        lines.append("| - | No disclosures found | - |")
    else:
        for row in disclosures.sort_values("rcept_dt", ascending=False).itertuples(index=False):
            lines.append(f"| {row.rcept_dt or '-'} | {row.report_nm or '-'} | {row.rcept_no or '-'} |")
    lines.extend(
        [
            "",
            "Human review is still required before copying any value into the manual decision gate.",
        ]
    )
    return "\n".join(lines)


def _stock_code_from_symbol(symbol: str) -> str:
    return symbol.split(".", maxsplit=1)[0].zfill(6)
