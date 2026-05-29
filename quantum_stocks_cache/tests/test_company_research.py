from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.company_research import (
    _extension_penalty,
    _extension_risk,
    _research_view,
    _why_summary,
    run_company_research,
)


def _prices(rows: int = 150) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="B", name="date")
    return pd.DataFrame(
        {
            "000660.KS": [100.0 + i * 0.9 + ((i % 5) * 0.2) for i in range(rows)],
            "005380.KS": [220.0 - i * 0.2 + ((i % 7) * 0.1) for i in range(rows)],
        },
        index=dates,
    )


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
                "  000660.KS: 0.60",
                "  005380.KS: 0.40",
            ]
        ),
        encoding="utf-8",
    )


def test_company_research_writes_ranked_report_with_data_reasons() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_path = root / "prices.csv"
        config_path = root / "portfolio.yaml"
        universe_path = root / "research_universe.csv"
        _prices().to_csv(prices_path, encoding="utf-8-sig", index_label="date")
        _write_config(config_path, prices_path)
        universe_path.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector",
                    "000660.KS,SK hynix,Semiconductors",
                    "005380.KS,Hyundai Motor,Autos",
                ]
            ),
            encoding="utf-8",
        )

        output = run_company_research(
            config_path=config_path,
            universe_csv=universe_path,
            min_samples=20,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.report["research_score"].is_monotonic_decreasing
        assert {
            "symbol",
            "company_name",
            "sector",
            "research_score",
            "decision",
            "why_summary",
            "latest_price_date",
        }.issubset(output.report.columns)
        assert output.report.iloc[0]["symbol"] == "000660.KS"
        assert "POSITIVE_20D_MOMENTUM" in output.report.iloc[0]["why_summary"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Company Research Candidates" in markdown
        assert "not an instruction to trade" in markdown
        assert "## 1. 000660.KS SK hynix" in markdown
        assert "### 투자 논리" in markdown
        assert "### 주요 리스크" in markdown
        assert "### 확인 질문" in markdown
        assert "20일 모멘텀이 양호합니다" in markdown


def test_company_research_uses_symbols_when_universe_csv_is_not_provided() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_path = root / "prices.csv"
        config_path = root / "portfolio.yaml"
        _prices().to_csv(prices_path, encoding="utf-8-sig", index_label="date")
        _write_config(config_path, prices_path)

        output = run_company_research(config_path=config_path, min_samples=20)

        assert set(output.report["symbol"]) == {"000660.KS", "005380.KS"}
        assert set(output.report["company_name"]) == {"000660.KS", "005380.KS"}


def test_company_research_combines_fundamentals_when_csv_is_provided() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_path = root / "prices.csv"
        config_path = root / "portfolio.yaml"
        fundamentals_path = root / "fundamentals.csv"
        _prices().to_csv(prices_path, encoding="utf-8-sig", index_label="date")
        _write_config(config_path, prices_path)
        fundamentals_path.write_text(
            "\n".join(
                [
                    "symbol,revenue_growth,operating_margin,roe,per,pbr,debt_ratio,net_income,equity,shares_outstanding,latest_price,market_cap",
                    "000660.KS,0.12,0.20,0.16,12.0,1.1,0.35,1000,5000,100,110,11000",
                    "005380.KS,-0.02,0.04,0.03,35.0,2.8,1.60,1000,5000,100,210,21000",
                ]
            ),
            encoding="utf-8",
        )

        output = run_company_research(
            config_path=config_path,
            fundamentals_csv=fundamentals_path,
            min_samples=20,
        )

        assert {
            "fundamental_score",
            "fundamental_view",
            "fundamental_reasons",
        }.issubset(output.report.columns)
        assert "latest_price" in output.report.columns
        assert "latest_price_x" not in output.report.columns
        assert "latest_price_y" not in output.report.columns
        top = output.report.iloc[0]
        assert top["symbol"] == "000660.KS"
        assert top["fundamental_view"] == "FUNDAMENTAL_STRONG"
        assert "FUNDAMENTAL_STRONG" in top["why_summary"]


def test_company_research_marks_overextended_buy_ready_as_pullback_wait() -> None:
    row = pd.Series(
        {
            "decision": "BUY_READY",
            "return_20d": 0.397,
            "ma20_gap": 0.091,
            "drawdown_20d": -0.04,
            "expected_20d_return": 0.17,
            "upside_probability": 0.99,
            "fundamental_view": "FUNDAMENTAL_NEUTRAL",
        }
    )
    row["extension_risk"] = _extension_risk(row)
    row["extension_penalty"] = _extension_penalty(row)

    assert row["extension_risk"] == "OVEREXTENDED_WAIT"
    assert row["extension_penalty"] > 0
    assert _research_view(row) == "WAIT_PULLBACK"
    assert "OVEREXTENDED_20D_RETURN" in _why_summary(row)
