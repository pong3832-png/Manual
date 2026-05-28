from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.symbol_analysis import run_symbol_analysis, run_symbol_batch_analysis


def _prices(rows: int = 80, include_target: bool = True) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="B", name="date")
    data = {
        "005930.KS": [70000.0 + i * 30.0 for i in range(rows)],
    }
    if include_target:
        data["006800.KS"] = [7500.0 + i * 12.0 + ((i % 4) * 2.0) for i in range(rows)]
    return pd.DataFrame(data, index=dates)


def _write_config(path: Path, prices_path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "data:",
                f"  prices_csv: {prices_path.name}",
                "reports:",
                "  output_dir: reports",
                "strategy:",
                "  trend_window: 20",
                "  cost_bps: 5.0",
                "  periods_per_year: 252",
                "portfolio:",
                "  005930.KS: 1.0",
            ]
        ),
        encoding="utf-8",
    )


def test_symbol_analysis_adds_company_and_runs_local_analysis_when_price_cache_exists() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_path = root / "prices.csv"
        config_path = root / "portfolio.yaml"
        universe_path = root / "research_universe.actual.csv"
        _prices().to_csv(prices_path, encoding="utf-8-sig", index_label="date")
        _write_config(config_path, prices_path)
        universe_path.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector,market,code",
                    "005930.KS,Samsung Electronics,Semiconductors,KOSPI,005930",
                ]
            ),
            encoding="utf-8",
        )

        output = run_symbol_analysis(
            config_path=config_path,
            universe_csv=universe_path,
            output_dir=root / "reports",
            code="006800",
            company_name="Mirae Asset Securities",
            market="KOSPI",
            sector="Securities",
            min_samples=20,
        )

        assert output.status == "ANALYSIS_READY"
        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["external_api_requested"] == "NO"
        written_universe = pd.read_csv(universe_path, dtype=str)
        assert written_universe["symbol"].tolist() == ["005930.KS", "006800.KS"]
        row = output.report.iloc[0]
        assert row["symbol"] == "006800.KS"
        assert row["company_name"] == "Mirae Asset Securities"
        assert row["analysis_status"] == "ANALYSIS_READY"
        assert row["price_data_status"] == "READY"
        assert row["order_status"] == "NO_ORDER"
        assert row["external_api_requested"] == "NO"
        assert row["broker_order_requested"] == "NO"
        assert Path(str(row["company_research_csv"])).exists()


def test_symbol_analysis_reports_data_required_when_price_cache_is_missing() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_path = root / "prices.csv"
        config_path = root / "portfolio.yaml"
        universe_path = root / "research_universe.actual.csv"
        _prices(include_target=False).to_csv(prices_path, encoding="utf-8-sig", index_label="date")
        _write_config(config_path, prices_path)
        universe_path.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector,market,code",
                    "005930.KS,Samsung Electronics,Semiconductors,KOSPI,005930",
                ]
            ),
            encoding="utf-8",
        )

        output = run_symbol_analysis(
            config_path=config_path,
            universe_csv=universe_path,
            output_dir=root / "reports",
            code="006800",
            company_name="Mirae Asset Securities",
            market="KOSPI",
            sector="Securities",
            min_samples=20,
        )

        row = output.report.iloc[0]
        assert output.status == "DATA_REQUIRED"
        assert row["analysis_status"] == "DATA_REQUIRED"
        assert row["price_data_status"] == "MISSING"
        assert "missing cached price history" in row["blocking_reason"]
        assert row["local_pipeline_ready"] == "NO"
        assert row["order_status"] == "NO_ORDER"
        assert row["external_api_requested"] == "NO"


def test_symbol_batch_analysis_adds_multiple_companies_and_marks_missing_price_data() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_path = root / "prices.csv"
        config_path = root / "portfolio.yaml"
        universe_path = root / "research_universe.actual.csv"
        batch_path = root / "symbols.csv"
        _prices(include_target=True).to_csv(prices_path, encoding="utf-8-sig", index_label="date")
        _write_config(config_path, prices_path)
        universe_path.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector,market,code",
                    "005930.KS,Samsung Electronics,Semiconductors,KOSPI,005930",
                ]
            ),
            encoding="utf-8",
        )
        batch_path.write_text(
            "\n".join(
                [
                    "code,company_name,market,sector",
                    "006800,Mirae Asset Securities,KOSPI,Securities",
                    "091990,Celltrion Healthcare,KOSDAQ,Biotech",
                ]
            ),
            encoding="utf-8",
        )

        output = run_symbol_batch_analysis(
            config_path=config_path,
            universe_csv=universe_path,
            symbols_csv=batch_path,
            output_dir=root / "reports",
            min_samples=20,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["analysis_ready_count"] == 1
        assert output.summary["data_required_count"] == 1
        written_universe = pd.read_csv(universe_path, dtype=str)
        assert written_universe["symbol"].tolist() == ["005930.KS", "006800.KS", "091990.KQ"]
        rows = output.report.set_index("symbol")
        assert rows.loc["006800.KS", "analysis_status"] == "ANALYSIS_READY"
        assert rows.loc["006800.KS", "order_status"] == "NO_ORDER"
        assert rows.loc["091990.KQ", "analysis_status"] == "DATA_REQUIRED"
        assert rows.loc["091990.KQ", "price_data_status"] == "MISSING"
        assert "missing cached price history" in rows.loc["091990.KQ", "blocking_reason"]
