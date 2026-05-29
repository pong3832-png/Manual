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


def fetch_market_prices_batched(
    symbols: Sequence[str],
    config: MarketDataConfig,
    batch_size: int = 200,
    downloader: DownloadFn | None = None,
    allow_partial: bool = False,
) -> pd.DataFrame:
    try:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0.")
        cleaned = [str(symbol).strip() for symbol in symbols if str(symbol).strip()]
        if not cleaned:
            raise ValueError("symbols must not be empty.")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Market data symbols contain duplicates.")

        frames: list[pd.DataFrame] = []
        for start in range(0, len(cleaned), batch_size):
            batch = cleaned[start : start + batch_size]
            if allow_partial:
                frame = _fetch_market_prices_batch_allow_partial(
                    batch,
                    config=config,
                    downloader=downloader,
                )
                if not frame.empty:
                    frames.append(frame)
            else:
                frames.append(fetch_market_prices(batch, config=config, downloader=downloader))

        if not frames:
            raise ValueError("No market data could be fetched for requested symbols.")
        prices = pd.concat(frames, axis=1)
        prices = prices.loc[:, ~prices.columns.duplicated()]
        columns = [symbol for symbol in cleaned if symbol in prices.columns] if allow_partial else cleaned
        drop_mode = "all" if allow_partial else "any"
        prices = prices.reindex(columns=columns).ffill().dropna(how=drop_mode)
        prices.index.name = "date"
        if prices.empty:
            raise ValueError("Price frame is empty after batched fetch.")
        return prices
    except Exception as exc:
        logger.exception("Failed to fetch batched market prices: %s", exc)
        raise


def _fetch_market_prices_batch_allow_partial(
    symbols: Sequence[str],
    config: MarketDataConfig,
    downloader: DownloadFn | None = None,
) -> pd.DataFrame:
    try:
        return fetch_market_prices(symbols, config=config, downloader=downloader)
    except Exception as exc:
        if len(symbols) == 1:
            logger.warning("Skipping symbol with unavailable market data: %s (%s)", symbols[0], exc)
            return pd.DataFrame()

        midpoint = len(symbols) // 2
        left = _fetch_market_prices_batch_allow_partial(
            symbols[:midpoint],
            config=config,
            downloader=downloader,
        )
        right = _fetch_market_prices_batch_allow_partial(
            symbols[midpoint:],
            config=config,
            downloader=downloader,
        )
        frames = [frame for frame in [left, right] if not frame.empty]
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, axis=1)


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


async def fetch_market_prices_batched_async(
    symbols: Sequence[str],
    config: MarketDataConfig,
    batch_size: int = 200,
    downloader: DownloadFn | None = None,
    allow_partial: bool = False,
) -> pd.DataFrame:
    try:
        return await asyncio.to_thread(
            fetch_market_prices_batched,
            symbols,
            config,
            batch_size,
            downloader,
            allow_partial,
        )
    except Exception as exc:
        logger.exception("Async batched market price fetch failed: %s", exc)
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
