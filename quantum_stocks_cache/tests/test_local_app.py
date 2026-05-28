from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.local_app import render_home, run_form_analysis


def test_local_app_home_is_simple_korean_workflow() -> None:
    html = render_home()

    assert "퀀트 트레이너" in html
    assert "종목 입력" in html
    assert "오늘 분석 실행" in html
    assert "오늘 결론 보기" in html
    assert "최신 가격 갱신" in html
    assert "주문 실행 없음" in html
    assert "broker" not in html.lower()


def test_local_app_runs_today_analysis_from_form_without_external_refresh_by_default() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()

        output = run_form_analysis(
            project_root=root,
            form={"stock": "삼성전자"},
            dry_run=True,
        )

        assert output.pipeline.summary["external_api_requested"] == "NO"
        assert output.pipeline.summary["symbol_intake_requested"] == "YES"
        assert any("삼성전자" in line for line in output.lines)


def test_local_app_can_request_latest_price_only_when_checked() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        (root / "scripts").mkdir()
        (root / "configs").mkdir()
        (root / "reports").mkdir()

        output = run_form_analysis(
            project_root=root,
            form={"refresh_market_data": "on"},
            dry_run=True,
        )

        assert output.pipeline.summary["external_api_requested"] == "YES"
