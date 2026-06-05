from __future__ import annotations

import importlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def _price_rows() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=90, freq="D")
    base = [100.0 + i * 0.05 for i in range(70)]
    rebound_tail = [
        110,
        108,
        104,
        100,
        95,
        90,
        86,
        82,
        80,
        82,
        84,
        86,
        88,
        90,
        92,
        94,
        95,
        96,
        97,
        98,
    ]
    falling_tail = [
        110,
        108,
        105,
        100,
        96,
        91,
        87,
        83,
        80,
        78,
        77,
        76,
        75,
        74,
        73,
        72,
        71,
        70,
        69,
        68,
    ]
    chased_tail = [
        110,
        100,
        90,
        80,
        72,
        68,
        70,
        76,
        82,
        88,
        94,
        100,
        106,
        112,
        118,
        124,
        128,
        130,
        132,
        134,
    ]
    return pd.DataFrame(
        {
            "date": dates,
            "REBOUND.KQ": base + rebound_tail,
            "FALLING.KQ": base + falling_tail,
            "CHASED.KQ": base + chased_tail,
        }
    )


def test_panic_rebound_signal_classifies_rebound_confirmation_and_chase_risk() -> None:
    module = importlib.import_module("quantum_trainer.panic_rebound_signal")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_csv = root / "prices.csv"
        research_csv = root / "company_research.csv"
        _price_rows().to_csv(prices_csv, index=False)
        pd.DataFrame(
            [
                {"symbol": "REBOUND.KQ", "company_name": "Rebound Co", "sector": "Semiconductors"},
                {"symbol": "FALLING.KQ", "company_name": "Falling Co", "sector": "Materials"},
                {"symbol": "CHASED.KQ", "company_name": "Chased Co", "sector": "Biotech"},
            ]
        ).to_csv(research_csv, index=False)

        output = module.run_panic_rebound_signal(
            prices_csv=prices_csv,
            company_research_csv=research_csv,
            output_dir=root / "reports",
            min_samples=60,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["row_count"] == 3
        assert output.summary["ready_rebound_review_count"] == 1
        assert output.summary["wait_confirmation_count"] == 1
        assert output.summary["chase_risk_count"] == 1
        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["order_status"] == "NO_ORDER"
        assert set(output.report["order_status"]) == {"NO_ORDER"}
        assert set(output.report["broker_order_requested"]) == {"NO"}

        by_symbol = output.report.set_index("symbol")
        assert by_symbol.loc["REBOUND.KQ", "rebound_status"] == "READY_REBOUND_REVIEW"
        assert by_symbol.loc["REBOUND.KQ", "panic_detected"] == "YES"
        assert by_symbol.loc["REBOUND.KQ", "reversal_confirmed"] == "YES"
        assert by_symbol.loc["REBOUND.KQ", "chase_risk"] == "LOW"

        assert by_symbol.loc["FALLING.KQ", "rebound_status"] == "WAIT_CONFIRMATION"
        assert by_symbol.loc["FALLING.KQ", "panic_detected"] == "YES"
        assert by_symbol.loc["FALLING.KQ", "reversal_confirmed"] == "NO"

        assert by_symbol.loc["CHASED.KQ", "rebound_status"] == "CHASE_RISK"
        assert by_symbol.loc["CHASED.KQ", "chase_risk"] == "HIGH"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Panic Rebound Signal" in markdown
        assert "READY_REBOUND_REVIEW" in markdown
        assert "NO_ORDER" in markdown


def test_panic_rebound_signal_marks_short_history_as_insufficient_data() -> None:
    module = importlib.import_module("quantum_trainer.panic_rebound_signal")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_csv = root / "prices.csv"
        research_csv = root / "company_research.csv"
        pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=20, freq="D"),
                "SHORT.KQ": [100 + i for i in range(20)],
            }
        ).to_csv(prices_csv, index=False)
        pd.DataFrame(
            [{"symbol": "SHORT.KQ", "company_name": "Short Co", "sector": "New Listing"}]
        ).to_csv(research_csv, index=False)

        output = module.run_panic_rebound_signal(
            prices_csv=prices_csv,
            company_research_csv=research_csv,
            output_dir=root / "reports",
            min_samples=60,
        )

        row = output.report.iloc[0]
        assert row["sample_count"] == 20
        assert row["rebound_status"] == "INSUFFICIENT_DATA"
        assert row["panic_detected"] == "UNKNOWN"
        assert row["reversal_confirmed"] == "UNKNOWN"
        assert row["order_status"] == "NO_ORDER"
        assert row["external_api_requested"] == "NO"
