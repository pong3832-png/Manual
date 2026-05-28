from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


class FakeResponse:
    def __init__(self, content: bytes = b"") -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


def _document_zip(text: str) -> bytes:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<DOCUMENT>
  <BODY>{text}</BODY>
</DOCUMENT>
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("REPORT.xml", xml)
    return buffer.getvalue()


def test_scan_filing_texts_extracts_keyword_snippets_without_auto_pass() -> None:
    from quantum_trainer.filing_text_scan import build_risk_summary, scan_filing_texts

    documents = pd.DataFrame(
        [
            {
                "symbol": "028260.KS",
                "report_nm": "사업보고서 (2025.12)",
                "rcept_no": "20260312000856",
                "rcept_dt": "20260312",
                "text": "계류 중인 소송은 제한적입니다.\n특수관계자 거래와 채무보증 약정이 있습니다.",
            }
        ]
    )

    evidence = scan_filing_texts(symbol="028260.KS", documents=documents)
    summary = build_risk_summary(symbol="028260.KS", evidence=evidence)

    assert set(evidence["review_check"]) >= {
        "litigation_review",
        "contingent_liability_review",
        "related_party_review",
    }
    assert "소송" in evidence.loc[evidence["review_check"] == "litigation_review", "snippet"].iloc[0]
    assert set(summary["recommended_review_value"]) == {"UNKNOWN"}
    assert "TEXT_HIT_REVIEW_REQUIRED" in set(summary["scan_status"])


def test_run_opendart_text_risk_scan_writes_reports_for_selected_filings() -> None:
    from quantum_trainer.filing_text_scan import run_opendart_text_risk_scan

    calls: list[dict[str, object]] = []

    def fake_get(url: str, params: dict[str, object], timeout: int) -> FakeResponse:
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(
            content=_document_zip(
                "우발채무 검토 문단입니다. 특수관계자 거래도 함께 검토합니다. 프로젝트 손실 위험을 점검합니다."
            )
        )

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        disclosures_csv = root / "filings.csv"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "report_nm": "분기보고서 (2026.03)",
                    "rcept_no": "20260515001895",
                    "rcept_dt": "20260515",
                },
                {
                    "symbol": "028260.KS",
                    "report_nm": "기업설명회(IR)개최(안내공시)",
                    "rcept_no": "20260522800766",
                    "rcept_dt": "20260522",
                },
            ]
        ).to_csv(disclosures_csv, index=False)

        output = run_opendart_text_risk_scan(
            symbol="028260.KS",
            disclosures_csv=disclosures_csv,
            api_key="secret",
            output_dir=root / "reports",
            requester=fake_get,
        )

        assert output.evidence_csv_path.exists()
        assert output.summary_csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["document_count"] == 1
        assert output.summary["evidence_count"] >= 3
        assert calls[0]["url"].endswith("/api/document.xml")
        assert calls[0]["params"] == {"crtfc_key": "secret", "rcept_no": "20260515001895"}


def test_scan_filing_texts_caps_hits_per_check_across_documents() -> None:
    from quantum_trainer.filing_text_scan import scan_filing_texts

    documents = pd.DataFrame(
        [
            {
                "symbol": "028260.KS",
                "report_nm": "사업보고서 (2025.12)",
                "rcept_no": "1",
                "rcept_dt": "20260312",
                "text": "소송 검토 1.\n소송 검토 2.\n소송 검토 3.",
            },
            {
                "symbol": "028260.KS",
                "report_nm": "분기보고서 (2026.03)",
                "rcept_no": "2",
                "rcept_dt": "20260515",
                "text": "소송 검토 4.\n소송 검토 5.\n소송 검토 6.",
            },
        ]
    )

    evidence = scan_filing_texts(symbol="028260.KS", documents=documents, max_hits_per_check=3)

    litigation_hits = evidence.loc[evidence["review_check"] == "litigation_review"]
    assert len(litigation_hits) == 3


def test_scan_filing_texts_does_not_match_pf_inside_longer_english_token() -> None:
    from quantum_trainer.filing_text_scan import scan_filing_texts

    documents = pd.DataFrame(
        [
            {
                "symbol": "028260.KS",
                "report_nm": "분기보고서 (2026.03)",
                "rcept_no": "1",
                "rcept_dt": "20260515",
                "text": "ADC DP 라인과 사전충전형 주사기 PFS 마더라인을 구축할 예정입니다.",
            }
        ]
    )

    evidence = scan_filing_texts(symbol="028260.KS", documents=documents)

    assert evidence.loc[evidence["review_check"] == "project_risk_review"].empty
