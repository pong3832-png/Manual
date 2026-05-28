from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from quantum_trainer.capital_config import load_total_capital_krw
from quantum_trainer.symbol_input import resolve_stock_input


CommandRunner = Callable[[Sequence[str], Path], int]


@dataclass(frozen=True)
class PipelineStep:
    name: str
    command: list[str]
    external_api: bool = False


@dataclass(frozen=True)
class TodayPipelineOutput:
    steps: list[PipelineStep]
    executed_steps: list[str]
    summary: dict[str, str | int]


def run_today_pipeline(
    project_root: Path | str,
    config_path: Path | str | None = None,
    universe_csv: Path | str | None = None,
    fundamentals_csv: Path | str | None = None,
    shares_csv: Path | str | None = None,
    reports_dir: Path | str | None = None,
    manual_review_csv: Path | str | None = None,
    refresh_market_data: bool = False,
    include_building_focus: bool = True,
    add_stock: str | None = None,
    add_code: str | None = None,
    add_symbol: str | None = None,
    add_symbols_csv: Path | str | None = None,
    add_company_name: str = "",
    add_market: str = "KOSPI",
    add_sector: str = "UNKNOWN",
    replace_symbol: bool = False,
    symbol_min_samples: int = 80,
    total_capital_krw: float | None = None,
    dry_run: bool = False,
    runner: CommandRunner | None = None,
) -> TodayPipelineOutput:
    root = Path(project_root).resolve()
    resolved_total_capital = (
        total_capital_krw
        if total_capital_krw is not None
        else load_total_capital_krw(root / "configs" / "capital.actual.csv")
    )
    resolved_stock = (
        resolve_stock_input(
            add_stock,
            universe_csv=Path(universe_csv).resolve() if universe_csv else root / "configs" / "research_universe.actual.csv",
        )
        if add_stock
        else None
    )
    resolved_add_code = resolved_stock.code if resolved_stock else add_code
    resolved_add_symbol = None if resolved_stock else add_symbol
    resolved_add_company_name = resolved_stock.company_name if resolved_stock else add_company_name
    resolved_add_market = resolved_stock.market if resolved_stock else add_market
    resolved_add_sector = resolved_stock.sector if resolved_stock else add_sector
    steps = build_today_pipeline_steps(
        project_root=root,
        config_path=Path(config_path).resolve() if config_path else root / "configs" / "portfolio.yaml",
        universe_csv=Path(universe_csv).resolve() if universe_csv else root / "configs" / "research_universe.actual.csv",
        fundamentals_csv=_resolve_fundamentals(root, fundamentals_csv),
        shares_csv=_resolve_shares(root, shares_csv),
        reports_dir=Path(reports_dir).resolve() if reports_dir else root / "reports",
        manual_review_csv=_resolve_manual_review(root, manual_review_csv),
        refresh_market_data=refresh_market_data,
        include_building_focus=include_building_focus,
        add_code=resolved_add_code,
        add_symbol=resolved_add_symbol,
        add_symbols_csv=Path(add_symbols_csv).resolve() if add_symbols_csv else None,
        add_company_name=resolved_add_company_name,
        add_market=resolved_add_market,
        add_sector=resolved_add_sector,
        replace_symbol=replace_symbol,
        symbol_min_samples=symbol_min_samples,
        total_capital_krw=resolved_total_capital,
    )

    executed: list[str] = []
    if not dry_run:
        command_runner = runner or _subprocess_runner
        for step in steps:
            exit_code = command_runner(step.command, root)
            if exit_code != 0:
                raise RuntimeError(f"Pipeline step failed: {step.name} exit_code={exit_code}")
            executed.append(step.name)

    summary = {
        "step_count": len(steps),
        "executed_count": len(executed),
        "external_api_requested": "YES" if any(step.external_api for step in steps) else "NO",
        "symbol_intake_requested": "YES"
        if _symbol_requested(resolved_add_code, resolved_add_symbol, add_symbols_csv)
        else "NO",
        "dashboard_path": str((Path(reports_dir).resolve() if reports_dir else root / "reports") / "dashboard" / "index.html"),
    }
    return TodayPipelineOutput(steps=steps, executed_steps=executed, summary=summary)


def build_today_pipeline_steps(
    project_root: Path,
    config_path: Path,
    universe_csv: Path,
    fundamentals_csv: Path | None,
    shares_csv: Path | None,
    reports_dir: Path,
    manual_review_csv: Path | None,
    refresh_market_data: bool,
    include_building_focus: bool,
    add_code: str | None = None,
    add_symbol: str | None = None,
    add_symbols_csv: Path | None = None,
    add_company_name: str = "",
    add_market: str = "KOSPI",
    add_sector: str = "UNKNOWN",
    replace_symbol: bool = False,
    symbol_min_samples: int = 80,
    total_capital_krw: float | None = None,
) -> list[PipelineStep]:
    scripts = project_root / "scripts"
    py = sys.executable
    steps: list[PipelineStep] = []

    if add_symbols_csv:
        batch_add_command = [
            py,
            str(scripts / "add_research_symbols.py"),
            "--symbols-csv",
            str(add_symbols_csv),
            "--universe-csv",
            str(universe_csv),
            "--output-csv",
            str(universe_csv),
        ]
        if replace_symbol:
            batch_add_command.append("--replace")
        steps.append(PipelineStep(name="symbol_universe_add_batch", command=batch_add_command))

    if _symbol_requested(add_code, add_symbol):
        add_command = [
            py,
            str(scripts / "add_research_symbol.py"),
            "--universe-csv",
            str(universe_csv),
            "--output-csv",
            str(universe_csv),
            "--company-name",
            add_company_name,
            "--market",
            add_market,
            "--sector",
            add_sector,
        ]
        if add_code:
            add_command.extend(["--code", add_code])
        if add_symbol:
            add_command.extend(["--symbol", add_symbol])
        if replace_symbol:
            add_command.append("--replace")
        steps.append(PipelineStep(name="symbol_universe_add", command=add_command))

    if refresh_market_data:
        steps.append(
            PipelineStep(
                name="market_data_refresh",
                command=[
                    py,
                    str(scripts / "update_market_data.py"),
                    "--config",
                    str(config_path),
                    "--universe-csv",
                    str(universe_csv),
                ],
                external_api=True,
            )
        )

    if refresh_market_data and fundamentals_csv and shares_csv:
        steps.append(
            PipelineStep(
                name="valuation_metrics_refresh",
                command=[
                    py,
                    str(scripts / "apply_valuation_metrics.py"),
                    "--fundamentals-csv",
                    str(fundamentals_csv),
                    "--prices-csv",
                    str(project_root / "data" / "prices.csv"),
                    "--shares-csv",
                    str(shares_csv),
                    "--output-csv",
                    str(fundamentals_csv),
                ],
            )
        )

    company_research_csv = reports_dir / "company_research" / "company_research.csv"
    research_filter_csv = reports_dir / "research_filter" / "research_filter.csv"
    candidate_briefs_csv = reports_dir / "candidate_briefs" / "candidate_briefs.csv"
    investment_checklist_csv = reports_dir / "investment_checklist" / "investment_checklist.csv"
    market_watch_csv = reports_dir / "market_watch" / "market_watch.csv"
    conviction_csv = reports_dir / "conviction" / "conviction_score.csv"
    profit_focus_csv = reports_dir / "profit_focus" / "profit_focus.csv"
    investment_memo_csv = reports_dir / "investment_memo" / "investment_memo.csv"
    manual_review_draft_csv = reports_dir / "decision_gate" / "manual_review_draft.csv"
    manual_review_proposal_csv = reports_dir / "decision_gate" / "manual_review_proposal.csv"
    decision_gate_csv = reports_dir / "decision_gate" / "decision_gate.csv"
    actual_manual_review_csv = project_root / "configs" / "manual_review.actual.csv"

    steps.append(
        PipelineStep(
            name="universe_coverage",
            command=[
                py,
                str(scripts / "run_universe_coverage.py"),
                "--universe-csv",
                str(universe_csv),
                "--prices-csv",
                str(project_root / "data" / "prices.csv"),
                "--output-dir",
                str(reports_dir),
            ],
        )
    )

    company_research = [
        py,
        str(scripts / "run_company_research.py"),
        "--config",
        str(config_path),
        "--universe-csv",
        str(universe_csv),
        "--reports-dir",
        str(reports_dir),
    ]
    if fundamentals_csv:
        company_research.extend(["--fundamentals-csv", str(fundamentals_csv)])
    steps.append(PipelineStep(name="company_research", command=company_research))

    steps.append(
        PipelineStep(
            name="universe_stock_analysis",
            command=[
                py,
                str(scripts / "run_universe_stock_analysis.py"),
                "--company-research-csv",
                str(company_research_csv),
                "--output-dir",
                str(reports_dir),
            ],
        )
    )

    steps.extend(
        [
            PipelineStep(
                name="research_filter",
                command=[
                    py,
                    str(scripts / "run_research_filter.py"),
                    "--company-research-csv",
                    str(company_research_csv),
                    "--output-dir",
                    str(reports_dir),
                    "--top-n",
                    "5",
                ],
            ),
            PipelineStep(
                name="candidate_briefs",
                command=[
                    py,
                    str(scripts / "run_candidate_briefs.py"),
                    "--research-filter-csv",
                    str(research_filter_csv),
                    "--output-dir",
                    str(reports_dir),
                    "--status",
                    "PRIORITY_RESEARCH",
                ],
            ),
            PipelineStep(
                name="investment_checklist",
                command=[
                    py,
                    str(scripts / "run_investment_checklist.py"),
                    "--candidate-briefs-csv",
                    str(candidate_briefs_csv),
                    "--output-dir",
                    str(reports_dir),
                ],
            ),
            PipelineStep(
                name="market_watch",
                command=[
                    py,
                    str(scripts / "run_market_watch.py"),
                    "--company-research-csv",
                    str(company_research_csv),
                    "--output-dir",
                    str(reports_dir),
                    "--top-n",
                    "15",
                ],
            ),
        ]
    )

    conviction_command = [
        py,
        str(scripts / "run_conviction_score.py"),
        "--market-watch-csv",
        str(market_watch_csv),
        "--company-research-csv",
        str(company_research_csv),
        "--output-dir",
        str(reports_dir),
    ]
    if include_building_focus:
        conviction_command.append("--include-building-focus")
    steps.append(PipelineStep(name="conviction_score", command=conviction_command))

    steps.extend(
        [
            PipelineStep(
                name="profit_focus",
                command=[
                    py,
                    str(scripts / "run_profit_focus.py"),
                    "--conviction-csv",
                    str(conviction_csv),
                    "--checklist-csv",
                    str(investment_checklist_csv),
                    "--output-dir",
                    str(reports_dir),
                    "--max-core",
                    "3",
                ],
            ),
            PipelineStep(
                name="investment_memo",
                command=[
                    py,
                    str(scripts / "run_investment_memo.py"),
                    "--profit-focus-csv",
                    str(profit_focus_csv),
                    "--output-dir",
                    str(reports_dir),
                    "--max-memos",
                    "1",
                ],
            ),
        ]
    )

    capital_plan_command = [
        py,
        str(scripts / "run_capital_plan_review.py"),
        "--investment-memo-csv",
        str(investment_memo_csv),
        "--investment-checklist-csv",
        str(investment_checklist_csv),
        "--company-research-csv",
        str(company_research_csv),
        "--output-dir",
        str(reports_dir),
    ]
    if total_capital_krw is not None:
        capital_plan_command.extend(["--total-capital-krw", _amount_arg(total_capital_krw)])
    steps.append(PipelineStep(name="capital_plan_review", command=capital_plan_command))

    for scan_csv in sorted((reports_dir / "filing_review").glob("opendart_text_risk_scan_*.csv")):
        code = scan_csv.stem.removeprefix("opendart_text_risk_scan_")
        steps.append(
            PipelineStep(
                name=f"filing_risk_summary_{code}",
                command=[
                    py,
                    str(scripts / "run_filing_risk_summary.py"),
                    "--scan-csv",
                    str(scan_csv),
                    "--output-dir",
                    str(reports_dir),
                ],
            )
        )

    steps.append(
        PipelineStep(
            name="manual_review_draft",
            command=[
                py,
                str(scripts / "run_manual_review_draft.py"),
                "--investment-memo-csv",
                str(investment_memo_csv),
                "--investment-checklist-csv",
                str(investment_checklist_csv),
                "--company-research-csv",
                str(company_research_csv),
                "--filing-risk-dir",
                str(reports_dir / "filing_review"),
                "--capital-plan-dir",
                str(reports_dir / "decision_gate"),
                "--output-dir",
                str(reports_dir),
            ],
        )
    )

    steps.append(
        PipelineStep(
            name="manual_review_proposal",
            command=[
                py,
                str(scripts / "run_manual_review_proposal.py"),
                "--manual-review-draft-csv",
                str(manual_review_draft_csv),
                "--output-dir",
                str(reports_dir),
            ],
        )
    )

    steps.append(
        PipelineStep(
            name="manual_review_apply_plan",
            command=[
                py,
                str(scripts / "run_manual_review_apply_plan.py"),
                "--manual-proposal-csv",
                str(manual_review_proposal_csv),
                "--actual-output-csv",
                str(actual_manual_review_csv),
                "--output-dir",
                str(reports_dir),
            ],
        )
    )

    decision_gate = [
        py,
        str(scripts / "run_decision_gate.py"),
        "--investment-memo-csv",
        str(investment_memo_csv),
        "--output-dir",
        str(reports_dir),
    ]
    if manual_review_csv:
        decision_gate.extend(["--manual-review-csv", str(manual_review_csv)])
    steps.append(PipelineStep(name="decision_gate", command=decision_gate))

    steps.append(
        PipelineStep(
            name="pre_buy_decision",
            command=[
                py,
                str(scripts / "run_pre_buy_decision.py"),
                "--profit-focus-csv",
                str(profit_focus_csv),
                "--decision-gate-csv",
                str(decision_gate_csv),
                "--company-research-csv",
                str(company_research_csv),
                "--filing-risk-dir",
                str(reports_dir / "filing_review"),
                "--manual-proposal-csv",
                str(manual_review_proposal_csv),
                "--capital-plan-dir",
                str(reports_dir / "decision_gate"),
                "--output-dir",
                str(reports_dir),
            ],
        )
    )

    order_sizer_command = [
        py,
        str(scripts / "run_order_sizer.py"),
        "--candidate-checklist-csv",
        str(investment_checklist_csv),
        "--prices-csv",
        str(project_root / "data" / "prices.csv"),
        "--output-dir",
        str(reports_dir),
    ]
    if total_capital_krw is not None:
        order_sizer_command.extend(["--total-capital-krw", _amount_arg(total_capital_krw)])
    steps.append(PipelineStep(name="order_sizer", command=order_sizer_command))

    steps.append(
        PipelineStep(
            name="capital_scenarios",
            command=[
                py,
                str(scripts / "run_capital_scenarios.py"),
                "--candidate-checklist-csv",
                str(investment_checklist_csv),
                "--prices-csv",
                str(project_root / "data" / "prices.csv"),
                "--capital-plan-dir",
                str(reports_dir / "decision_gate"),
                "--output-dir",
                str(reports_dir),
            ],
        )
    )

    steps.append(
        PipelineStep(
            name="investment_tracking",
            command=[
                py,
                str(scripts / "run_investment_tracking.py"),
                "--trade-journal-csv",
                str(project_root / "configs" / "trade_journal.actual.csv"),
                "--prices-csv",
                str(project_root / "data" / "prices.csv"),
                "--output-dir",
                str(reports_dir),
            ],
        )
    )

    steps.append(
        PipelineStep(
            name="operating_status",
            command=[
                py,
                str(scripts / "run_operating_status.py"),
                "--reports-dir",
                str(reports_dir),
                "--dashboard-path",
                str(reports_dir / "dashboard" / "index.html"),
            ],
        )
    )

    if _symbol_requested(add_code, add_symbol):
        intake_command = [
            py,
            str(scripts / "run_symbol_analysis.py"),
            "--config",
            str(config_path),
            "--universe-csv",
            str(universe_csv),
            "--output-dir",
            str(reports_dir),
            "--company-name",
            add_company_name,
            "--market",
            add_market,
            "--sector",
            add_sector,
            "--min-samples",
            str(symbol_min_samples),
        ]
        if add_code:
            intake_command.extend(["--code", add_code])
        if add_symbol:
            intake_command.extend(["--symbol", add_symbol])
        if fundamentals_csv:
            intake_command.extend(["--fundamentals-csv", str(fundamentals_csv)])
        if replace_symbol:
            intake_command.append("--replace")
        steps.append(PipelineStep(name="symbol_analysis_intake", command=intake_command))

    if add_symbols_csv:
        batch_intake_command = [
            py,
            str(scripts / "run_symbol_batch_analysis.py"),
            "--symbols-csv",
            str(add_symbols_csv),
            "--config",
            str(config_path),
            "--universe-csv",
            str(universe_csv),
            "--output-dir",
            str(reports_dir),
            "--min-samples",
            str(symbol_min_samples),
        ]
        if fundamentals_csv:
            batch_intake_command.extend(["--fundamentals-csv", str(fundamentals_csv)])
        if replace_symbol:
            batch_intake_command.append("--replace")
        steps.append(PipelineStep(name="symbol_batch_analysis_intake", command=batch_intake_command))

    steps.append(
        PipelineStep(
            name="dashboard",
            command=[py, str(scripts / "run_dashboard.py"), "--reports-dir", str(reports_dir)],
        )
    )
    return steps


def _symbol_requested(
    code: str | None,
    symbol: str | None,
    symbols_csv: Path | str | None = None,
) -> bool:
    return bool((code or "").strip() or (symbol or "").strip() or symbols_csv)


def _resolve_fundamentals(project_root: Path, fundamentals_csv: Path | str | None) -> Path | None:
    if fundamentals_csv:
        return Path(fundamentals_csv).resolve()
    candidate = project_root / "configs" / "fundamentals.actual.csv"
    return candidate if candidate.exists() else None


def _resolve_shares(project_root: Path, shares_csv: Path | str | None) -> Path | None:
    if shares_csv:
        return Path(shares_csv).resolve()
    candidate = project_root / "configs" / "shares_outstanding.actual.csv"
    return candidate if candidate.exists() else None


def _resolve_manual_review(project_root: Path, manual_review_csv: Path | str | None) -> Path | None:
    if manual_review_csv:
        return Path(manual_review_csv).resolve()
    candidate = project_root / "configs" / "manual_review.actual.csv"
    return candidate if candidate.exists() else None


def _amount_arg(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _subprocess_runner(command: Sequence[str], cwd: Path) -> int:
    completed = subprocess.run(command, cwd=cwd, check=False)
    return int(completed.returncode)
