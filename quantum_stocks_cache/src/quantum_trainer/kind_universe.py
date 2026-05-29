from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

from quantum_trainer.research_universe import normalize_full_krx_universe

COMPANY_COL = "\ud68c\uc0ac\uba85"
MARKET_COL = "\uc2dc\uc7a5\uad6c\ubd84"
CODE_COL = "\uc885\ubaa9\ucf54\ub4dc"
SECTOR_COL = "\uc5c5\uc885"
DEFAULT_KIND_MARKETS = ("KOSPI", "KOSDAQ")


class _HtmlTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "tr":
            self._row = []
        elif tag.lower() in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(_clean_cell_text("".join(self._cell)))
            self._cell = None
        elif normalized_tag == "tr" and self._row is not None:
            if any(value != "" for value in self._row):
                self.rows.append(self._row)
            self._row = None
            self._cell = None


def parse_kind_corp_list_html(html: str) -> pd.DataFrame:
    parser = _HtmlTableParser()
    parser.feed(html)
    if not parser.rows:
        return pd.DataFrame()

    header = parser.rows[0]
    data_rows = [row for row in parser.rows[1:] if len(row) == len(header)]
    return pd.DataFrame(data_rows, columns=header).fillna("")


def read_kind_corp_list(path: Path | str, encoding: str = "euc-kr") -> pd.DataFrame:
    source_path = Path(path).resolve()
    html = source_path.read_text(encoding=encoding, errors="replace")
    return parse_kind_corp_list_html(html)


def normalize_kind_corp_list(
    source: pd.DataFrame,
    markets: tuple[str, ...] = DEFAULT_KIND_MARKETS,
) -> pd.DataFrame:
    if source.empty:
        raise ValueError("KIND corp list is empty.")
    required = [COMPANY_COL, MARKET_COL, CODE_COL, SECTOR_COL]
    missing = [column for column in required if column not in source.columns]
    if missing:
        raise ValueError(f"KIND corp list missing required columns: {missing}")

    base = pd.DataFrame(
        {
            "code": source[CODE_COL].astype(str).str.strip(),
            "company_name": source[COMPANY_COL].astype(str).str.strip(),
            "market": source[MARKET_COL].astype(str).map(_normalize_kind_market),
            "sector": source[SECTOR_COL].astype(str).str.strip(),
            "security_type": "STOCK",
            "share_type": "UNKNOWN",
            "listing_status": "LISTED",
        }
    )
    allowed_markets = {market.upper() for market in markets}
    base = base.loc[base["market"].isin(allowed_markets)].copy()
    if base.empty:
        raise ValueError("KIND corp list has no KOSPI/KOSDAQ rows after filtering.")

    return normalize_full_krx_universe(base).drop_duplicates(subset=["symbol"], keep="first").reset_index(drop=True)


def _clean_cell_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _normalize_kind_market(value: str) -> str:
    compact = re.sub(r"\s+", "", str(value)).upper()
    market_map = {
        "\ucf54\uc2a4\ud53c": "KOSPI",
        "\uc720\uac00": "KOSPI",
        "\uc720\uac00\uc99d\uad8c": "KOSPI",
        "KOSPI": "KOSPI",
        "\ucf54\uc2a4\ub2e5": "KOSDAQ",
        "KOSDAQ": "KOSDAQ",
        "\ucf54\ub125\uc2a4": "KONEX",
        "KONEX": "KONEX",
    }
    return market_map.get(compact, compact)
