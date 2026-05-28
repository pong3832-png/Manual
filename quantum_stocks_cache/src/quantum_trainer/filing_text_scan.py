from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quantum_trainer.opendart_client import (
    RequestGet,
    extract_document_text_from_zip,
    fetch_document_file,
)


RISK_KEYWORDS: dict[str, list[str]] = {
    "litigation_review": ["소송", "분쟁", "중재", "법적절차", "계류"],
    "contingent_liability_review": ["우발채무", "채무보증", "지급보증", "담보제공", "금융보증", "약정"],
    "related_party_review": ["특수관계자", "특수관계인", "관계기업", "계열회사", "대주주", "종속기업"],
    "project_risk_review": ["프로젝트", "공사손실", "미청구공사", "개발사업", "수주", "도급", "PF"],
}
SCAN_CHECKS = list(RISK_KEYWORDS)


@dataclass(frozen=True)
class FilingTextScanOutput:
    evidence: pd.DataFrame
    summary_report: pd.DataFrame
    documents: pd.DataFrame
    evidence_csv_path: Path
    summary_csv_path: Path
    markdown_path: Path
    summary: dict[str, Any]


def run_opendart_text_risk_scan(
    symbol: str,
    disclosures_csv: Path | str,
    api_key: str,
    output_dir: Path | str,
    requester: RequestGet | None = None,
    max_documents: int = 2,
) -> FilingTextScanOutput:
    disclosures = _select_review_disclosures(disclosures_csv=disclosures_csv, symbol=symbol, limit=max_documents)
    documents = _fetch_document_texts(disclosures=disclosures, api_key=api_key, requester=requester)
    evidence = scan_filing_texts(symbol=symbol, documents=documents)
    summary_report = build_risk_summary(symbol=symbol, evidence=evidence)

    output_root = Path(output_dir) / "filing_review"
    output_root.mkdir(parents=True, exist_ok=True)
    stock_code = symbol.split(".", maxsplit=1)[0].zfill(6)
    evidence_csv_path = output_root / f"opendart_text_risk_scan_{stock_code}.csv"
    summary_csv_path = output_root / f"opendart_text_risk_summary_{stock_code}.csv"
    markdown_path = output_root / f"opendart_text_risk_scan_{stock_code}.md"

    evidence.to_csv(evidence_csv_path, index=False, encoding="utf-8-sig")
    summary_report.to_csv(summary_csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(
        _render_text_risk_scan_markdown(
            symbol=symbol,
            documents=documents,
            evidence=evidence,
            summary_report=summary_report,
        ),
        encoding="utf-8",
    )
    return FilingTextScanOutput(
        evidence=evidence,
        summary_report=summary_report,
        documents=documents,
        evidence_csv_path=evidence_csv_path,
        summary_csv_path=summary_csv_path,
        markdown_path=markdown_path,
        summary={
            "symbol": symbol,
            "document_count": int(len(documents)),
            "evidence_count": int(len(evidence)),
        },
    )


def scan_filing_texts(
    symbol: str,
    documents: pd.DataFrame,
    max_hits_per_check: int = 8,
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    hit_counts = {check: 0 for check in SCAN_CHECKS}
    for document in documents.fillna("").itertuples(index=False):
        text = str(getattr(document, "text", ""))
        segments = _split_segments(text)
        for check, keywords in RISK_KEYWORDS.items():
            if hit_counts[check] >= max_hits_per_check:
                continue
            for segment in segments:
                keyword = _first_keyword(segment, keywords)
                if not keyword:
                    continue
                rows.append(
                    {
                        "symbol": symbol,
                        "review_check": check,
                        "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                        "keyword": keyword,
                        "report_nm": str(getattr(document, "report_nm", "")),
                        "rcept_no": str(getattr(document, "rcept_no", "")),
                        "rcept_dt": str(getattr(document, "rcept_dt", "")),
                        "snippet": _truncate(segment, 320),
                    }
                )
                hit_counts[check] += 1
                if hit_counts[check] >= max_hits_per_check:
                    break
    return pd.DataFrame(
        rows,
        columns=[
            "symbol",
            "review_check",
            "scan_status",
            "keyword",
            "report_nm",
            "rcept_no",
            "rcept_dt",
            "snippet",
        ],
    )


def build_risk_summary(symbol: str, evidence: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, str | int]] = []
    for check in SCAN_CHECKS:
        check_hits = evidence.loc[evidence["review_check"] == check] if not evidence.empty else evidence
        hit_count = int(len(check_hits))
        rows.append(
            {
                "symbol": symbol,
                "review_check": check,
                "scan_status": "TEXT_HIT_REVIEW_REQUIRED" if hit_count else "NO_TEXT_HIT_STILL_REVIEW",
                "hit_count": hit_count,
                "recommended_review_value": "UNKNOWN",
                "review_note": _summary_note(check=check, hit_count=hit_count),
            }
        )
    return pd.DataFrame(rows)


def _select_review_disclosures(disclosures_csv: Path | str, symbol: str, limit: int) -> pd.DataFrame:
    disclosures = pd.read_csv(disclosures_csv, dtype=str).fillna("")
    if "symbol" not in disclosures.columns:
        raise ValueError("Disclosures CSV must include a 'symbol' column.")
    required = {"report_nm", "rcept_no", "rcept_dt"}
    missing = sorted(required.difference(disclosures.columns))
    if missing:
        raise ValueError(f"Disclosures CSV missing required columns: {missing}")

    selected = disclosures.loc[disclosures["symbol"].astype(str).str.strip() == symbol].copy()
    report_name = selected["report_nm"].astype(str)
    selected = selected.loc[
        report_name.str.contains("사업보고서", regex=False)
        | report_name.str.contains("분기보고서", regex=False)
        | report_name.str.contains("반기보고서", regex=False)
    ]
    selected = selected.sort_values("rcept_dt", ascending=False).head(limit)
    if selected.empty:
        raise ValueError(f"No annual, quarterly, or semiannual filings found for {symbol}.")
    return selected


def _fetch_document_texts(
    disclosures: pd.DataFrame,
    api_key: str,
    requester: RequestGet | None,
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for row in disclosures.itertuples(index=False):
        receipt_no = str(row.rcept_no)
        content = fetch_document_file(api_key=api_key, receipt_no=receipt_no, requester=requester)
        rows.append(
            {
                "symbol": str(row.symbol),
                "report_nm": str(row.report_nm),
                "rcept_no": receipt_no,
                "rcept_dt": str(row.rcept_dt),
                "text": extract_document_text_from_zip(content),
            }
        )
    return pd.DataFrame(rows)


def _split_segments(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", str(text)).strip()
    if not normalized:
        return []
    rough_segments = re.split(r"(?<=[.!?。])\s+|[\n\r]+", normalized)
    return [segment.strip() for segment in rough_segments if segment.strip()]


def _first_keyword(segment: str, keywords: list[str]) -> str:
    for keyword in keywords:
        if _contains_keyword(segment, keyword):
            return keyword
    return ""


def _contains_keyword(segment: str, keyword: str) -> bool:
    if keyword.isascii() and keyword.isalpha():
        pattern = rf"(?<![A-Za-z]){re.escape(keyword)}(?![A-Za-z])"
        return re.search(pattern, segment, flags=re.IGNORECASE) is not None
    return keyword.lower() in segment.lower()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _summary_note(check: str, hit_count: int) -> str:
    if hit_count:
        return f"{check} keyword hits found. Human review is required before PASS/FAIL."
    return f"No {check} keyword hit found in downloaded filings. Keep UNKNOWN until human review."


def _render_text_risk_scan_markdown(
    symbol: str,
    documents: pd.DataFrame,
    evidence: pd.DataFrame,
    summary_report: pd.DataFrame,
) -> str:
    lines = [
        "# OpenDART Text Risk Scan",
        "",
        "This report extracts keyword-based review candidates from downloaded OpenDART filings.",
        "It never changes manual review values automatically.",
        "",
        f"- Symbol: {symbol}",
        f"- Downloaded filings: {len(documents)}",
        f"- Evidence rows: {len(evidence)}",
        "",
        "## Summary",
        "",
        "| Check | Status | Hits | Recommended Value |",
        "|---|---|---:|---|",
    ]
    for row in summary_report.itertuples(index=False):
        lines.append(
            f"| {row.review_check} | {row.scan_status} | {row.hit_count} | "
            f"{row.recommended_review_value} |"
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "| Check | Keyword | Report | Date | Snippet |",
            "|---|---|---|---|---|",
        ]
    )
    if evidence.empty:
        lines.append("| - | - | - | - | No keyword evidence found. |")
    else:
        for row in evidence.head(80).itertuples(index=False):
            snippet = str(row.snippet).replace("|", "/")
            lines.append(
                f"| {row.review_check} | {row.keyword} | {row.report_nm} | "
                f"{row.rcept_dt} | {snippet} |"
            )
    lines.append("")
    lines.append("Keep all suggested manual review values as `UNKNOWN` until a human reads the evidence.")
    return "\n".join(lines)
