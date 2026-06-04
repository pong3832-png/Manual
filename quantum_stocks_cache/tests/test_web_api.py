from __future__ import annotations

import importlib
import sys
import time
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


def test_fastapi_app_default_analysis_requests_live_refresh() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)
        calls: list[tuple[str | None, bool, bool]] = []

        def fake_run_today_analysis(project_root: Path, stock: str | None, refresh_market_data: bool, dry_run: bool):
            calls.append((stock, refresh_market_data, dry_run))

            class _Pipeline:
                summary = {
                    "external_api_requested": "YES" if refresh_market_data else "NO",
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
        assert body["summary"]["external_api_requested"] == "YES"
        assert body["order_status"] == "NO_ORDER"
        assert calls == [("삼성전자", True, False)]


def test_fastapi_app_can_force_cached_analysis() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)
        calls: list[tuple[str | None, bool, bool]] = []

        def fake_run_today_analysis(project_root: Path, stock: str | None, refresh_market_data: bool, dry_run: bool):
            calls.append((stock, refresh_market_data, dry_run))

            class _Pipeline:
                summary = {
                    "external_api_requested": "YES" if refresh_market_data else "NO",
                    "dashboard_path": str(root / "reports" / "dashboard" / "index.html"),
                }

            class _Output:
                pipeline = _Pipeline()
                lines = ["오늘 분석 실행", "주문 실행: 안함"]

            return _Output()

        app = module.create_app(project_root=root, analysis_runner=fake_run_today_analysis)
        client = module.TestClient(app)
        response = client.post("/api/analyze", json={"stock": "삼성전자", "cache_market_data": True})

        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["external_api_requested"] == "NO"
        assert calls == [("삼성전자", False, False)]


def test_fastapi_app_honors_refresh_market_data_false() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)
        calls: list[tuple[str | None, bool, bool]] = []

        def fake_run_today_analysis(project_root: Path, stock: str | None, refresh_market_data: bool, dry_run: bool):
            calls.append((stock, refresh_market_data, dry_run))

            class _Pipeline:
                summary = {
                    "external_api_requested": "YES" if refresh_market_data else "NO",
                    "dashboard_path": str(root / "reports" / "dashboard" / "index.html"),
                }

            class _Output:
                pipeline = _Pipeline()
                lines = ["오늘 분석 실행", "주문 실행: 안함"]

            return _Output()

        app = module.create_app(project_root=root, analysis_runner=fake_run_today_analysis)
        client = module.TestClient(app)
        response = client.post("/api/analyze", json={"stock": "삼성전자", "refresh_market_data": False})

        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["external_api_requested"] == "NO"
        assert body["order_status"] == "NO_ORDER"
        assert calls == [("삼성전자", False, False)]


def test_fastapi_analyze_job_reports_progress_and_result() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)
        calls: list[tuple[str | None, bool, bool]] = []

        def fake_run_today_analysis(project_root: Path, stock: str | None, refresh_market_data: bool, dry_run: bool):
            calls.append((stock, refresh_market_data, dry_run))

            class _Pipeline:
                summary = {
                    "external_api_requested": "YES" if refresh_market_data else "NO",
                    "dashboard_path": str(root / "reports" / "dashboard" / "index.html"),
                }

            class _Output:
                pipeline = _Pipeline()
                lines = ["오늘 분석 실행", "주문 실행: 안함"]

            return _Output()

        app = module.create_app(project_root=root, analysis_runner=fake_run_today_analysis)
        client = module.TestClient(app)
        response = client.post(
            "/api/analyze/jobs",
            json={"refresh_market_data": False, "dry_run": True},
        )

        assert response.status_code == 200
        created = response.json()
        assert created["job_id"]
        assert created["status"] in {"QUEUED", "RUNNING", "DONE"}
        assert created["order_status"] == "NO_ORDER"
        assert created["stage"] in {"QUEUED", "STAGE_1", "DONE"}
        assert created["stage_text"]
        assert created["elapsed_seconds"] >= 0
        assert created["external_api_requested"] == "NO"

        body = created
        for _ in range(20):
            if body["status"] == "DONE":
                break
            time.sleep(0.05)
            body = client.get(f"/api/analyze/jobs/{created['job_id']}").json()

        assert body["status"] == "DONE"
        assert body["stage"] == "DONE"
        assert body["stage_text"]
        assert body["elapsed_seconds"] >= 0
        assert body["summary"]["external_api_requested"] == "NO"
        assert body["order_status"] == "NO_ORDER"
        assert body["broker_order_requested"] == "NO"
        assert body["lines"] == ["오늘 분석 실행", "주문 실행: 안함"]
        assert calls == [(None, False, True)]


def test_fastapi_analyze_job_with_stock_uses_quick_local_runner() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)
        full_calls: list[tuple[str | None, bool, bool]] = []
        quick_calls: list[tuple[str | None, bool, bool]] = []

        def fake_full_analysis(project_root: Path, stock: str | None, refresh_market_data: bool, dry_run: bool):
            full_calls.append((stock, refresh_market_data, dry_run))
            raise AssertionError("full analysis should not run for stock jobs")

        def fake_quick_analysis(project_root: Path, stock: str | None, refresh_market_data: bool, dry_run: bool):
            quick_calls.append((stock, refresh_market_data, dry_run))

            class _Pipeline:
                summary = {
                    "analysis_mode": "QUICK_STOCK",
                    "external_api_requested": "NO",
                    "dashboard_path": str(root / "reports" / "dashboard" / "index.html"),
                }

            class _Output:
                pipeline = _Pipeline()
                lines = ["빠른 종목 분석", "주문 실행: 없음"]

            return _Output()

        app = module.create_app(
            project_root=root,
            analysis_runner=fake_full_analysis,
            quick_analysis_runner=fake_quick_analysis,
        )
        client = module.TestClient(app)
        response = client.post(
            "/api/analyze/jobs",
            json={"stock": "005930", "refresh_market_data": True, "cache_market_data": False},
        )

        assert response.status_code == 200
        body = response.json()
        for _ in range(20):
            if body["status"] == "DONE":
                break
            time.sleep(0.05)
            body = client.get(f"/api/analyze/jobs/{body['job_id']}").json()

        assert body["status"] == "DONE"
        assert body["stage"] == "DONE"
        assert body["stage_text"]
        assert body["elapsed_seconds"] >= 0
        assert body["external_api_requested"] == "NO"
        assert body["summary"]["analysis_mode"] == "QUICK_STOCK"
        assert body["summary"]["external_api_requested"] == "NO"
        assert body["order_status"] == "NO_ORDER"
        assert quick_calls == [("005930", False, False)]
        assert full_calls == []


def test_fastapi_app_searches_stock_name_without_code() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)
        configs = root / "configs"
        configs.mkdir(parents=True, exist_ok=True)
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


def test_candidates_endpoint_combines_watchlist_prebuy_and_market_gate() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)

        app = module.create_app(project_root=root)
        client = module.TestClient(app)
        response = client.get("/api/candidates", params={"limit": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["as_of"] == "2026-05-28"
        assert body["order_status"] == "NO_ORDER"
        assert body["broker_order_requested"] == "NO"
        assert body["market"]["regime_status"] == "RISK_OFF"
        assert body["market"]["risk_posture"] == "DEFENSIVE"
        assert body["candidates"][0]["symbol"] == "033640.KQ"
        assert body["candidates"][0]["company_name"] == "네패스"
        assert body["candidates"][0]["decision_status"] == "WAIT"
        assert body["candidates"][0]["entry_price_low"] == 33000
        assert body["candidates"][0]["entry_price_high"] == 37300
        assert body["candidates"][0]["readiness_blockers"] == "manual gate not ready"
        assert body["candidates"][0]["order_status"] == "NO_ORDER"


def test_candidates_endpoint_exposes_operator_control_tower_and_decision_summary() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)

        payload = module.build_candidate_payload(project_root=root, limit=1)

        assert payload["control_tower"]["market_entry_policy"] == "DEFENSIVE_REVIEW"
        assert payload["control_tower"]["data_status"] == "CACHED_LOCAL"
        assert payload["control_tower"]["external_api_requested"] == "NO"
        assert payload["control_tower"]["order_status"] == "NO_ORDER"
        assert payload["control_tower"]["candidate_count"] == 1
        assert payload["control_tower"]["risk_note"]

        summary = payload["candidates"][0]["decision_summary"]
        assert summary["label"] == "MARKET_WAIT"
        assert summary["watch_price_low"] == 33000
        assert summary["watch_price_high"] == 37300
        assert summary["risk_line"] == "SMA20 break plus -7%"
        assert summary["order_status"] == "NO_ORDER"


def test_holdings_endpoint_keeps_review_only_sell_watch() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)

        app = module.create_app(project_root=root)
        client = module.TestClient(app)
        response = client.get("/api/holdings")

        assert response.status_code == 200
        body = response.json()
        assert body["as_of"] == "2026-05-28"
        assert body["order_status"] == "NO_ORDER"
        assert body["broker_order_requested"] == "NO"
        assert body["summary"]["holding_count"] == 1
        assert body["summary"]["quantity_known_count"] == 0
        assert body["summary"]["quantity_missing_count"] == 1
        assert body["summary"]["risk_review_count"] == 1
        assert body["summary"]["known_market_value"] == 0
        assert body["summary"]["highest_priority_action"] == "REDUCE_REVIEW"
        assert body["holdings"][0]["symbol"] == "083450.KQ"
        assert body["holdings"][0]["company_name"] == "GST"
        assert body["holdings"][0]["entry_price"] == 48200
        assert body["holdings"][0]["quantity_known"] is False
        assert body["holdings"][0]["latest_price"] == 44800
        assert body["holdings"][0]["action_status"] == "REDUCE_REVIEW"
        assert body["holdings"][0]["risk_stop_price"] == 44826
        assert body["holdings"][0]["order_status"] == "NO_ORDER"


def test_holdings_endpoint_exposes_review_only_defense_summary() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)

        payload = module.build_holdings_payload(project_root=root)

        assert payload["control_tower"]["highest_priority_action"] == "REDUCE_REVIEW"
        assert payload["control_tower"]["risk_review_count"] == 1
        assert payload["control_tower"]["order_status"] == "NO_ORDER"
        assert payload["control_tower"]["external_api_requested"] == "NO"

        summary = payload["holdings"][0]["decision_summary"]
        assert summary["label"] == "REDUCE_REVIEW"
        assert summary["watch_price_low"] == 43380
        assert summary["watch_price_high"] == 44826
        assert summary["risk_line"] == "risk stop level reached"
        assert summary["order_status"] == "NO_ORDER"


def test_holdings_endpoint_updates_local_quantity_without_order_action() -> None:
    module = importlib.import_module("quantum_trainer.web_api")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        _write_minimal_reports(root)

        app = module.create_app(project_root=root)
        client = module.TestClient(app)
        response = client.post(
            "/api/holdings",
            json={
                "holdings": [
                    {
                        "symbol": "083450.KQ",
                        "company_name": "GST",
                        "entry_price": 48200,
                        "quantity": 2,
                        "notes": "updated quantity",
                    }
                ]
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["order_status"] == "NO_ORDER"
        assert body["broker_order_requested"] == "NO"
        assert body["summary"]["quantity_known_count"] == 1
        assert body["summary"]["quantity_missing_count"] == 0
        assert body["summary"]["known_cost_basis"] == 96400
        assert body["summary"]["known_market_value"] == 89600
        assert body["summary"]["known_unrealized_pnl"] == -6800
        assert body["holdings"][0]["quantity"] == 2
        assert body["holdings"][0]["quantity_known"] is True
        assert body["holdings"][0]["market_value"] == 89600
        assert "083450.KQ,GST,48200.0,2.0,updated quantity" in (
            root / "configs" / "holding_watch.actual.csv"
        ).read_text(encoding="utf-8")


def _write_minimal_reports(root: Path) -> None:
    reports = root / "reports"
    data = root / "data"
    configs = root / "configs"
    (reports / "profit_focus").mkdir(parents=True)
    (reports / "operating_status").mkdir(parents=True)
    (reports / "universe_coverage").mkdir(parents=True)
    (reports / "performance_tracking").mkdir(parents=True)
    (reports / "tactical_watchlist").mkdir(parents=True)
    (reports / "pre_buy_decision").mkdir(parents=True)
    (reports / "market_regime").mkdir(parents=True)
    (reports / "trend_forecast").mkdir(parents=True)
    (reports / "event_adjusted_ranking").mkdir(parents=True)
    (reports / "dashboard").mkdir(parents=True)
    data.mkdir(parents=True)
    configs.mkdir(parents=True)

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
            {
                "symbol": "033640.KQ",
                "company_name": "네패스",
                "sector": "반도체 제조업",
                "tactical_status": "SECTOR_RECOVERY_WATCH",
                "tactical_priority": 2,
                "priority_score": 79.85,
                "final_watch_status": "MARKET_WAIT",
                "entry_watch_status": "WAIT_MARKET_REGIME",
                "sector_rotation_status": "EARLY_ROTATION",
                "sector_recovery_status": "WATCH_CONFIRMATION",
                "sector_regime_status": "RECOVERY_WATCH",
                "final_rank_score": 52.85,
                "chase_risk": "NO",
                "latest_price": 37300,
                "key_reason": "섹터 회복 관찰권",
                "next_check": "market gate clear",
                "operator_action": "시장 게이트 해제 전 신규 주문 없음",
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "broker_order_requested": "NO",
            }
        ]
    ).to_csv(reports / "tactical_watchlist" / "tactical_watchlist.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "033640.KQ",
                "company_name": "네패스",
                "decision_status": "WAIT",
                "order_status": "NO_ORDER",
                "final_action": "NO_ORDER",
                "manual_proposal_status": "INCOMPLETE_DRAFT",
                "capital_status": "CAPITAL_PROVIDED",
                "readiness_blockers": "manual gate not ready",
                "buy_reasons": "conviction_score=74.18",
                "buy_ban_reasons": "manual gate not ready",
                "entry_price_low": 33000,
                "entry_price_high": 37300,
                "staged_buy_plan": "first tranche 30%",
                "stop_loss_rule": "SMA20 break plus -7%",
                "next_review_date": "2026-06-04",
            }
        ]
    ).to_csv(reports / "pre_buy_decision" / "pre_buy_decision.csv", index=False)
    pd.DataFrame(
        [
            {
                "scope": "MARKET",
                "sector": "ALL",
                "bullish_ratio": 0.05,
                "bearish_ratio": 0.66,
                "average_trend_score": 16.63,
                "regime_status": "RISK_OFF",
                "risk_posture": "DEFENSIVE",
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "action_summary": "defensive posture",
            }
        ]
    ).to_csv(reports / "market_regime" / "market_regime.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "083450.KQ",
                "company_name": "GST",
                "sector": "특수 목적용 기계 제조업",
                "latest_price": 44800,
                "latest_price_date": "2026-05-28",
                "sample_count": 250,
                "return_5d": -0.08,
                "return_20d": -0.12,
                "return_60d": 0.18,
                "ma20": 51000,
                "ma60": 39000,
                "ma20_position": -0.12,
                "ma60_position": 0.15,
                "volatility_20d": 0.05,
                "max_drawdown_60d": -0.2,
                "trend_regime": "PULLBACK_UPTREND",
                "forecast_bias": "WATCH_REBOUND",
                "chase_risk": "MEDIUM",
                "trend_score": 66.2,
                "research_score": 37.5,
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "action_summary": "wait for rebound evidence",
            }
        ]
    ).to_csv(reports / "trend_forecast" / "trend_forecast.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "083450.KQ",
                "company_name": "GST",
                "sector": "특수 목적용 기계 제조업",
                "final_watch_status": "LOW_PRIORITY",
                "rank_bucket": 6,
                "final_rank_score": 12.4,
                "quant_decision": "REJECT",
                "research_score": 37.5,
                "event_decision": "NO_EVENT",
                "event_score": 0,
                "chase_risk": "NO",
                "entry_status": "ENTRY_REVIEW",
                "market_regime_status": "RISK_OFF",
                "market_risk_posture": "DEFENSIVE",
                "sector_regime_status": "RISK_OFF",
                "sector_risk_posture": "DEFENSIVE",
                "latest_price": 44800,
                "expected_20d_return": 0.05,
                "upside_probability": 0.6,
                "return_20d": -0.12,
                "ma20_gap": -0.12,
                "valuation_status": "VALUATION_UNKNOWN",
                "risk_status": "RISK_REVIEW",
                "catalyst_title": "",
                "action_summary": "우선순위 낮음. 신규 매수 검토 대상 아님.",
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
            }
        ]
    ).to_csv(reports / "event_adjusted_ranking" / "event_adjusted_ranking.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "083450.KQ",
                "company_name": "GST",
                "entry_price": 48200,
                "quantity": "",
                "notes": "test holding",
            }
        ]
    ).to_csv(configs / "holding_watch.actual.csv", index=False)
    pd.DataFrame(
        [
            {"date": "2026-05-27", "003550.KS": 118200, "083450.KQ": 48200},
            {"date": "2026-05-28", "003550.KS": 115800, "083450.KQ": 44800},
        ]
    ).to_csv(data / "prices.csv", index=False)
    (reports / "dashboard" / "index.html").write_text("<html>dashboard</html>", encoding="utf-8")
