from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.config import load_runtime_config
from quantum_trainer.market_data import (
    MarketDataConfig,
    fetch_market_prices,
    resolve_market_data_symbols,
    write_price_cache,
)


def test_fetch_market_prices_normalizes_yfinance_multiindex_close_data() -> None:
    dates = pd.date_range("2026-01-01", periods=3, freq="B")
    raw = pd.DataFrame(
        {
            ("Close", "000660.KS"): [100.0, 101.0, 102.0],
            ("Close", "005380.KS"): [200.0, 201.0, 202.0],
        },
        index=dates,
    )
    raw.columns = pd.MultiIndex.from_tuples(raw.columns)

    def fake_downloader(*args: object, **kwargs: object) -> pd.DataFrame:
        return raw

    prices = fetch_market_prices(
        symbols=["000660.KS", "005380.KS"],
        config=MarketDataConfig(start="2026-01-01"),
        downloader=fake_downloader,
    )

    assert list(prices.columns) == ["000660.KS", "005380.KS"]
    assert prices.iloc[-1]["000660.KS"] == 102.0
    assert prices.index.name == "date"


def test_write_price_cache_outputs_date_column_csv() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        output_path = Path(tmp_dir) / "prices.csv"
        prices = pd.DataFrame(
            {"000660.KS": [100.0, 101.0]},
            index=pd.date_range("2026-01-01", periods=2, freq="B", name="date"),
        )

        write_price_cache(prices, output_path)

        text = output_path.read_text(encoding="utf-8-sig")
        assert text.splitlines()[0] == "date,000660.KS"


def test_runtime_config_loads_market_data_section() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        config_path = Path(tmp_dir) / "portfolio.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "data:",
                    "  prices_csv: prices.csv",
                    "reports:",
                    "  output_dir: reports",
                    "strategy:",
                    "  trend_window: 20",
                    "  cost_bps: 5.0",
                    "  periods_per_year: 252",
                    "market_data:",
                    "  provider: yfinance",
                    "  start: '2024-01-01'",
                    "  end:",
                    "  auto_adjust: true",
                    "  progress: false",
                    "portfolio:",
                    "  000660.KS: 0.6",
                    "  005380.KS: 0.4",
                ]
            ),
            encoding="utf-8",
        )

        runtime_config = load_runtime_config(config_path)

        assert runtime_config.market_data.provider == "yfinance"
        assert runtime_config.market_data.start == "2024-01-01"
        assert runtime_config.market_data.end is None
        assert runtime_config.market_data.auto_adjust is True


def test_resolve_market_data_symbols_prefers_research_universe_when_provided() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "research_universe.actual.csv"
        universe_csv.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector,market,code",
                    "005930.KS,Samsung Electronics,Semiconductors,KOSPI,005930",
                    "091990.KQ,Celltrion Healthcare,Biotech,KOSDAQ,091990",
                ]
            ),
            encoding="utf-8",
        )

        symbols = resolve_market_data_symbols(
            portfolio_symbols=["000660.KS", "005380.KS"],
            universe_csv=universe_csv,
        )

        assert symbols == ["005930.KS", "091990.KQ"]


def test_resolve_market_data_symbols_uses_portfolio_when_universe_is_missing() -> None:
    symbols = resolve_market_data_symbols(
        portfolio_symbols=["000660.KS", "005380.KS"],
        universe_csv=None,
    )

    assert symbols == ["000660.KS", "005380.KS"]
