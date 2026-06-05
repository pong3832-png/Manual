from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from quantum_trainer.dashboard import run_dashboard
from quantum_trainer.config import load_runtime_config
from quantum_trainer.io import load_price_csv
from quantum_trainer.market_data import fetch_market_prices, write_price_cache
from quantum_trainer.symbol_analysis import run_symbol_analysis
from quantum_trainer.symbol_input import resolve_stock_input
from quantum_trainer.today_pipeline import CommandRunner, PipelineStep, TodayPipelineOutput, run_today_pipeline


@dataclass(frozen=True)
class TodayAnalysisOutput:
    pipeline: TodayPipelineOutput
    lines: list[str]


def run_today_analysis(
    project_root: Path | str,
    stock: str | None = None,
    refresh_market_data: bool = True,
    dry_run: bool = False,
    runner: CommandRunner | None = None,
) -> TodayAnalysisOutput:
    root = Path(project_root).resolve()
    pipeline = run_today_pipeline(
        project_root=root,
        add_stock=stock,
        refresh_market_data=refresh_market_data,
        dry_run=dry_run,
        runner=runner,
    )
    return TodayAnalysisOutput(
        pipeline=pipeline,
        lines=_format_lines(stock=stock, dry_run=dry_run, pipeline=pipeline),
    )


def run_quick_stock_analysis(
    project_root: Path | str,
    stock: str | None = None,
    refresh_market_data: bool = False,
    dry_run: bool = False,
) -> TodayAnalysisOutput:
    root = Path(project_root).resolve()
    stock_text = stock.strip() if stock else ""
    if not stock_text:
        return run_today_analysis(
            project_root=root,
            stock=None,
            refresh_market_data=refresh_market_data,
            dry_run=dry_run,
        )

    config_path = root / "configs" / "portfolio.yaml"
    universe_csv = root / "configs" / "research_universe.actual.csv"
    reports_dir = root / "reports"
    dashboard_path = reports_dir / "dashboard" / "index.html"
    resolved = resolve_stock_input(stock_text, universe_csv=universe_csv)
    fundamentals_csv = root / "configs" / "fundamentals.actual.csv"
    fundamentals_arg = fundamentals_csv if fundamentals_csv.exists() else None
    steps = [
        PipelineStep(
            name="symbol_analysis_intake",
            command=[
                "python",
                str(root / "scripts" / "run_symbol_analysis.py"),
                "--config",
                str(config_path),
                "--universe-csv",
                str(universe_csv),
                "--code",
                resolved.code,
                "--company-name",
                resolved.company_name,
                "--market",
                resolved.market,
                "--sector",
                resolved.sector,
                "--output-dir",
                str(reports_dir),
            ],
        ),
        PipelineStep(
            name="dashboard",
            command=[
                "python",
                str(root / "scripts" / "run_dashboard.py"),
                "--reports-dir",
                str(reports_dir),
            ],
        ),
    ]
    executed: list[str] = []
    symbol_status = "DRY_RUN"
    refresh_status = "NO"
    if not dry_run:
        if refresh_market_data:
            _refresh_single_symbol_price_cache(root=root, symbol=resolved.symbol)
            refresh_status = "YES"
        symbol_output = run_symbol_analysis(
            config_path=config_path,
            universe_csv=universe_csv,
            output_dir=reports_dir,
            code=resolved.code,
            company_name=resolved.company_name,
            market=resolved.market,
            sector=resolved.sector,
            fundamentals_csv=fundamentals_arg,
        )
        symbol_status = symbol_output.status
        executed.append("symbol_analysis_intake")
        run_dashboard(reports_dir=reports_dir)
        executed.append("dashboard")

    pipeline = TodayPipelineOutput(
        steps=steps,
        executed_steps=executed,
        summary={
            "analysis_date": date.today().isoformat(),
            "analysis_mode": "QUICK_STOCK",
            "step_count": len(steps),
            "executed_count": len(executed),
            "market_data_refresh": "YES" if refresh_market_data else "NO",
            "external_api_requested": "YES" if refresh_market_data else "NO",
            "symbol_intake_requested": "YES",
            "single_symbol_refresh": refresh_status,
            "symbol_analysis_status": symbol_status,
            "dashboard_path": str(dashboard_path),
        },
    )
    return TodayAnalysisOutput(
        pipeline=pipeline,
        lines=_format_lines(stock=stock_text, dry_run=dry_run, pipeline=pipeline),
    )


def _refresh_single_symbol_price_cache(root: Path, symbol: str) -> None:
    config_path = root / "configs" / "portfolio.yaml"
    runtime_config = load_runtime_config(config_path)
    fresh = fetch_market_prices([symbol], config=runtime_config.market_data)
    try:
        existing = load_price_csv(runtime_config.prices_csv, drop_incomplete=False)
    except FileNotFoundError:
        merged = fresh
    else:
        remaining = existing.drop(columns=[symbol], errors="ignore")
        columns = list(remaining.columns) + [symbol]
        merged = remaining.join(fresh[[symbol]], how="outer").sort_index().reindex(columns=columns)
    write_price_cache(merged, runtime_config.prices_csv)


def _format_lines(
    stock: str | None,
    dry_run: bool,
    pipeline: TodayPipelineOutput,
) -> list[str]:
    summary = pipeline.summary
    title = "오늘 분석 미리보기" if dry_run else "오늘 분석 실행"
    stock_text = stock.strip() if stock else "전체 후보"
    external_requested = summary["external_api_requested"] == "YES"
    external_text = "요청됨" if external_requested else "안함"
    approval_text = "YES" if external_requested else "NO"
    return [
        title,
        f"기준일: {summary['analysis_date']}",
        f"종목: {stock_text}",
        f"실행 단계: {summary['executed_count']} / {summary['step_count']}",
        f"최신 가격 조회: {external_text}",
        f"외부 데이터 승인 필요: {approval_text}",
        "주문 실행: 안함",
        f"대시보드: {summary['dashboard_path']}",
    ]
