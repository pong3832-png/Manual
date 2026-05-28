from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.market_watch import run_market_watch


def _company_research_rows() -> list[dict[str, object]]:
    return [
        {
            "symbol": "028260.KS",
            "company_name": "Samsung C&T",
            "sector": "Holding",
            "research_score": 88.5,
            "research_view": "RESEARCH_CANDIDATE",
            "decision": "BUY_READY",
            "fundamental_view": "FUNDAMENTAL_NEUTRAL",
            "why_summary": "ALPHA_BUY_READY,POSITIVE_20D_MOMENTUM,ABOVE_SMA20",
            "expected_20d_return": 0.15,
            "upside_probability": 0.78,
            "return_20d": 0.32,
            "ma20_gap": 0.08,
            "drawdown_20d": -0.04,
        },
        {
            "symbol": "005930.KS",
            "company_name": "Samsung Electronics",
            "sector": "Semiconductors",
            "research_score": 87.5,
            "research_view": "RESEARCH_CANDIDATE",
            "decision": "BUY_READY",
            "fundamental_view": "FUNDAMENTAL_NEUTRAL",
            "why_summary": "ALPHA_BUY_READY,POSITIVE_EXPECTED_RETURN",
            "expected_20d_return": 0.19,
            "upside_probability": 0.86,
            "return_20d": 0.45,
            "ma20_gap": 0.18,
            "drawdown_20d": 0.0,
        },
        {
            "symbol": "000660.KS",
            "company_name": "SK hynix",
            "sector": "Semiconductors",
            "research_score": 56.5,
            "research_view": "AVOID_FOR_NOW",
            "decision": "AVOID",
            "fundamental_view": "FUNDAMENTAL_WEAK",
            "why_summary": "ALPHA_AVOID",
            "expected_20d_return": -0.02,
            "upside_probability": 0.40,
            "return_20d": 0.12,
            "ma20_gap": 0.04,
            "drawdown_20d": -0.10,
        },
        {
            "symbol": "012330.KS",
            "company_name": "Hyundai Mobis",
            "sector": "Autos",
            "research_score": 86.9,
            "research_view": "WATCHLIST",
            "decision": "BUY_READY",
            "fundamental_view": "FUNDAMENTAL_WEAK",
            "why_summary": "ALPHA_BUY_READY,FUNDAMENTAL_WEAK",
            "expected_20d_return": 0.14,
            "upside_probability": 0.73,
            "return_20d": 0.63,
            "ma20_gap": 0.27,
            "drawdown_20d": 0.0,
        },
    ]


def test_market_watch_detects_upgrades_downgrades_and_focus_list() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        company_research_csv = root / "company_research.csv"
        previous_watch_csv = root / "previous_market_watch.csv"
        output_dir = root / "reports"

        pd.DataFrame(_company_research_rows()).to_csv(company_research_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "research_score": 60.0,
                    "research_view": "WATCHLIST",
                    "decision": "WAIT",
                    "watch_status": "WATCH_FOR_CONFIRMATION",
                },
                {
                    "symbol": "005930.KS",
                    "research_score": 85.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "watch_status": "TODAY_FOCUS",
                },
                {
                    "symbol": "000660.KS",
                    "research_score": 82.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "watch_status": "TODAY_FOCUS",
                },
            ]
        ).to_csv(previous_watch_csv, index=False)

        output = run_market_watch(
            company_research_csv=company_research_csv,
            output_dir=output_dir,
            previous_watch_csv=previous_watch_csv,
            top_n=4,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["focus_count"] == 2

        by_symbol = output.report.set_index("symbol")
        assert by_symbol.loc["028260.KS", "watch_event"] == "UPGRADED_TO_RESEARCH_CANDIDATE"
        assert by_symbol.loc["028260.KS", "watch_status"] == "TODAY_FOCUS"
        assert by_symbol.loc["028260.KS", "score_delta"] == 28.5
        assert by_symbol.loc["005930.KS", "watch_event"] == "STABLE_PRIORITY"
        assert by_symbol.loc["000660.KS", "watch_event"] == "DOWNGRADED_TO_AVOID"
        assert by_symbol.loc["012330.KS", "watch_status"] == "WATCH_FOR_CONFIRMATION"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Market Watch" in markdown
        assert "투자금 없이 동향을 감시하는 리포트" in markdown
        assert "UPGRADED_TO_RESEARCH_CANDIDATE" in markdown
        assert "DOWNGRADED_TO_AVOID" in markdown


def test_market_watch_appends_snapshot_history_without_overwriting() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        company_research_csv = root / "company_research.csv"
        output_dir = root / "reports"
        pd.DataFrame(_company_research_rows()).to_csv(company_research_csv, index=False)

        first = run_market_watch(
            company_research_csv=company_research_csv,
            output_dir=output_dir,
            top_n=2,
            as_of="2026-05-27",
        )
        second = run_market_watch(
            company_research_csv=company_research_csv,
            output_dir=output_dir,
            top_n=2,
            as_of="2026-05-28",
        )

        assert first.history_path == second.history_path
        assert second.history_path.exists()
        history = pd.read_csv(second.history_path)
        assert len(history) == 4
        assert history["as_of"].tolist() == [
            "2026-05-27",
            "2026-05-27",
            "2026-05-28",
            "2026-05-28",
        ]
        assert history["symbol"].tolist() == [
            "028260.KS",
            "005930.KS",
            "028260.KS",
            "005930.KS",
        ]


def test_market_watch_scores_persistent_focus_from_history() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        company_research_csv = root / "company_research.csv"
        output_dir = root / "reports"
        history_csv = output_dir / "market_watch" / "market_watch_history.csv"
        history_csv.parent.mkdir(parents=True)
        pd.DataFrame(
            _company_research_rows()
            + [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "sector": "Holding",
                    "research_score": 74.5,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "why_summary": "ALPHA_BUY_READY,POSITIVE_EXPECTED_RETURN",
                    "expected_20d_return": 0.05,
                    "upside_probability": 0.62,
                    "return_20d": 0.23,
                    "ma20_gap": 0.08,
                    "drawdown_20d": -0.05,
                },
            ]
        ).to_csv(company_research_csv, index=False)
        pd.DataFrame(
            [
                {
                    "as_of": "2026-05-25",
                    "symbol": "028260.KS",
                    "watch_status": "TODAY_FOCUS",
                    "research_score": 80.0,
                },
                {
                    "as_of": "2026-05-26",
                    "symbol": "028260.KS",
                    "watch_status": "TODAY_FOCUS",
                    "research_score": 84.0,
                },
                {
                    "as_of": "2026-05-25",
                    "symbol": "005930.KS",
                    "watch_status": "TODAY_FOCUS",
                    "research_score": 82.0,
                },
                {
                    "as_of": "2026-05-26",
                    "symbol": "005930.KS",
                    "watch_status": "WATCH_FOR_CONFIRMATION",
                    "research_score": 83.0,
                },
                {
                    "as_of": "2026-05-26",
                    "symbol": "003550.KS",
                    "watch_status": "TODAY_FOCUS",
                    "research_score": 70.0,
                },
            ]
        ).to_csv(history_csv, index=False)

        output = run_market_watch(
            company_research_csv=company_research_csv,
            output_dir=output_dir,
            top_n=5,
            as_of="2026-05-27",
        )

        by_symbol = output.report.set_index("symbol")
        assert output.summary["persistent_focus_count"] == 1
        assert by_symbol.loc["028260.KS", "focus_persistence_count"] == 3
        assert by_symbol.loc["028260.KS", "persistence_label"] == "PERSISTENT_FOCUS"
        assert by_symbol.loc["005930.KS", "focus_persistence_count"] == 1
        assert by_symbol.loc["005930.KS", "persistence_label"] == "NEW_FOCUS"
        assert by_symbol.loc["003550.KS", "focus_persistence_count"] == 2
        assert by_symbol.loc["003550.KS", "persistence_label"] == "BUILDING_FOCUS"

        history = pd.read_csv(output.history_path)
        assert "focus_persistence_count" in history.columns
        latest_028260 = history.loc[
            (history["as_of"] == "2026-05-27") & (history["symbol"] == "028260.KS")
        ].iloc[0]
        assert latest_028260["focus_persistence_count"] == 3
