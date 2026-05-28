from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from pydantic import BaseModel

from quantum_trainer.symbol_input import search_stock_inputs
from quantum_trainer.today_command import TodayAnalysisOutput, run_today_analysis


AnalysisRunner = Callable[[Path, str | None, bool, bool], TodayAnalysisOutput]

COMPANY_NAME_KO = {
    "Samsung Electronics": "삼성전자",
    "Hyundai Motor": "현대차",
    "SK hynix": "SK하이닉스",
    "Samsung C&T": "삼성물산",
    "LG Corp": "LG",
    "Hyundai Mobis": "현대모비스",
}


class AnalyzeRequest(BaseModel):
    stock: str | None = None
    refresh_market_data: bool = False
    dry_run: bool = False


def create_app(
    project_root: Path | str,
    analysis_runner: AnalysisRunner = run_today_analysis,
) -> FastAPI:
    root = Path(project_root).resolve()
    app = FastAPI(title="퀀트 트레이너", version="1.0.0")

    dist_dir = root / "web" / "dist"
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/api/status")
    def api_status() -> dict[str, Any]:
        return build_status_payload(root)

    @app.get("/api/search")
    def api_search(q: str = "") -> dict[str, Any]:
        candidates = search_stock_inputs(
            q,
            universe_csv=root / "configs" / "research_universe.actual.csv",
            limit=8,
        )
        return {
            "query": q,
            "count": len(candidates),
            "candidates": [
                {
                    "symbol": item.symbol,
                    "code": item.code,
                    "company_name": item.company_name,
                    "market": item.market,
                    "sector": item.sector,
                    "source": item.source,
                }
                for item in candidates
            ],
            "order_status": "NO_ORDER",
            "broker_order_requested": "NO",
        }

    @app.post("/api/analyze")
    def api_analyze(request: AnalyzeRequest) -> dict[str, Any]:
        stock = request.stock.strip() if request.stock else None
        try:
            output = analysis_runner(root, stock, request.refresh_market_data, request.dry_run)
        except Exception as exc:  # pragma: no cover - HTTP boundary
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {
            "lines": output.lines,
            "summary": output.pipeline.summary,
            "order_status": "NO_ORDER",
            "broker_order_requested": "NO",
            "status": build_status_payload(root),
        }

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard() -> str:
        path = root / "reports" / "dashboard" / "index.html"
        if not path.exists():
            raise HTTPException(status_code=404, detail="대시보드가 아직 없습니다.")
        return path.read_text(encoding="utf-8")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "OK"}

    @app.get("/{path_name:path}", response_model=None)
    def spa(path_name: str):
        index = dist_dir / "index.html"
        if index.exists():
            return FileResponse(index)
        return HTMLResponse(_fallback_html(), status_code=200)

    return app


def build_status_payload(project_root: Path | str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    reports = root / "reports"
    profit = _read_csv(reports / "profit_focus" / "profit_focus.csv")
    operating = _first_row(_read_csv(reports / "operating_status" / "operating_status.csv"))
    universe = _first_row(_read_csv(reports / "universe_coverage" / "universe_coverage.csv"))
    tracking = _first_row(_read_csv(reports / "performance_tracking" / "performance_tracking.csv"))
    top = _top_candidate(profit, operating)
    latest_price_date = _latest_price_date(root / "data" / "prices.csv")

    return {
        "app_name": "퀀트 트레이너",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completion_status": _text(operating.get("completion_status"), "UNKNOWN"),
        "usage_status": _text(operating.get("usage_status"), "UNKNOWN"),
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
        "latest_price_date": latest_price_date,
        "dashboard_url": "/dashboard",
        "top_candidate": top,
        "universe": {
            "universe_status": _text(universe.get("universe_status"), "UNKNOWN"),
            "universe_count": int(_number(universe.get("universe_count"))),
            "price_coverage_status": _text(universe.get("price_coverage_status"), "UNKNOWN"),
        },
        "tracking": {
            "tracking_status": _text(tracking.get("tracking_status"), "NO_TRADE_JOURNAL"),
            "review_action": _text(tracking.get("review_action"), "WRITE_TRADE_JOURNAL_AFTER_BUY"),
            "order_status": "NO_ORDER",
        },
    }


def _top_candidate(profit: pd.DataFrame, operating: dict[str, Any]) -> dict[str, Any]:
    if profit.empty:
        return {
            "symbol": _text(operating.get("top_symbol"), ""),
            "company_name": _company_name(operating.get("company_name")),
            "decision": _text(operating.get("decision_status"), "UNKNOWN"),
            "profit_focus_status": "UNKNOWN",
            "conviction_score": 0.0,
            "why_not_now": "",
        }
    ordered = profit.copy()
    ordered["_rank"] = ordered.get("profit_focus_status", "").map(
        {"CORE_FOCUS": 4, "WAIT_RISK": 3, "NEEDS_CHECKLIST": 2, "WATCH_ONLY": 1}
    ).fillna(0)
    if "conviction_score" not in ordered.columns:
        ordered["conviction_score"] = 0.0
    row = ordered.sort_values(["_rank", "conviction_score"], ascending=[False, False]).iloc[0].to_dict()
    return {
        "symbol": _text(row.get("symbol"), ""),
        "company_name": _company_name(row.get("company_name")),
        "decision": _text(row.get("decision"), _text(operating.get("decision_status"), "UNKNOWN")),
        "profit_focus_status": _text(row.get("profit_focus_status"), "UNKNOWN"),
        "conviction_score": float(_number(row.get("conviction_score"))),
        "why_not_now": _text(row.get("why_not_now"), ""),
    }


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def _first_row(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {}
    return frame.iloc[0].to_dict()


def _latest_price_date(path: Path) -> str:
    if not path.exists():
        return ""
    frame = pd.read_csv(path, usecols=["date"])
    if frame.empty:
        return ""
    return str(frame.iloc[-1]["date"])


def _company_name(value: object) -> str:
    text = _text(value, "")
    return COMPANY_NAME_KO.get(text, text)


def _text(value: object, default: str = "") -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return text


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fallback_html() -> str:
    return """<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>퀀트 트레이너</title></head>
<body style="font-family:Segoe UI,Malgun Gothic,sans-serif;margin:32px">
<h1>퀀트 트레이너</h1>
<p>React 화면이 아직 빌드되지 않았습니다. <code>npm.cmd run build</code> 후 다시 실행하세요.</p>
<p>주문 실행: 안함</p>
</body>
</html>"""
