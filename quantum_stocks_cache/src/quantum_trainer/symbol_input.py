from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class ResolvedStockInput:
    raw_input: str
    symbol: str
    code: str
    company_name: str
    market: str
    sector: str
    source: str


@dataclass(frozen=True)
class StockSearchCandidate:
    symbol: str
    code: str
    company_name: str
    market: str
    sector: str
    source: str
    match_score: int


_DISPLAY_NAME_BY_ENGLISH: dict[str, str] = {
    "Samsung Electronics": "삼성전자",
    "SK hynix": "SK하이닉스",
    "NAVER": "NAVER",
    "Kakao": "카카오",
    "Hyundai Motor": "현대차",
    "LG Chem": "LG화학",
    "LG Energy Solution": "LG에너지솔루션",
    "Samsung Biologics": "삼성바이오로직스",
    "Kia": "기아",
    "Celltrion": "셀트리온",
    "POSCO Holdings": "포스코홀딩스",
    "Samsung SDI": "삼성SDI",
    "Hyundai Mobis": "현대모비스",
    "Samsung C&T": "삼성물산",
    "KB Financial": "KB금융",
    "Shinhan Financial": "신한지주",
    "Hana Financial": "하나금융지주",
    "Woori Financial": "우리금융지주",
    "Samsung Life": "삼성생명",
    "Meritz Financial": "메리츠금융지주",
    "LG Electronics": "LG전자",
    "Korea Electric Power": "한국전력",
    "LG Corp": "LG",
    "SK Inc": "SK",
    "SK Innovation": "SK이노베이션",
    "Samsung Electro-Mechanics": "삼성전기",
    "HMM": "HMM",
    "Korea Zinc": "고려아연",
    "SK Telecom": "SK텔레콤",
    "KT": "KT",
    "POSCO Future M": "포스코퓨처엠",
    "HYBE": "하이브",
    "Krafton": "크래프톤",
    "Samsung SDS": "삼성SDS",
    "NCSoft": "엔씨소프트",
}


_SECTOR_KO_BY_ENGLISH: dict[str, str] = {
    "Semiconductors": "반도체",
    "Internet": "인터넷",
    "Autos": "자동차",
    "Chemicals": "화학",
    "Battery": "배터리",
    "Biotech": "바이오",
    "Steel": "철강",
    "Holding": "지주",
    "Financials": "금융",
    "Insurance": "보험",
    "Electronics": "전자부품",
    "Utilities": "전력",
    "Energy": "에너지",
    "Shipping": "해운",
    "Materials": "소재",
    "Telecom": "통신",
    "Battery Materials": "배터리소재",
    "Entertainment": "엔터테인먼트",
    "Gaming": "게임",
    "IT Services": "IT서비스",
}


_ALIASES: dict[str, dict[str, str]] = {
    "삼성전자": {"code": "005930", "company_name": "삼성전자", "market": "KOSPI", "sector": "반도체"},
    "samsung electronics": {
        "code": "005930",
        "company_name": "삼성전자",
        "market": "KOSPI",
        "sector": "반도체",
    },
    "sk하이닉스": {"code": "000660", "company_name": "SK하이닉스", "market": "KOSPI", "sector": "반도체"},
    "sk hynix": {"code": "000660", "company_name": "SK하이닉스", "market": "KOSPI", "sector": "반도체"},
    "하이닉스": {"code": "000660", "company_name": "SK하이닉스", "market": "KOSPI", "sector": "반도체"},
    "현대차": {"code": "005380", "company_name": "현대차", "market": "KOSPI", "sector": "자동차"},
    "현대자동차": {"code": "005380", "company_name": "현대차", "market": "KOSPI", "sector": "자동차"},
    "hyundai motor": {"code": "005380", "company_name": "현대차", "market": "KOSPI", "sector": "자동차"},
    "삼성물산": {"code": "028260", "company_name": "삼성물산", "market": "KOSPI", "sector": "지주/건설"},
    "samsung c&t": {"code": "028260", "company_name": "삼성물산", "market": "KOSPI", "sector": "지주/건설"},
    "lg": {"code": "003550", "company_name": "LG", "market": "KOSPI", "sector": "지주"},
    "lg corp": {"code": "003550", "company_name": "LG", "market": "KOSPI", "sector": "지주"},
    "현대모비스": {"code": "012330", "company_name": "현대모비스", "market": "KOSPI", "sector": "자동차부품"},
    "hyundai mobis": {"code": "012330", "company_name": "현대모비스", "market": "KOSPI", "sector": "자동차부품"},
    "기아": {"code": "000270", "company_name": "기아", "market": "KOSPI", "sector": "자동차"},
    "kia": {"code": "000270", "company_name": "기아", "market": "KOSPI", "sector": "자동차"},
    "kb금융": {"code": "105560", "company_name": "KB금융", "market": "KOSPI", "sector": "금융지주"},
    "kb financial": {"code": "105560", "company_name": "KB금융", "market": "KOSPI", "sector": "금융지주"},
    "신한지주": {"code": "055550", "company_name": "신한지주", "market": "KOSPI", "sector": "금융지주"},
    "하나금융지주": {"code": "086790", "company_name": "하나금융지주", "market": "KOSPI", "sector": "금융지주"},
    "우리금융지주": {"code": "316140", "company_name": "우리금융지주", "market": "KOSPI", "sector": "금융지주"},
    "naver": {"code": "035420", "company_name": "NAVER", "market": "KOSPI", "sector": "인터넷"},
    "네이버": {"code": "035420", "company_name": "NAVER", "market": "KOSPI", "sector": "인터넷"},
    "카카오": {"code": "035720", "company_name": "카카오", "market": "KOSPI", "sector": "인터넷"},
    "kakao": {"code": "035720", "company_name": "카카오", "market": "KOSPI", "sector": "인터넷"},
    "셀트리온": {"code": "068270", "company_name": "셀트리온", "market": "KOSPI", "sector": "바이오"},
    "celltrion": {"code": "068270", "company_name": "셀트리온", "market": "KOSPI", "sector": "바이오"},
    "lg화학": {"code": "051910", "company_name": "LG화학", "market": "KOSPI", "sector": "화학"},
    "엘지화학": {"code": "051910", "company_name": "LG화학", "market": "KOSPI", "sector": "화학"},
    "lg chem": {"code": "051910", "company_name": "LG화학", "market": "KOSPI", "sector": "화학"},
    "lg에너지솔루션": {"code": "373220", "company_name": "LG에너지솔루션", "market": "KOSPI", "sector": "배터리"},
    "엘지에너지솔루션": {"code": "373220", "company_name": "LG에너지솔루션", "market": "KOSPI", "sector": "배터리"},
    "엔솔": {"code": "373220", "company_name": "LG에너지솔루션", "market": "KOSPI", "sector": "배터리"},
    "lg energy solution": {"code": "373220", "company_name": "LG에너지솔루션", "market": "KOSPI", "sector": "배터리"},
    "삼성바이오로직스": {"code": "207940", "company_name": "삼성바이오로직스", "market": "KOSPI", "sector": "바이오"},
    "삼바": {"code": "207940", "company_name": "삼성바이오로직스", "market": "KOSPI", "sector": "바이오"},
    "samsung biologics": {"code": "207940", "company_name": "삼성바이오로직스", "market": "KOSPI", "sector": "바이오"},
    "포스코홀딩스": {"code": "005490", "company_name": "포스코홀딩스", "market": "KOSPI", "sector": "철강"},
    "posco홀딩스": {"code": "005490", "company_name": "포스코홀딩스", "market": "KOSPI", "sector": "철강"},
    "posco holdings": {"code": "005490", "company_name": "포스코홀딩스", "market": "KOSPI", "sector": "철강"},
    "삼성sdi": {"code": "006400", "company_name": "삼성SDI", "market": "KOSPI", "sector": "배터리"},
    "samsung sdi": {"code": "006400", "company_name": "삼성SDI", "market": "KOSPI", "sector": "배터리"},
    "삼성생명": {"code": "032830", "company_name": "삼성생명", "market": "KOSPI", "sector": "보험"},
    "samsung life": {"code": "032830", "company_name": "삼성생명", "market": "KOSPI", "sector": "보험"},
    "메리츠금융": {"code": "138040", "company_name": "메리츠금융지주", "market": "KOSPI", "sector": "금융지주"},
    "메리츠금융지주": {"code": "138040", "company_name": "메리츠금융지주", "market": "KOSPI", "sector": "금융지주"},
    "meritz financial": {"code": "138040", "company_name": "메리츠금융지주", "market": "KOSPI", "sector": "금융지주"},
    "lg전자": {"code": "066570", "company_name": "LG전자", "market": "KOSPI", "sector": "전자"},
    "엘지전자": {"code": "066570", "company_name": "LG전자", "market": "KOSPI", "sector": "전자"},
    "lg electronics": {"code": "066570", "company_name": "LG전자", "market": "KOSPI", "sector": "전자"},
    "한국전력": {"code": "015760", "company_name": "한국전력", "market": "KOSPI", "sector": "전력"},
    "한전": {"code": "015760", "company_name": "한국전력", "market": "KOSPI", "sector": "전력"},
    "korea electric power": {"code": "015760", "company_name": "한국전력", "market": "KOSPI", "sector": "전력"},
    "엘지": {"code": "003550", "company_name": "LG", "market": "KOSPI", "sector": "지주"},
    "lg지주": {"code": "003550", "company_name": "LG", "market": "KOSPI", "sector": "지주"},
    "sk": {"code": "034730", "company_name": "SK", "market": "KOSPI", "sector": "지주"},
    "sk주식회사": {"code": "034730", "company_name": "SK", "market": "KOSPI", "sector": "지주"},
    "sk inc": {"code": "034730", "company_name": "SK", "market": "KOSPI", "sector": "지주"},
    "sk이노베이션": {"code": "096770", "company_name": "SK이노베이션", "market": "KOSPI", "sector": "에너지"},
    "에스케이이노베이션": {"code": "096770", "company_name": "SK이노베이션", "market": "KOSPI", "sector": "에너지"},
    "sk innovation": {"code": "096770", "company_name": "SK이노베이션", "market": "KOSPI", "sector": "에너지"},
    "삼성전기": {"code": "009150", "company_name": "삼성전기", "market": "KOSPI", "sector": "전자부품"},
    "samsung electro-mechanics": {"code": "009150", "company_name": "삼성전기", "market": "KOSPI", "sector": "전자부품"},
    "hmm": {"code": "011200", "company_name": "HMM", "market": "KOSPI", "sector": "해운"},
    "에이치엠엠": {"code": "011200", "company_name": "HMM", "market": "KOSPI", "sector": "해운"},
    "고려아연": {"code": "010130", "company_name": "고려아연", "market": "KOSPI", "sector": "소재"},
    "korea zinc": {"code": "010130", "company_name": "고려아연", "market": "KOSPI", "sector": "소재"},
    "sk텔레콤": {"code": "017670", "company_name": "SK텔레콤", "market": "KOSPI", "sector": "통신"},
    "에스케이텔레콤": {"code": "017670", "company_name": "SK텔레콤", "market": "KOSPI", "sector": "통신"},
    "sk telecom": {"code": "017670", "company_name": "SK텔레콤", "market": "KOSPI", "sector": "통신"},
    "kt": {"code": "030200", "company_name": "KT", "market": "KOSPI", "sector": "통신"},
    "케이티": {"code": "030200", "company_name": "KT", "market": "KOSPI", "sector": "통신"},
    "포스코퓨처엠": {"code": "003670", "company_name": "포스코퓨처엠", "market": "KOSPI", "sector": "배터리소재"},
    "posco future m": {"code": "003670", "company_name": "포스코퓨처엠", "market": "KOSPI", "sector": "배터리소재"},
    "하이브": {"code": "352820", "company_name": "하이브", "market": "KOSPI", "sector": "엔터테인먼트"},
    "hybe": {"code": "352820", "company_name": "하이브", "market": "KOSPI", "sector": "엔터테인먼트"},
    "크래프톤": {"code": "259960", "company_name": "크래프톤", "market": "KOSPI", "sector": "게임"},
    "krafton": {"code": "259960", "company_name": "크래프톤", "market": "KOSPI", "sector": "게임"},
    "삼성sds": {"code": "018260", "company_name": "삼성SDS", "market": "KOSPI", "sector": "IT서비스"},
    "삼성에스디에스": {"code": "018260", "company_name": "삼성SDS", "market": "KOSPI", "sector": "IT서비스"},
    "samsung sds": {"code": "018260", "company_name": "삼성SDS", "market": "KOSPI", "sector": "IT서비스"},
    "엔씨소프트": {"code": "036570", "company_name": "엔씨소프트", "market": "KOSPI", "sector": "게임"},
    "nc소프트": {"code": "036570", "company_name": "엔씨소프트", "market": "KOSPI", "sector": "게임"},
    "ncsoft": {"code": "036570", "company_name": "엔씨소프트", "market": "KOSPI", "sector": "게임"},
}


def resolve_stock_input(raw_input: str, universe_csv: Path | str | None = None) -> ResolvedStockInput:
    text = str(raw_input).strip()
    if not text:
        raise ValueError("종목명을 입력하거나 6자리 종목코드를 입력하세요.")

    universe_match = _resolve_from_universe(text, universe_csv)
    if universe_match:
        return universe_match

    alias = _ALIASES.get(_key(text))
    if alias:
        return _resolved(
            raw_input=text,
            code=alias["code"],
            company_name=alias["company_name"],
            market=alias["market"],
            sector=alias["sector"],
            source="alias",
        )

    if _looks_like_symbol(text):
        code, market = _split_symbol(text)
        return _resolved(
            raw_input=text,
            code=code,
            company_name=text.upper(),
            market=market,
            sector="UNKNOWN",
            source="symbol",
        )

    if _looks_like_code(text):
        return _resolved(
            raw_input=text,
            code=text,
            company_name=text.zfill(6),
            market="KOSPI",
            sector="UNKNOWN",
            source="code",
        )

    raise ValueError(
        f"'{text}'은 로컬에서 바로 찾을 수 없습니다. 외부 조회 없이 진행하려면 6자리 종목코드로 입력하세요."
    )


def search_stock_inputs(
    query: str,
    universe_csv: Path | str | None = None,
    limit: int = 8,
) -> list[StockSearchCandidate]:
    text = str(query).strip()
    if not text:
        return []

    results: dict[str, StockSearchCandidate] = {}
    for alias_text, alias in _ALIASES.items():
        resolved = _resolved(
            raw_input=alias_text,
            code=alias["code"],
            company_name=alias["company_name"],
            market=alias["market"],
            sector=alias["sector"],
            source="alias",
        )
        score = _match_score(text, [alias_text, resolved.company_name, resolved.code, resolved.symbol])
        if score:
            _add_candidate(results, _candidate_from_resolved(resolved, score))

    for row in _universe_rows(universe_csv):
        company_name = _display_company_name(str(row.get("company_name", "")))
        sector = _display_sector(str(row.get("sector", "")))
        resolved = _resolved(
            raw_input=company_name,
            code=str(row.get("code", "") or _code_from_symbol(str(row.get("symbol", "")))),
            company_name=company_name,
            market=str(row.get("market", "") or _market_from_symbol(str(row.get("symbol", "")))),
            sector=sector,
            source="universe",
        )
        score = _match_score(
            text,
            [
                company_name,
                str(row.get("company_name", "")),
                resolved.code,
                resolved.symbol,
            ],
        )
        if score:
            _add_candidate(results, _candidate_from_resolved(resolved, score))

    return sorted(results.values(), key=lambda item: (-item.match_score, item.company_name, item.code))[:limit]


def _resolve_from_universe(raw_input: str, universe_csv: Path | str | None) -> ResolvedStockInput | None:
    if not universe_csv:
        return None
    path = Path(universe_csv)
    if not path.exists():
        return None
    universe = pd.read_csv(path, dtype=str).fillna("")
    if universe.empty:
        return None

    normalized_input = _key(raw_input)
    candidates = universe.copy()
    for column in ["symbol", "company_name", "code"]:
        if column not in candidates.columns:
            candidates[column] = ""
    matched = candidates.loc[
        (candidates["company_name"].map(_key) == normalized_input)
        | (candidates["symbol"].map(_key) == normalized_input)
        | (candidates["code"].astype(str).str.zfill(6) == raw_input.strip().zfill(6))
    ]
    if matched.empty:
        return None

    row = matched.iloc[0]
    code = str(row.get("code", "")) or _code_from_symbol(str(row.get("symbol", "")))
    market = str(row.get("market", "")) or _market_from_symbol(str(row.get("symbol", "")))
    return _resolved(
        raw_input=raw_input,
        code=code,
        company_name=_display_company_name(str(row.get("company_name", "") or raw_input)),
        market=market or "KOSPI",
        sector=_display_sector(str(row.get("sector", "") or "UNKNOWN")),
        source="universe",
    )


def _universe_rows(universe_csv: Path | str | None) -> list[dict[str, str]]:
    if not universe_csv:
        return []
    path = Path(universe_csv)
    if not path.exists():
        return []
    universe = pd.read_csv(path, dtype=str).fillna("")
    if universe.empty:
        return []
    return [row.to_dict() for _, row in universe.iterrows()]


def _display_company_name(value: str) -> str:
    text = str(value).strip()
    return _DISPLAY_NAME_BY_ENGLISH.get(text, text)


def _display_sector(value: str) -> str:
    text = str(value).strip()
    return _SECTOR_KO_BY_ENGLISH.get(text, text or "UNKNOWN")


def _match_score(query: str, terms: list[str]) -> int:
    q = _key(query)
    for term in terms:
        key = _key(term)
        if key == q:
            return 100
    for term in terms:
        key = _key(term)
        if key.startswith(q):
            return 80
    for term in terms:
        key = _key(term)
        if q in key:
            return 55
    return 0


def _candidate_from_resolved(resolved: ResolvedStockInput, score: int) -> StockSearchCandidate:
    return StockSearchCandidate(
        symbol=resolved.symbol,
        code=resolved.code,
        company_name=resolved.company_name,
        market=resolved.market,
        sector=resolved.sector,
        source=resolved.source,
        match_score=score,
    )


def _add_candidate(
    results: dict[str, StockSearchCandidate],
    candidate: StockSearchCandidate,
) -> None:
    existing = results.get(candidate.symbol)
    if existing is None or candidate.match_score > existing.match_score:
        results[candidate.symbol] = candidate


def _resolved(
    raw_input: str,
    code: str,
    company_name: str,
    market: str,
    sector: str,
    source: str,
) -> ResolvedStockInput:
    normalized_code = str(code).strip().zfill(6)
    normalized_market = _normalize_market(market)
    suffix = ".KQ" if normalized_market == "KOSDAQ" else ".KS"
    return ResolvedStockInput(
        raw_input=raw_input,
        symbol=f"{normalized_code}{suffix}",
        code=normalized_code,
        company_name=str(company_name).strip() or normalized_code,
        market=normalized_market,
        sector=str(sector).strip() or "UNKNOWN",
        source=source,
    )


def _key(value: object) -> str:
    return str(value).strip().lower().replace(" ", "")


def _looks_like_code(value: str) -> bool:
    return value.strip().isdigit() and len(value.strip()) <= 6


def _looks_like_symbol(value: str) -> bool:
    text = value.strip().upper()
    return (text.endswith(".KS") or text.endswith(".KQ")) and text.split(".", maxsplit=1)[0].isdigit()


def _split_symbol(value: str) -> tuple[str, str]:
    text = value.strip().upper()
    code, suffix = text.split(".", maxsplit=1)
    market = "KOSDAQ" if suffix == "KQ" else "KOSPI"
    return code.zfill(6), market


def _code_from_symbol(symbol: str) -> str:
    text = symbol.strip().upper()
    if "." in text:
        text = text.split(".", maxsplit=1)[0]
    return text.zfill(6) if text.isdigit() else text


def _market_from_symbol(symbol: str) -> str:
    text = symbol.strip().upper()
    if text.endswith(".KQ"):
        return "KOSDAQ"
    if text.endswith(".KS"):
        return "KOSPI"
    return ""


def _normalize_market(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"KQ", "KOSDAQ"}:
        return "KOSDAQ"
    return "KOSPI"
