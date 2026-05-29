from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.krx_universe import fetch_pykrx_equity_universe


class FakePykrxStockProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str | None, str]] = []

    def get_market_ticker_list(self, date: str | None = None, market: str = "KOSPI") -> list[str]:
        self.calls.append((date, market))
        return {
            "KOSPI": ["005930", "000545"],
            "KOSDAQ": ["091990"],
        }[market]

    def get_market_ticker_name(self, code: str) -> str:
        return {
            "005930": "Samsung Electronics",
            "000545": "Heungkuk Fire Preferred",
            "091990": "Celltrion Healthcare",
        }[code]


class EmptyPykrxStockProvider:
    def get_market_ticker_list(self, date: str | None = None, market: str = "KOSPI") -> list[str]:
        return []

    def get_market_ticker_name(self, code: str) -> str:
        return code


def test_fetch_pykrx_equity_universe_builds_kospi_and_kosdaq_symbols() -> None:
    universe = fetch_pykrx_equity_universe(provider=FakePykrxStockProvider())

    assert universe["symbol"].tolist() == ["005930.KS", "000545.KS", "091990.KQ"]
    assert universe["company_name"].tolist() == [
        "Samsung Electronics",
        "Heungkuk Fire Preferred",
        "Celltrion Healthcare",
    ]
    assert universe["market"].tolist() == ["KOSPI", "KOSPI", "KOSDAQ"]
    assert universe["security_type"].tolist() == ["STOCK", "STOCK", "STOCK"]
    assert universe["share_type"].tolist() == ["UNKNOWN", "UNKNOWN", "UNKNOWN"]
    assert universe["listing_status"].tolist() == ["LISTED", "LISTED", "LISTED"]


def test_fetch_pykrx_equity_universe_passes_explicit_date_to_provider() -> None:
    provider = FakePykrxStockProvider()

    fetch_pykrx_equity_universe(provider=provider, date="20260529")

    assert provider.calls == [("20260529", "KOSPI"), ("20260529", "KOSDAQ")]


def test_fetch_pykrx_equity_universe_rejects_empty_provider_result() -> None:
    with pytest.raises(ValueError, match="returned no tickers"):
        fetch_pykrx_equity_universe(provider=EmptyPykrxStockProvider())
