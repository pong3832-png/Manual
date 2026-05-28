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

from quantum_trainer.opendart_client import (
    extract_disclosure_rows,
    extract_document_text_from_zip,
    extract_fundamentals_from_statement,
    extract_shares_outstanding,
    fetch_corp_code_map,
    fetch_disclosure_list,
    fetch_document_file,
    load_env_file,
)


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
    <corp_code>00126380</corp_code>
    <corp_name>삼성전자</corp_name>
    <stock_code>005930</stock_code>
    <modify_date>20260101</modify_date>
  </list>
  <list>
    <corp_code>00164742</corp_code>
    <corp_name>현대자동차</corp_name>
    <stock_code>005380</stock_code>
    <modify_date>20260101</modify_date>
  </list>
</result>
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CORPCODE.xml", xml)
    return buffer.getvalue()


def _document_zip() -> bytes:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<DOCUMENT>
  <TITLE>사업보고서</TITLE>
  <BODY>우발채무와 특수관계자 거래를 검토합니다.</BODY>
</DOCUMENT>
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("REPORT.xml", xml)
    return buffer.getvalue()


def test_fetch_corp_code_map_reads_zip_xml_without_exposing_key() -> None:
    calls: list[dict[str, object]] = []

    def fake_get(url: str, params: dict[str, object], timeout: int) -> FakeResponse:
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(content=_corp_code_zip())

    mapping = fetch_corp_code_map(api_key="secret", requester=fake_get)

    assert mapping == {"005930": "00126380", "005380": "00164742"}
    assert calls[0]["params"] == {"crtfc_key": "secret"}


def test_extract_fundamentals_from_statement_uses_major_accounts() -> None:
    payload = {
        "status": "000",
        "list": [
            {"account_nm": "매출액", "thstrm_amount": "1,120"},
            {"account_nm": "영업이익", "thstrm_amount": "220"},
            {"account_nm": "당기순이익", "thstrm_amount": "160"},
            {"account_nm": "자산총계", "thstrm_amount": "2,000"},
            {"account_nm": "부채총계", "thstrm_amount": "700"},
            {"account_nm": "자본총계", "thstrm_amount": "1,300"},
        ],
    }

    row = extract_fundamentals_from_statement(symbol="005930.KS", payload=payload)

    assert row["symbol"] == "005930.KS"
    assert row["revenue_growth"] == 0.0
    assert row["operating_margin"] == 220 / 1120
    assert row["roe"] == 160 / 1300
    assert row["debt_ratio"] == 700 / 1300
    assert row["per"] == 0.0
    assert row["pbr"] == 0.0


def test_extract_fundamentals_prefers_account_ids_over_duplicate_names() -> None:
    payload = {
        "status": "000",
        "list": [
            {"account_id": "ifrs-full_Revenue", "account_nm": "매출액", "thstrm_amount": "1,000"},
            {
                "account_id": "ifrs-full_OperatingIncomeLoss",
                "account_nm": "영업이익",
                "thstrm_amount": "100",
            },
            {"account_id": "ifrs-full_ProfitLoss", "account_nm": "당기순이익", "thstrm_amount": "80"},
            {"account_id": "ifrs-full_Liabilities", "account_nm": "부채총계", "thstrm_amount": "400"},
            {"account_id": "ifrs-full_Equity", "account_nm": "자본총계", "thstrm_amount": "600"},
            {"account_nm": "부채총계", "thstrm_amount": "9,999"},
            {"account_nm": "자본총계", "thstrm_amount": "1"},
        ],
    }

    row = extract_fundamentals_from_statement(symbol="005930.KS", payload=payload)

    assert row["operating_margin"] == 0.10
    assert row["roe"] == 80 / 600
    assert row["debt_ratio"] == 400 / 600


def test_load_env_file_returns_key_without_printing_value() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        env_path = Path(tmp_dir) / ".env"
        env_path.write_text("OPENDART_API_KEY=abc123\n", encoding="utf-8")

        values = load_env_file(env_path)

        assert values["OPENDART_API_KEY"] == "abc123"


def test_extract_shares_outstanding_prefers_common_stock() -> None:
    payload = {
        "status": "000",
        "list": [
            {"se": "우선주", "istc_totqy": "1,000"},
            {"se": "보통주", "istc_totqy": "5,969,782,550"},
            {"se": "합계", "istc_totqy": "5,970,000,000"},
        ],
    }

    shares = extract_shares_outstanding(payload)

    assert shares == 5969782550.0


def test_fetch_disclosure_list_calls_opendart_list_endpoint() -> None:
    calls: list[dict[str, object]] = []

    def fake_get(url: str, params: dict[str, object], timeout: int) -> FakeResponse:
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(payload={"status": "000", "list": []})

    payload = fetch_disclosure_list(
        api_key="secret",
        corp_code="00126380",
        begin_date="20260101",
        end_date="20260527",
        requester=fake_get,
    )

    assert payload == {"status": "000", "list": []}
    assert calls[0]["url"].endswith("/api/list.json")
    assert calls[0]["params"] == {
        "crtfc_key": "secret",
        "corp_code": "00126380",
        "bgn_de": "20260101",
        "end_de": "20260527",
        "page_count": "100",
    }


def test_extract_disclosure_rows_normalizes_list_response() -> None:
    payload = {
        "status": "000",
        "list": [
            {
                "corp_code": "00126380",
                "corp_name": "삼성전자",
                "stock_code": "005930",
                "report_nm": "분기보고서 (2026.03)",
                "rcept_no": "20260515000123",
                "rcept_dt": "20260515",
                "rm": "",
            }
        ],
    }

    rows = extract_disclosure_rows(symbol="005930.KS", payload=payload)

    assert rows.to_dict("records") == [
        {
            "symbol": "005930.KS",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "report_nm": "분기보고서 (2026.03)",
            "rcept_no": "20260515000123",
            "rcept_dt": "20260515",
            "rm": "",
        }
    ]


def test_extract_disclosure_rows_treats_no_data_as_empty() -> None:
    rows = extract_disclosure_rows(
        symbol="005930.KS",
        payload={"status": "013", "message": "조회된 데이타가 없습니다."},
    )

    assert rows.empty
    assert list(rows.columns) == [
        "symbol",
        "corp_code",
        "corp_name",
        "stock_code",
        "report_nm",
        "rcept_no",
        "rcept_dt",
        "rm",
    ]


def test_fetch_document_file_calls_opendart_document_endpoint() -> None:
    calls: list[dict[str, object]] = []

    def fake_get(url: str, params: dict[str, object], timeout: int) -> FakeResponse:
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(content=_document_zip())

    content = fetch_document_file(api_key="secret", receipt_no="20260312000856", requester=fake_get)

    assert content == _document_zip()
    assert calls[0]["url"].endswith("/api/document.xml")
    assert calls[0]["params"] == {"crtfc_key": "secret", "rcept_no": "20260312000856"}


def test_extract_document_text_from_zip_reads_xml_text() -> None:
    text = extract_document_text_from_zip(_document_zip())

    assert "사업보고서" in text
    assert "우발채무" in text
    assert "특수관계자" in text
