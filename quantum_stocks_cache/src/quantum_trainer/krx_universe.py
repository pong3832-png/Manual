from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

import pandas as pd

from quantum_trainer.research_universe import normalize_full_krx_universe

DEFAULT_EQUITY_MARKETS = ("KOSPI", "KOSDAQ")


class PykrxStockProvider(Protocol):
    def get_market_ticker_list(self, date: str | None = None, market: str = "KOSPI") -> list[str]:
        ...

    def get_market_ticker_name(self, code: str) -> str:
        ...


def fetch_pykrx_equity_universe(
    provider: PykrxStockProvider | None = None,
    markets: Iterable[str] = DEFAULT_EQUITY_MARKETS,
    date: str | None = None,
) -> pd.DataFrame:
    if provider is None:
        from pykrx import stock as provider

    rows: list[dict[str, str]] = []
    for market in markets:
        normalized_market = str(market).strip().upper()
        if date:
            tickers = provider.get_market_ticker_list(date=date, market=normalized_market)
        else:
            tickers = provider.get_market_ticker_list(market=normalized_market)
        for raw_code in tickers:
            code = str(raw_code).strip().zfill(6)
            rows.append(
                {
                    "code": code,
                    "company_name": str(provider.get_market_ticker_name(code)).strip(),
                    "market": normalized_market,
                    "sector": "UNKNOWN",
                    "security_type": "STOCK",
                    "share_type": "UNKNOWN",
                    "listing_status": "LISTED",
                }
            )

    if not rows:
        raise ValueError("pykrx returned no tickers for requested markets.")

    universe = normalize_full_krx_universe(pd.DataFrame(rows))
    return universe.drop_duplicates(subset=["symbol"], keep="first").reset_index(drop=True)
