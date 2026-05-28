from __future__ import annotations

import html
import io
import logging
import os
import re
import zipfile
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree

import pandas as pd
import requests

logger = logging.getLogger(__name__)

RequestGet = Callable[..., object]

CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
DISCLOSURE_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"
SINGLE_ACCOUNT_ALL_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
STOCK_TOTAL_URL = "https://opendart.fss.or.kr/api/stockTotqySttus.json"


def load_env_file(path: Path | str) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", maxsplit=1)
        values[key.strip()] = value.strip()
    return values


def load_opendart_api_key(env_path: Path | str | None = None) -> str:
    value = os.environ.get("OPENDART_API_KEY", "").strip()
    if value:
        return value
    if env_path is not None:
        value = load_env_file(env_path).get("OPENDART_API_KEY", "").strip()
        if value:
            return value
    raise ValueError("OPENDART_API_KEY is missing. Set it in the environment or .env file.")


def fetch_corp_code_map(
    api_key: str,
    requester: RequestGet | None = None,
    timeout: int = 30,
) -> dict[str, str]:
    get = requester or requests.get
    response = get(CORP_CODE_URL, params={"crtfc_key": api_key}, timeout=timeout)
    response.raise_for_status()
    return _parse_corp_code_zip(response.content)


def fetch_single_company_statement(
    api_key: str,
    corp_code: str,
    business_year: int,
    report_code: str = "11011",
    fs_div: str = "CFS",
    requester: RequestGet | None = None,
    timeout: int = 30,
) -> dict[str, object]:
    get = requester or requests.get
    response = get(
        SINGLE_ACCOUNT_ALL_URL,
        params={
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": str(business_year),
            "reprt_code": report_code,
            "fs_div": fs_div,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("OpenDART response must be a JSON object.")
    return payload


def fetch_disclosure_list(
    api_key: str,
    corp_code: str,
    begin_date: str,
    end_date: str,
    page_count: int = 100,
    requester: RequestGet | None = None,
    timeout: int = 30,
) -> dict[str, object]:
    get = requester or requests.get
    response = get(
        DISCLOSURE_LIST_URL,
        params={
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bgn_de": begin_date,
            "end_de": end_date,
            "page_count": str(page_count),
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("OpenDART disclosure list response must be a JSON object.")
    return payload


def fetch_document_file(
    api_key: str,
    receipt_no: str,
    requester: RequestGet | None = None,
    timeout: int = 30,
) -> bytes:
    get = requester or requests.get
    response = get(
        DOCUMENT_URL,
        params={"crtfc_key": api_key, "rcept_no": receipt_no},
        timeout=timeout,
    )
    response.raise_for_status()
    return bytes(response.content)


def extract_document_text_from_zip(content: bytes) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            raw = archive.read(name)
            text = _decode_document_bytes(raw)
            parts.append(_extract_text_from_xml_like_content(text))
    return "\n".join(part for part in parts if part.strip())


def fetch_fundamentals_for_universe(
    universe_csv: Path | str,
    api_key: str,
    business_year: int,
    report_code: str = "11011",
    fs_div: str = "CFS",
    requester: RequestGet | None = None,
) -> pd.DataFrame:
    universe = pd.read_csv(universe_csv, dtype=str).fillna("")
    if "symbol" not in universe.columns:
        raise ValueError("Universe CSV must include a 'symbol' column.")

    corp_code_map = fetch_corp_code_map(api_key=api_key, requester=requester)
    rows: list[dict[str, float | str]] = []
    for symbol in universe["symbol"].astype(str).str.strip():
        stock_code = _stock_code_from_symbol(symbol)
        corp_code = corp_code_map.get(stock_code)
        if not corp_code:
            logger.warning("No OpenDART corp_code found for %s", symbol)
            continue
        payload = fetch_single_company_statement(
            api_key=api_key,
            corp_code=corp_code,
            business_year=business_year,
            report_code=report_code,
            fs_div=fs_div,
            requester=requester,
        )
        rows.append(extract_fundamentals_from_statement(symbol=symbol, payload=payload))

    if not rows:
        raise ValueError("No fundamentals rows were fetched.")
    return pd.DataFrame(rows)


def extract_disclosure_rows(symbol: str, payload: dict[str, object]) -> pd.DataFrame:
    columns = [
        "symbol",
        "corp_code",
        "corp_name",
        "stock_code",
        "report_nm",
        "rcept_no",
        "rcept_dt",
        "rm",
    ]
    status = str(payload.get("status", ""))
    if status == "013":
        return pd.DataFrame(columns=columns)
    if status != "000":
        message = str(payload.get("message", "OpenDART request failed"))
        raise ValueError(f"OpenDART disclosure list response failed: {status} {message}")

    items = payload.get("list")
    if not isinstance(items, list):
        raise ValueError("OpenDART disclosure list response missing list.")

    rows: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "symbol": symbol,
                "corp_code": str(item.get("corp_code", "")).strip(),
                "corp_name": str(item.get("corp_name", "")).strip(),
                "stock_code": str(item.get("stock_code", "")).strip(),
                "report_nm": str(item.get("report_nm", "")).strip(),
                "rcept_no": str(item.get("rcept_no", "")).strip(),
                "rcept_dt": str(item.get("rcept_dt", "")).strip(),
                "rm": str(item.get("rm", "")).strip(),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def fetch_shares_for_universe(
    universe_csv: Path | str,
    api_key: str,
    business_year: int,
    report_code: str = "11011",
    requester: RequestGet | None = None,
) -> pd.DataFrame:
    universe = pd.read_csv(universe_csv, dtype=str).fillna("")
    if "symbol" not in universe.columns:
        raise ValueError("Universe CSV must include a 'symbol' column.")

    corp_code_map = fetch_corp_code_map(api_key=api_key, requester=requester)
    rows: list[dict[str, float | str]] = []
    for symbol in universe["symbol"].astype(str).str.strip():
        stock_code = _stock_code_from_symbol(symbol)
        corp_code = corp_code_map.get(stock_code)
        if not corp_code:
            logger.warning("No OpenDART corp_code found for %s", symbol)
            continue
        payload = fetch_stock_total_status(
            api_key=api_key,
            corp_code=corp_code,
            business_year=business_year,
            report_code=report_code,
            requester=requester,
        )
        rows.append(
            {
                "symbol": symbol,
                "shares_outstanding": extract_shares_outstanding(payload),
            }
        )

    if not rows:
        raise ValueError("No share rows were fetched.")
    return pd.DataFrame(rows)


def fetch_stock_total_status(
    api_key: str,
    corp_code: str,
    business_year: int,
    report_code: str = "11011",
    requester: RequestGet | None = None,
    timeout: int = 30,
) -> dict[str, object]:
    get = requester or requests.get
    response = get(
        STOCK_TOTAL_URL,
        params={
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": str(business_year),
            "reprt_code": report_code,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("OpenDART stock total response must be a JSON object.")
    return payload


def extract_fundamentals_from_statement(
    symbol: str,
    payload: dict[str, object],
) -> dict[str, float | str]:
    status = str(payload.get("status", ""))
    if status != "000":
        message = str(payload.get("message", "OpenDART request failed"))
        raise ValueError(f"OpenDART statement response failed: {status} {message}")

    items = payload.get("list")
    if not isinstance(items, list):
        raise ValueError("OpenDART statement response missing list.")

    accounts_by_id: dict[str, float] = {}
    accounts_by_name: dict[str, float] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        account_id = str(item.get("account_id", "")).strip()
        account_name = str(item.get("account_nm", "")).strip()
        amount = _parse_amount(item.get("thstrm_amount"))
        if amount is None:
            continue
        if account_id and account_id not in accounts_by_id:
            accounts_by_id[account_id] = amount
        if account_name and account_name not in accounts_by_name:
            accounts_by_name[account_name] = amount

    revenue = _first_account_by_id_or_name(
        accounts_by_id,
        accounts_by_name,
        ids=["ifrs-full_Revenue"],
        names=["매출액", "영업수익"],
    )
    operating_income = _first_account_by_id_or_name(
        accounts_by_id,
        accounts_by_name,
        ids=["ifrs-full_OperatingIncomeLoss"],
        names=["영업이익", "영업손실"],
    )
    net_income = _first_account_by_id_or_name(
        accounts_by_id,
        accounts_by_name,
        ids=["ifrs-full_ProfitLoss"],
        names=["당기순이익", "당기순손실"],
    )
    liabilities = _first_account_by_id_or_name(
        accounts_by_id,
        accounts_by_name,
        ids=["ifrs-full_Liabilities"],
        names=["부채총계"],
    )
    equity = _first_account_by_id_or_name(
        accounts_by_id,
        accounts_by_name,
        ids=["ifrs-full_Equity"],
        names=["자본총계"],
    )

    operating_margin = operating_income / revenue if revenue else 0.0
    roe = net_income / equity if equity else 0.0
    debt_ratio = liabilities / equity if equity else 0.0
    return {
        "symbol": symbol,
        "revenue": revenue,
        "operating_income": operating_income,
        "net_income": net_income,
        "liabilities": liabilities,
        "equity": equity,
        "revenue_growth": 0.0,
        "operating_margin": operating_margin,
        "roe": roe,
        "per": 0.0,
        "pbr": 0.0,
        "debt_ratio": debt_ratio,
    }


def extract_shares_outstanding(payload: dict[str, object]) -> float:
    status = str(payload.get("status", ""))
    if status != "000":
        message = str(payload.get("message", "OpenDART request failed"))
        raise ValueError(f"OpenDART stock total response failed: {status} {message}")

    items = payload.get("list")
    if not isinstance(items, list):
        raise ValueError("OpenDART stock total response missing list.")

    fallback_total = 0.0
    for item in items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("se", "")).strip()
        quantity = _parse_amount(item.get("istc_totqy"))
        if quantity is None:
            continue
        if label == "보통주":
            return quantity
        if label == "합계":
            fallback_total = quantity
    if fallback_total:
        return fallback_total
    raise ValueError("OpenDART stock total response has no common or total share count.")


def _parse_corp_code_zip(content: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = [name for name in archive.namelist() if name.upper().endswith(".XML")]
        if not names:
            raise ValueError("OpenDART corpCode zip does not contain XML.")
        xml_bytes = archive.read(names[0])

    root = ElementTree.fromstring(xml_bytes)
    mapping: dict[str, str] = {}
    for node in root.findall("list"):
        corp_code = (node.findtext("corp_code") or "").strip()
        stock_code = (node.findtext("stock_code") or "").strip()
        if corp_code and stock_code:
            mapping[stock_code.zfill(6)] = corp_code
    if not mapping:
        raise ValueError("OpenDART corpCode map is empty.")
    return mapping


def _parse_amount(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _first_account(accounts: dict[str, float], names: list[str]) -> float:
    for name in names:
        if name in accounts:
            return accounts[name]
    return 0.0


def _first_account_by_id_or_name(
    accounts_by_id: dict[str, float],
    accounts_by_name: dict[str, float],
    ids: list[str],
    names: list[str],
) -> float:
    for account_id in ids:
        if account_id in accounts_by_id:
            return accounts_by_id[account_id]
    return _first_account(accounts_by_name, names)


def _stock_code_from_symbol(symbol: str) -> str:
    return symbol.split(".", maxsplit=1)[0].zfill(6)


def _decode_document_bytes(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_text_from_xml_like_content(text: str) -> str:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        without_tags = re.sub(r"<[^>]+>", " ", text)
        return _normalize_document_text(html.unescape(without_tags))
    return _normalize_document_text(" ".join(fragment for fragment in root.itertext() if fragment))


def _normalize_document_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
