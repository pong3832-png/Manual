from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.universe_coverage import run_universe_coverage


def test_universe_coverage_passes_when_universe_is_broad_and_cached_prices_exist() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "universe.csv"
        prices_csv = root / "prices.csv"
        rows = [
            ("005930.KS", "Samsung Electronics", "Semiconductors", "KOSPI", "005930"),
            ("005380.KS", "Hyundai Motor", "Autos", "KOSPI", "005380"),
            ("000660.KS", "SK hynix", "Semiconductors", "KOSPI", "000660"),
            ("028260.KS", "Samsung C&T", "Holding", "KOSPI", "028260"),
            ("003550.KS", "LG Corp", "Holding", "KOSPI", "003550"),
            ("012330.KS", "Hyundai Mobis", "Autos", "KOSPI", "012330"),
            ("105560.KS", "KB Financial", "Financials", "KOSPI", "105560"),
            ("055550.KS", "Shinhan Financial", "Financials", "KOSPI", "055550"),
            ("066570.KS", "LG Electronics", "Electronics", "KOSPI", "066570"),
            ("017670.KS", "SK Telecom", "Telecom", "KOSPI", "017670"),
        ]
        pd.DataFrame(rows, columns=["symbol", "company_name", "sector", "market", "code"]).to_csv(
            universe_csv, index=False
        )
        price_dates = pd.date_range("2026-01-01", periods=30, freq="B", name="date")
        prices = pd.DataFrame({symbol: [100.0 + i for i in range(30)] for symbol, *_ in rows}, index=price_dates)
        prices.to_csv(prices_csv, encoding="utf-8-sig", index_label="date")

        output = run_universe_coverage(
            universe_csv=universe_csv,
            prices_csv=prices_csv,
            output_dir=root / "reports",
            min_count=10,
            max_count=50,
        )

        row = output.report.iloc[0]
        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert row["universe_status"] == "PASS_CANDIDATE"
        assert row["universe_count"] == 10
        assert row["sector_count"] >= 6
        assert row["required_missing_count"] == 0
        assert row["price_coverage_status"] == "PRICE_COVERAGE_READY"
        assert row["price_missing_count"] == 0
        assert row["order_status"] == "NO_ORDER"
        assert row["external_api_requested"] == "NO"


def test_universe_coverage_flags_small_universe_missing_required_symbols_and_prices() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "universe.csv"
        prices_csv = root / "prices.csv"
        pd.DataFrame(
            [
                ("028260.KS", "Samsung C&T", "Holding", "KOSPI", "028260"),
                ("003550.KS", "LG Corp", "Holding", "KOSPI", "003550"),
            ],
            columns=["symbol", "company_name", "sector", "market", "code"],
        ).to_csv(universe_csv, index=False)
        pd.DataFrame(
            {"date": ["2026-01-01", "2026-01-02"], "028260.KS": [100.0, 101.0]}
        ).to_csv(prices_csv, index=False)

        output = run_universe_coverage(
            universe_csv=universe_csv,
            prices_csv=prices_csv,
            output_dir=root / "reports",
            min_count=10,
            max_count=50,
        )

        row = output.report.iloc[0]
        assert row["universe_status"] == "EXPAND_UNIVERSE"
        assert row["count_status"] == "TOO_SMALL"
        assert row["required_missing_count"] >= 4
        assert "005930.KS" in row["required_missing_symbols"]
        assert row["price_coverage_status"] == "PRICE_DATA_REQUIRED"
        assert row["price_missing_count"] == 1
        assert row["order_status"] == "NO_ORDER"
