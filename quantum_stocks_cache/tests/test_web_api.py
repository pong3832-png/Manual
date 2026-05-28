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


def test_web_status_payload_is_safe_korean_app_summary() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)

        payload = module.build_status_payload(project_root=root)

        assert payload["app_name"] == "퀀트 트레이너"
        assert payload["completion_status"] == "DONE"
        assert payload["order_status"] == "NO_ORDER"
        assert payload["broker_order_requested"] == "NO"
        assert payload["latest_price_date"] == "2026-05-28"
        assert payload["top_candidate"]["symbol"] == "003550.KS"
        assert payload["top_candidate"]["company_name"] == "LG"
        assert payload["top_candidate"]["decision"] == "BUY_READY"
        assert payload["universe"]["universe_count"] == 35
        assert payload["universe"]["price_coverage_status"] == "PRICE_COVERAGE_READY"
        assert payload["tracking"]["tracking_status"] == "NO_TRADE_JOURNAL"


def test_fastapi_app_default_analysis_does_not_request_external_refresh() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)
        calls: list[tuple[str | None, bool, bool]] = []

        def fake_run_today_analysis(project_root: Path, stock: str | None, refresh_market_data: bool, dry_run: bool):
            calls.append((stock, refresh_market_data, dry_run))

            class _Pipeline:
                summary = {
                    "external_api_requested": "NO",
                    "dashboard_path": str(root / "reports" / "dashboard" / "index.html"),
                }

            class _Output:
                pipeline = _Pipeline()
                lines = ["오늘 분석 실행", "주문 실행: 안함"]

            return _Output()

        app = module.create_app(project_root=root, analysis_runner=fake_run_today_analysis)
        client = module.TestClient(app)
        response = client.post("/api/analyze", json={"stock": "삼성전자"})

        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["external_api_requested"] == "NO"
        assert body["order_status"] == "NO_ORDER"
        assert calls == [("삼성전자", False, False)]


def test_fastapi_app_searches_stock_name_without_code() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)
        configs = root / "configs"
        configs.mkdir(parents=True)
        pd.DataFrame(
            [
                {
                    "symbol": "373220.KS",
                    "company_name": "LG Energy Solution",
                    "sector": "Battery",
                    "market": "KOSPI",
                    "code": "373220",
                }
            ]
        ).to_csv(configs / "research_universe.actual.csv", index=False)

        app = module.create_app(project_root=root)
        client = module.TestClient(app)
        response = client.get("/api/search", params={"q": "에너지"})

        assert response.status_code == 200
        body = response.json()
        assert body["order_status"] == "NO_ORDER"
        assert body["candidates"][0]["company_name"] == "LG에너지솔루션"
        assert body["candidates"][0]["symbol"] == "373220.KS"


def _write_minimal_reports(root: Path) -> None:
    reports = root / "reports"
    data = root / "data"
    (reports / "profit_focus").mkdir(parents=True)
    (reports / "operating_status").mkdir(parents=True)
    (reports / "universe_coverage").mkdir(parents=True)
    (reports / "performance_tracking").mkdir(parents=True)
    (reports / "dashboard").mkdir(parents=True)
    data.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "symbol": "003550.KS",
                "company_name": "LG Corp",
                "profit_focus_status": "CORE_FOCUS",
                "decision": "BUY_READY",
                "conviction_score": 69.17,
                "why_not_now": "핵심 후보지만 실제 주문 전 수동 확인 필요",
            }
        ]
    ).to_csv(reports / "profit_focus" / "profit_focus.csv", index=False)
    pd.DataFrame(
        [
            {
                "completion_status": "DONE",
                "usage_status": "READY_FOR_REVIEW_USE",
                "top_symbol": "003550.KS",
                "company_name": "LG Corp",
                "decision_status": "BUY_READY",
                "order_status": "NO_ORDER",
                "broker_order_requested": "NO",
            }
        ]
    ).to_csv(reports / "operating_status" / "operating_status.csv", index=False)
    pd.DataFrame(
        [
            {
                "universe_status": "PASS_CANDIDATE",
                "universe_count": 35,
                "price_coverage_status": "PRICE_COVERAGE_READY",
                "order_status": "NO_ORDER",
            }
        ]
    ).to_csv(reports / "universe_coverage" / "universe_coverage.csv", index=False)
    pd.DataFrame(
        [
            {
                "tracking_status": "NO_TRADE_JOURNAL",
                "review_action": "WRITE_TRADE_JOURNAL_AFTER_BUY",
                "order_status": "NO_ORDER",
            }
        ]
    ).to_csv(reports / "performance_tracking" / "performance_tracking.csv", index=False)
    pd.DataFrame(
        [
            {"date": "2026-05-27", "003550.KS": 118200},
            {"date": "2026-05-28", "003550.KS": 115800},
        ]
    ).to_csv(data / "prices.csv", index=False)
    (reports / "dashboard" / "index.html").write_text("<html>dashboard</html>", encoding="utf-8")
