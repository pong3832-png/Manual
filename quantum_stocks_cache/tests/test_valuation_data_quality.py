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


def test_valuation_data_quality_uses_memo_fallback_when_research_metrics_are_blank() -> None:
    module = importlib.import_module("quantum_trainer.valuation_data_quality")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        company_research_csv = root / "company_research.csv"
        investment_memo_csv = root / "investment_memo.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "per": "",
                    "pbr": "",
                    "roe": "",
                    "debt_ratio": "",
                    "market_cap": "",
                    "latest_price": 90000,
                }
            ]
        ).to_csv(company_research_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "evidence": "PER=40.08; PBR=4.75; ROE=19.69%; total_liabilities_to_equity=214.5%; market_cap=1.81조원",
                }
            ]
        ).to_csv(investment_memo_csv, index=False)

        output = module.run_valuation_data_quality(
            company_research_csv=company_research_csv,
            investment_memo_csv=investment_memo_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["order_status"] == "NO_ORDER"

        row = output.report.iloc[0]
        assert row["symbol"] == "183300.KQ"
        assert row["valuation_source"] == "INVESTMENT_MEMO_FALLBACK"
        assert row["data_gap"] == "RESEARCH_VALUATION_BLANK"
        assert row["per"] == 40.08
        assert row["pbr"] == 4.75
        assert row["roe"] == 0.1969
        assert row["liabilities_to_equity"] == 2.145
        assert row["valuation_status"] == "PREMIUM_REVIEW_REQUIRED"
        assert row["valuation_review_candidate"] == "UNKNOWN"
        assert row["order_status"] == "NO_ORDER"
        assert row["external_api_requested"] == "NO"
        assert "OpenDART/price refresh approval required before overwriting local valuation" in row["next_step"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Valuation Data Quality" in markdown
        assert "INVESTMENT_MEMO_FALLBACK" in markdown
        assert "PREMIUM_REVIEW_REQUIRED" in markdown
        assert "NO_ORDER" in markdown


def test_valuation_data_quality_reports_missing_values_without_guessing() -> None:
    module = importlib.import_module("quantum_trainer.valuation_data_quality")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        company_research_csv = root / "company_research.csv"
        investment_memo_csv = root / "investment_memo.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "331920.KQ",
                    "company_name": "셀레믹스",
                    "per": "",
                    "pbr": "",
                    "roe": "",
                    "debt_ratio": "",
                    "market_cap": "",
                    "latest_price": 17090,
                }
            ]
        ).to_csv(company_research_csv, index=False)
        pd.DataFrame([{"symbol": "331920.KQ", "company_name": "셀레믹스", "evidence": ""}]).to_csv(
            investment_memo_csv, index=False
        )

        output = module.run_valuation_data_quality(
            company_research_csv=company_research_csv,
            investment_memo_csv=investment_memo_csv,
            output_dir=output_dir,
        )

        row = output.report.iloc[0]
        assert row["valuation_source"] == "MISSING"
        assert row["data_gap"] == "VALUATION_DATA_REQUIRED"
        assert row["per"] == 0.0
        assert row["pbr"] == 0.0
        assert row["valuation_status"] == "VALUATION_DATA_REQUIRED"
        assert row["valuation_review_candidate"] == "UNKNOWN"
        assert row["order_status"] == "NO_ORDER"
        assert row["external_api_requested"] == "NO"
