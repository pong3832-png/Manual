from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import pandas as pd

logger = logging.getLogger(__name__)

DownloadFn = Callable[..., pd.DataFrame]


@dataclass(frozen=True)
class MarketDataConfig:
    provider: str = "yfinance"
    start: str = "2024-01-01"
    end: str | None = None
    auto_adjust: bool = True
    progress: bool = False


def _load_yfinance_downloader() -> DownloadFn:
    try:
        import yfinance as yf

        return yf.download
    except Exception as exc:
        logger.exception("Failed to load yfinance: %s", exc)
        raise


def _extract_close_frame(raw: pd.DataFrame, symbols: Sequence[str]) -> pd.DataFrame:
    try:
        if raw.empty:
            raise ValueError("Downloaded market data is empty.")

        if isinstance(raw.columns, pd.MultiIndex):
            if "Close" in raw.columns.get_level_values(0):
                close = raw["Close"]
            elif "Adj Close" in raw.columns.get_level_values(0):
                close = raw["Adj Close"]
            else:
                raise ValueError("Downloaded data does not contain Close or Adj Close.")
        else:
            close_col = "Close" if "Close" in raw.columns else "Adj Close"
            if close_col not in raw.columns:
                raise ValueError("Downloaded data does not contain Close or Adj Close.")
            if len(symbols) != 1:
                raise ValueError("Single-level close data is only valid for one symbol.")
            close = raw[[close_col]].rename(columns={close_col: symbols[0]})

        prices = close.copy()
        prices.columns = [str(column) for column in prices.columns]
        prices = prices.reindex(columns=list(symbols)).ffill().dropna(how="any")
        prices.index = pd.to_datetime(prices.index)
        prices.index.name = "date"
        if prices.empty:
            raise ValueError("Price frame is empty after close extraction.")
        return prices
    except Exception as exc:
        logger.exception("Failed to extract close prices: %s", exc)
        raise


def fetch_market_prices(
    symbols: Sequence[str],
    config: MarketDataConfig,
    downloader: DownloadFn | None = None,
) -> pd.DataFrame:
    try:
        if config.provider != "yfinance":
            raise ValueError(f"Unsupported market data provider: {config.provider}")
        if not symbols:
            raise ValueError("symbols must not be empty.")

        download = downloader or _load_yfinance_downloader()
        raw = download(
            tickers=list(symbols),
            start=config.start,
            end=config.end,
            auto_adjust=config.auto_adjust,
            progress=config.progress,
            group_by="column",
            threads=True,
        )
        return _extract_close_frame(raw, symbols)
    except Exception as exc:
        logger.exception("Failed to fetch market prices: %s", exc)
        raise


def resolve_market_data_symbols(
    portfolio_symbols: Sequence[str],
    universe_csv: Path | str | None = None,
) -> list[str]:
    if universe_csv is None:
        symbols = [str(symbol).strip() for symbol in portfolio_symbols]
    else:
        path = Path(universe_csv).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Research universe CSV not found: {path}")
        universe = pd.read_csv(path, dtype=str).fillna("")
        if "symbol" not in universe.columns:
            raise ValueError("Research universe CSV must include a 'symbol' column.")
        symbols = universe["symbol"].astype(str).str.strip().tolist()

    symbols = [symbol for symbol in symbols if symbol]
    if not symbols:
        raise ValueError("No market data symbols resolved.")
    if len(symbols) != len(set(symbols)):
        raise ValueError("Market data symbols contain duplicates.")
    return symbols


async def fetch_market_prices_async(
    symbols: Sequence[str],
    config: MarketDataConfig,
    downloader: DownloadFn | None = None,
) -> pd.DataFrame:
    try:
        return await asyncio.to_thread(fetch_market_prices, symbols, config, downloader)
    except Exception as exc:
        logger.exception("Async market price fetch failed: %s", exc)
        raise


def write_price_cache(prices: pd.DataFrame, output_path: Path | str) -> Path:
    try:
        path = Path(output_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        prices.to_csv(path, encoding="utf-8-sig", index_label="date")
        return path
    except Exception as exc:
        logger.exception("Failed to write price cache: %s", exc)
        raise
