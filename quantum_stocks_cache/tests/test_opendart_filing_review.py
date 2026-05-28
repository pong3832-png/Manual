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
    def __init__(self, content: bytes = b"", payload: dict[str, object] | None = None) -> None:
        self.content = content
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


def _corp_code_zip() -> bytes:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <list>
    <corp_code>00126256</corp_code>
    <corp_name>삼성물산</corp_name>
    <stock_code>028260</stock_code>
    <modify_date>20260101</modify_date>
  </list>
</result>
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CORPCODE.xml", xml)
    return buffer.getvalue()


def test_fetch_opendart_filing_review_writes_disclosures_and_review_draft() -> None:
    from quantum_trainer.opendart_filing_review import fetch_opendart_filing_review

    calls: list[dict[str, object]] = []

    def fake_get(url: str, params: dict[str, object], timeout: int) -> FakeResponse:
        calls.append({"url": url, "params": params, "timeout": timeout})
        if url.endswith("/api/corpCode.xml"):
            return FakeResponse(content=_corp_code_zip())
        return FakeResponse(
            payload={
                "status": "000",
                "list": [
                    {
                        "corp_code": "00126256",
                        "corp_name": "삼성물산",
                        "stock_code": "028260",
                        "report_nm": "사업보고서 (2025.12)",
                        "rcept_no": "20260320000111",
                        "rcept_dt": "20260320",
                        "rm": "",
                    },
                    {
                        "corp_code": "00126256",
                        "corp_name": "삼성물산",
                        "stock_code": "028260",
                        "report_nm": "분기보고서 (2026.03)",
                        "rcept_no": "20260515000222",
                        "rcept_dt": "20260515",
                        "rm": "",
                    },
                ],
            }
        )

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        output = fetch_opendart_filing_review(
            symbol="028260.KS",
            api_key="secret",
            begin_date="20260101",
            end_date="20260527",
            output_dir=Path(tmp_dir) / "reports",
            requester=fake_get,
        )

        assert output.disclosures_csv_path.exists()
        assert output.review_input_csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["disclosure_count"] == 2
        review = pd.read_csv(output.review_input_csv_path)
        assert review.loc[0, "symbol"] == "028260.KS"
        assert review.loc[0, "annual_report_review"] == "PASS"
        assert review.loc[0, "quarterly_report_review"] == "PASS"
        assert review.loc[0, "litigation_review"] == "UNKNOWN"

    assert calls[1]["params"]["corp_code"] == "00126256"
    assert calls[1]["params"]["bgn_de"] == "20260101"
    assert calls[1]["params"]["end_de"] == "20260527"
