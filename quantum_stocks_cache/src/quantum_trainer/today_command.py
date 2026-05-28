from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quantum_trainer.today_pipeline import CommandRunner, TodayPipelineOutput, run_today_pipeline


@dataclass(frozen=True)
class TodayAnalysisOutput:
    pipeline: TodayPipelineOutput
    lines: list[str]


def run_today_analysis(
    project_root: Path | str,
    stock: str | None = None,
    refresh_market_data: bool = False,
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


def _format_lines(
    stock: str | None,
    dry_run: bool,
    pipeline: TodayPipelineOutput,
) -> list[str]:
    summary = pipeline.summary
    title = "오늘 분석 미리보기" if dry_run else "오늘 분석 실행"
    stock_text = stock.strip() if stock else "전체 후보"
    external_text = "요청됨" if summary["external_api_requested"] == "YES" else "안함"
    return [
        title,
        f"종목: {stock_text}",
        f"실행 단계: {summary['executed_count']} / {summary['step_count']}",
        f"외부 가격 조회: {external_text}",
        "주문 실행: 안함",
        f"대시보드: {summary['dashboard_path']}",
    ]
