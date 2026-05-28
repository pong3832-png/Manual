from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.today_command import run_today_analysis


def test_today_analysis_runs_local_pipeline_with_one_easy_command() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()

        output = run_today_analysis(
            project_root=root,
            stock="삼성전자",
            dry_run=True,
        )

        assert output.pipeline.summary["external_api_requested"] == "NO"
        assert output.pipeline.summary["symbol_intake_requested"] == "YES"
        assert any("오늘 분석" in line for line in output.lines)
        assert any("삼성전자" in line for line in output.lines)
        assert any("외부 가격 조회: 안함" in line for line in output.lines)
        assert any("주문 실행: 안함" in line for line in output.lines)
        assert any("대시보드:" in line for line in output.lines)


def test_today_analysis_can_explicitly_request_market_refresh() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()

        output = run_today_analysis(
            project_root=root,
            stock=None,
            refresh_market_data=True,
            dry_run=True,
        )

        assert output.pipeline.summary["external_api_requested"] == "YES"
        assert output.pipeline.steps[0].name == "market_data_refresh"
        assert any("외부 가격 조회: 요청됨" in line for line in output.lines)
