from __future__ import annotations

import importlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def test_today_pipeline_rebuilds_candidate_reports_and_dashboard_without_market_refresh() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()
        (root / "configs" / "fundamentals.actual.csv").write_text("symbol\n", encoding="utf-8")

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=False,
            dry_run=True,
        )

        step_names = [step.name for step in output.steps]
        assert step_names == [
            "universe_coverage",
            "company_research",
            "universe_stock_analysis",
            "trend_forecast",
            "market_regime",
            "event_catalysts",
            "event_adjusted_ranking",
            "research_filter",
            "candidate_briefs",
            "investment_checklist",
            "market_watch",
            "conviction_score",
            "profit_focus",
            "investment_memo",
            "valuation_data_quality",
            "capital_plan_review",
            "manual_review_draft",
            "manual_review_proposal",
            "manual_review_apply_plan",
            "decision_gate",
            "pre_buy_decision",
            "entry_signal_watch",
            "market_recovery_watch",
            "sector_rotation_watch",
            "tactical_watchlist",
            "order_sizer",
            "capital_scenarios",
            "investment_tracking",
            "operating_status",
            "dashboard",
        ]
        assert output.summary["executed_count"] == 0
        assert output.summary["external_api_requested"] == "NO"
        assert any("run_universe_coverage.py" in step.command[1] for step in output.steps)
        assert any("run_company_research.py" in step.command[1] for step in output.steps)
        assert any("run_universe_stock_analysis.py" in step.command[1] for step in output.steps)
        assert any("run_trend_forecast.py" in step.command[1] for step in output.steps)
        assert any("run_market_regime.py" in step.command[1] for step in output.steps)
        assert any("run_event_catalysts.py" in step.command[1] for step in output.steps)
        assert any("run_event_adjusted_ranking.py" in step.command[1] for step in output.steps)
        event_adjusted = next(step for step in output.steps if step.name == "event_adjusted_ranking")
        assert "--trend-forecast-csv" in event_adjusted.command
        assert "--market-regime-csv" in event_adjusted.command
        assert any("run_capital_plan_review.py" in step.command[1] for step in output.steps)
        assert any("run_manual_review_draft.py" in step.command[1] for step in output.steps)
        assert any("run_manual_review_proposal.py" in step.command[1] for step in output.steps)
        assert any("run_manual_review_apply_plan.py" in step.command[1] for step in output.steps)
        assert any("--actual-output-csv" in step.command for step in output.steps)
        assert any("--manual-proposal-csv" in step.command for step in output.steps)
        assert any("--capital-plan-dir" in step.command for step in output.steps)
        pre_buy = next(step for step in output.steps if step.name == "pre_buy_decision")
        assert "--trend-forecast-csv" in pre_buy.command
        assert "--market-regime-csv" in pre_buy.command
        entry_signal = next(step for step in output.steps if step.name == "entry_signal_watch")
        assert entry_signal.command[1].endswith("run_entry_signal_watch.py")
        assert "--event-adjusted-ranking-csv" in entry_signal.command
        assert "--pre-buy-decision-csv" in entry_signal.command
        assert "--trend-forecast-csv" in entry_signal.command
        recovery_watch = next(step for step in output.steps if step.name == "market_recovery_watch")
        assert recovery_watch.command[1].endswith("run_market_recovery_watch.py")
        assert "--market-regime-csv" in recovery_watch.command
        assert "--entry-signal-watch-csv" in recovery_watch.command
        sector_rotation = next(step for step in output.steps if step.name == "sector_rotation_watch")
        assert sector_rotation.command[1].endswith("run_sector_rotation_watch.py")
        assert "--market-recovery-watch-csv" in sector_rotation.command
        assert "--trend-forecast-csv" in sector_rotation.command
        tactical_watchlist = next(step for step in output.steps if step.name == "tactical_watchlist")
        assert tactical_watchlist.command[1].endswith("run_tactical_watchlist.py")
        assert "--event-adjusted-ranking-csv" in tactical_watchlist.command
        assert "--entry-signal-watch-csv" in tactical_watchlist.command
        assert "--sector-rotation-watch-csv" in tactical_watchlist.command
        assert any("run_order_sizer.py" in step.command[1] for step in output.steps)
        assert any("run_capital_scenarios.py" in step.command[1] for step in output.steps)
        assert any("run_investment_tracking.py" in step.command[1] for step in output.steps)
        assert any("run_operating_status.py" in step.command[1] for step in output.steps)
        assert any("run_valuation_data_quality.py" in step.command[1] for step in output.steps)
        assert any("--fundamentals-csv" in step.command for step in output.steps)
        assert any("--include-building-focus" in step.command for step in output.steps)
        assert output.steps[-1].command[1].endswith("run_dashboard.py")


def test_today_pipeline_market_refresh_adds_external_price_update_first() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=True,
            dry_run=True,
        )

        assert output.steps[0].name == "market_data_refresh"
        assert output.steps[0].external_api is True
        assert output.steps[0].command[1].endswith("update_market_data.py")
        assert "--allow-partial" in output.steps[0].command
        assert output.summary["external_api_requested"] == "YES"


def test_today_pipeline_can_add_symbol_before_refresh_and_render_intake_before_dashboard() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()
        fundamentals = root / "configs" / "fundamentals.actual.csv"
        fundamentals.write_text("symbol\n", encoding="utf-8")

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=True,
            dry_run=True,
            add_code="006800",
            add_company_name="Mirae Asset Securities",
            add_market="KOSPI",
            add_sector="Securities",
        )

        step_names = [step.name for step in output.steps]
        assert step_names[0] == "symbol_universe_add"
        assert step_names[1] == "market_data_refresh"
        assert step_names[-2:] == ["symbol_analysis_intake", "dashboard"]
        assert output.summary["symbol_intake_requested"] == "YES"
        assert output.summary["external_api_requested"] == "YES"

        add_step = output.steps[0]
        assert add_step.external_api is False
        assert add_step.command[1].endswith("add_research_symbol.py")
        assert "--code" in add_step.command
        assert "006800" in add_step.command
        assert "--company-name" in add_step.command
        assert "Mirae Asset Securities" in add_step.command

        intake_step = output.steps[-2]
        assert intake_step.external_api is False
        assert intake_step.command[1].endswith("run_symbol_analysis.py")
        assert "--code" in intake_step.command
        assert "006800" in intake_step.command
        assert "--fundamentals-csv" in intake_step.command
        assert str(fundamentals) in intake_step.command
        assert "--output-dir" in intake_step.command


def test_today_pipeline_can_add_easy_stock_input_before_refresh() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=True,
            dry_run=True,
            add_stock="삼성전자",
        )

        step_names = [step.name for step in output.steps]
        assert step_names[0] == "symbol_universe_add"
        assert step_names[1] == "market_data_refresh"
        assert step_names[-2:] == ["symbol_analysis_intake", "dashboard"]
        assert output.summary["symbol_intake_requested"] == "YES"

        add_step = output.steps[0]
        assert "--code" in add_step.command
        assert "005930" in add_step.command
        assert "--company-name" in add_step.command
        assert "삼성전자" in add_step.command
        assert "--sector" in add_step.command
        assert "반도체" in add_step.command

        intake_step = output.steps[-2]
        assert "--code" in intake_step.command
        assert "005930" in intake_step.command
        assert "삼성전자" in intake_step.command


def test_today_pipeline_can_add_symbols_csv_before_refresh_and_render_batch_intake() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()
        symbols_csv = root / "symbols.csv"
        symbols_csv.write_text("code,company_name,market,sector\n006800,Mirae Asset Securities,KOSPI,Securities\n", encoding="utf-8")

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=True,
            dry_run=True,
            add_symbols_csv=symbols_csv,
        )

        step_names = [step.name for step in output.steps]
        assert step_names[0] == "symbol_universe_add_batch"
        assert step_names[1] == "market_data_refresh"
        assert step_names[-2:] == ["symbol_batch_analysis_intake", "dashboard"]
        assert output.summary["symbol_intake_requested"] == "YES"
        assert output.summary["external_api_requested"] == "YES"

        add_step = output.steps[0]
        assert add_step.external_api is False
        assert add_step.command[1].endswith("add_research_symbols.py")
        assert "--symbols-csv" in add_step.command
        assert str(symbols_csv) in add_step.command

        intake_step = output.steps[-2]
        assert intake_step.external_api is False
        assert intake_step.command[1].endswith("run_symbol_batch_analysis.py")
        assert "--symbols-csv" in intake_step.command
        assert str(symbols_csv) in intake_step.command


def test_today_pipeline_reapplies_valuation_after_market_refresh_when_shares_exist() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "data").mkdir()
        (root / "reports").mkdir()
        fundamentals = root / "configs" / "fundamentals.actual.csv"
        shares = root / "configs" / "shares_outstanding.actual.csv"
        fundamentals.write_text("symbol\n", encoding="utf-8")
        shares.write_text("symbol\n", encoding="utf-8")

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=True,
            dry_run=True,
        )

        step_names = [step.name for step in output.steps]
        assert step_names[:4] == [
            "market_data_refresh",
            "valuation_metrics_refresh",
            "universe_coverage",
            "company_research",
        ]
        assert step_names[4:9] == [
            "universe_stock_analysis",
            "trend_forecast",
            "market_regime",
            "event_catalysts",
            "event_adjusted_ranking",
        ]
        valuation_step = output.steps[1]
        assert valuation_step.external_api is False
        assert valuation_step.command[1].endswith("apply_valuation_metrics.py")
        assert valuation_step.command[-2:] == ["--output-csv", str(fundamentals)]
        assert str(root / "data" / "prices.csv") in valuation_step.command
        assert str(shares) in valuation_step.command


def test_today_pipeline_adds_local_filing_risk_summary_when_scan_exists() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        filing_dir = root / "reports" / "filing_review"
        filing_dir.mkdir(parents=True)
        scan_csv = filing_dir / "opendart_text_risk_scan_028260.csv"
        scan_csv.write_text("symbol,review_check,scan_status,keyword,report_nm,rcept_no,rcept_dt,snippet\n", encoding="utf-8")

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=False,
            dry_run=True,
        )

        step_names = [step.name for step in output.steps]
        assert "filing_risk_summary_028260" in step_names
        assert step_names.index("filing_risk_summary_028260") < step_names.index("dashboard")
        assert step_names.index("filing_risk_summary_028260") < step_names.index("manual_review_draft")
        assert step_names.index("pre_buy_decision") < step_names.index("entry_signal_watch") < step_names.index("market_recovery_watch") < step_names.index("sector_rotation_watch") < step_names.index("tactical_watchlist") < step_names.index("order_sizer") < step_names.index("capital_scenarios") < step_names.index("investment_tracking") < step_names.index("operating_status") < step_names.index("dashboard")
        risk_step = output.steps[step_names.index("filing_risk_summary_028260")]
        assert risk_step.external_api is False
        assert risk_step.command[1].endswith("run_filing_risk_summary.py")
        assert str(scan_csv) in risk_step.command


def test_today_pipeline_passes_total_capital_to_capital_plan_and_order_sizer() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=False,
            total_capital_krw=3_000_000,
            dry_run=True,
        )

        capital_plan = next(step for step in output.steps if step.name == "capital_plan_review")
        order_sizer = next(step for step in output.steps if step.name == "order_sizer")
        assert "--total-capital-krw" in capital_plan.command
        assert "3000000" in capital_plan.command
        assert "--total-capital-krw" in order_sizer.command
        assert "3000000" in order_sizer.command


def test_today_pipeline_uses_existing_capital_actual_by_default() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()
        capital = root / "configs" / "capital.actual.csv"
        capital.write_text("total_capital_krw,notes\n3000000,review capital\n", encoding="utf-8")

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=False,
            dry_run=True,
        )

        capital_plan = next(step for step in output.steps if step.name == "capital_plan_review")
        order_sizer = next(step for step in output.steps if step.name == "order_sizer")
        assert "--total-capital-krw" in capital_plan.command
        assert "3000000" in capital_plan.command
        assert "--total-capital-krw" in order_sizer.command
        assert "3000000" in order_sizer.command


def test_today_pipeline_uses_existing_actual_manual_review_by_default() -> None:
    module = importlib.import_module("quantum_trainer.today_pipeline")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()
        actual = root / "configs" / "manual_review.actual.csv"
        actual.write_text("symbol,filing_review,earnings_review,business_driver_review,valuation_review,loss_rule_review,capital_plan_review,review_notes\n", encoding="utf-8")

        output = module.run_today_pipeline(
            project_root=root,
            refresh_market_data=False,
            dry_run=True,
        )

        decision_gate = next(step for step in output.steps if step.name == "decision_gate")
        assert "--manual-review-csv" in decision_gate.command
        assert str(actual) in decision_gate.command
