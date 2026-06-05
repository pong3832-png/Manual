from __future__ import annotations

import threading
import uuid
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
from quantum_trainer.symbol_input import resolve_stock_input
from quantum_trainer.today_command import TodayAnalysisOutput, run_quick_stock_analysis, run_today_analysis


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
    refresh_market_data: bool = True
    cache_market_data: bool = False
    dry_run: bool = False


class HoldingInput(BaseModel):
    symbol: str
    company_name: str | None = None
    entry_price: float = 0.0
    quantity: float | None = None
    notes: str | None = None


class TradeInput(BaseModel):
    stock: str
    side: str
    price: float
    quantity: float
    trade_date: str | None = None
    notes: str | None = None


class HoldingsUpdateRequest(BaseModel):
    holdings: list[HoldingInput]


def create_app(
    project_root: Path | str,
    analysis_runner: AnalysisRunner = run_today_analysis,
    quick_analysis_runner: AnalysisRunner = run_quick_stock_analysis,
) -> FastAPI:
    root = Path(project_root).resolve()
    app = FastAPI(title="퀀트 트레이너", version="1.0.0")
    jobs: dict[str, dict[str, Any]] = {}
    jobs_lock = threading.Lock()

    dist_dir = root / "web" / "dist"
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/api/status")
    def api_status() -> dict[str, Any]:
        return build_status_payload(root)

    @app.get("/api/candidates")
    def api_candidates(limit: int = 12) -> dict[str, Any]:
        return build_candidate_payload(root, limit=limit)

    @app.get("/api/holdings")
    def api_holdings() -> dict[str, Any]:
        return build_holdings_payload(root)

    @app.get("/api/symbol-analysis")
    def api_symbol_analysis(stock: str = "") -> dict[str, Any]:
        return build_symbol_analysis_payload(root, stock=stock)

    @app.get("/api/stock-detail")
    def api_stock_detail(stock: str = "") -> dict[str, Any]:
        return build_stock_detail_payload(root, stock=stock)

    @app.post("/api/holdings")
    def api_update_holdings(request: HoldingsUpdateRequest) -> dict[str, Any]:
        try:
            write_holding_watch(root, request.holdings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return build_holdings_payload(root)

    @app.post("/api/trades")
    def api_record_trade(request: TradeInput) -> dict[str, Any]:
        try:
            record_manual_trade(root, request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        payload = build_holdings_payload(root)
        payload["trade_recorded"] = "YES"
        return payload

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
        refresh_market_data = bool(request.refresh_market_data) and not request.cache_market_data
        try:
            output = analysis_runner(root, stock, refresh_market_data, request.dry_run)
        except Exception as exc:  # pragma: no cover - HTTP boundary
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {
            "lines": output.lines,
            "summary": output.pipeline.summary,
            "order_status": "NO_ORDER",
            "broker_order_requested": "NO",
            "status": build_status_payload(root),
        }

    @app.post("/api/analyze/jobs")
    def api_create_analyze_job(request: AnalyzeRequest) -> dict[str, Any]:
        job_id = uuid.uuid4().hex
        stock = request.stock.strip() if request.stock else None
        use_quick_stock = bool(stock)
        refresh_market_data = bool(request.refresh_market_data) and not request.cache_market_data
        selected_runner = quick_analysis_runner if use_quick_stock else analysis_runner
        job = {
            "job_id": job_id,
            "status": "QUEUED",
            "stage": "QUEUED",
            "stage_text": "대기 중",
            "stock": stock or "",
            "refresh_market_data": refresh_market_data,
            "analysis_mode": "QUICK_STOCK" if use_quick_stock else "FULL_PIPELINE",
            "dry_run": request.dry_run,
            "created_at": _now_text(),
            "started_at": "",
            "finished_at": "",
            "elapsed_seconds": 0,
            "lines": [],
            "summary": {},
            "error": "",
            "external_api_requested": "NO",
            "order_status": "NO_ORDER",
            "broker_order_requested": "NO",
        }
        with jobs_lock:
            jobs[job_id] = job
        thread = threading.Thread(
            target=_run_analysis_job,
            args=(job_id, root, selected_runner, stock, refresh_market_data, request.dry_run, jobs, jobs_lock),
            daemon=True,
        )
        thread.start()
        return _job_snapshot(job)

    @app.get("/api/analyze/jobs/{job_id}")
    def api_get_analyze_job(job_id: str) -> dict[str, Any]:
        with jobs_lock:
            job = jobs.get(job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
            return _job_snapshot(job)

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


def _run_analysis_job(
    job_id: str,
    root: Path,
    analysis_runner: AnalysisRunner,
    stock: str | None,
    refresh_market_data: bool,
    dry_run: bool,
    jobs: dict[str, dict[str, Any]],
    jobs_lock: threading.Lock,
) -> None:
    _update_job(
        jobs,
        jobs_lock,
        job_id,
        status="RUNNING",
        stage="STAGE_1",
        stage_text=_stage_text("STAGE_1", refresh_market_data),
        started_at=_now_text(),
    )
    try:
        output = analysis_runner(root, stock, refresh_market_data, dry_run)
        external_api_requested = _text(output.pipeline.summary.get("external_api_requested"), "NO")
        _update_job(
            jobs,
            jobs_lock,
            job_id,
            status="DONE",
            stage="DONE",
            stage_text=_stage_text("DONE", refresh_market_data),
            finished_at=_now_text(),
            lines=output.lines,
            summary=output.pipeline.summary,
            app_status=build_status_payload(root),
            external_api_requested=external_api_requested,
            order_status="NO_ORDER",
            broker_order_requested="NO",
        )
    except Exception as exc:  # pragma: no cover - background boundary
        _update_job(
            jobs,
            jobs_lock,
            job_id,
            status="ERROR",
            stage="ERROR",
            stage_text=_stage_text("ERROR", refresh_market_data),
            finished_at=_now_text(),
            error=str(exc),
            order_status="NO_ORDER",
            broker_order_requested="NO",
        )


def _update_job(
    jobs: dict[str, dict[str, Any]],
    jobs_lock: threading.Lock,
    job_id: str,
    **updates: Any,
) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is not None:
            job.update(updates)


def _job_snapshot(job: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(job)
    snapshot["stage"] = _text(snapshot.get("stage"), snapshot.get("status", "UNKNOWN"))
    snapshot["stage_text"] = _text(snapshot.get("stage_text"), _stage_text(snapshot["stage"], bool(snapshot.get("refresh_market_data"))))
    snapshot["elapsed_seconds"] = _elapsed_seconds(snapshot)
    snapshot["external_api_requested"] = _text(snapshot.get("external_api_requested"), "NO")
    snapshot["order_status"] = "NO_ORDER"
    snapshot["broker_order_requested"] = "NO"
    return snapshot


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _stage_text(stage: str, refresh_market_data: bool) -> str:
    mode = "최신 갱신" if refresh_market_data else "로컬 캐시"
    labels = {
        "QUEUED": "대기 중",
        "STAGE_1": f"데이터 로드 중 - {mode}",
        "STAGE_2": "점수 계산 중",
        "STAGE_3": "트렌드 분석 중",
        "STAGE_4": "Decision 생성 중",
        "DONE": f"분석 완료 - {mode} 기준",
        "ERROR": "오류 발생 - 로그 확인 필요",
    }
    return labels.get(stage, _text(stage, "상태 확인 중"))


def _elapsed_seconds(job: dict[str, Any]) -> int:
    started_at = _text(job.get("started_at"), "")
    if not started_at:
        return 0
    finished_at = _text(job.get("finished_at"), "") or _now_text()
    try:
        started = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S")
        finished = datetime.strptime(finished_at, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return int(_number(job.get("elapsed_seconds")))
    return max(0, int((finished - started).total_seconds()))


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


def build_candidate_payload(project_root: Path | str, limit: int = 12) -> dict[str, Any]:
    root = Path(project_root).resolve()
    reports = root / "reports"
    latest_price_date = _latest_price_date(root / "data" / "prices.csv")
    tactical = _read_csv(reports / "tactical_watchlist" / "tactical_watchlist.csv")
    pre_buy = _read_csv(reports / "pre_buy_decision" / "pre_buy_decision.csv")
    market = _read_csv(reports / "market_regime" / "market_regime.csv")
    market_summary = _market_summary(market)
    candidate_rows = _candidate_rows(tactical, pre_buy, limit=limit)

    return {
        "as_of": latest_price_date,
        "market": market_summary,
        "control_tower": _candidate_control_tower(
            market=market_summary,
            candidates=candidate_rows,
            latest_price_date=latest_price_date,
        ),
        "candidates": candidate_rows,
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }


def build_holdings_payload(project_root: Path | str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    reports = root / "reports"
    holdings = _read_csv(root / "configs" / "holding_watch.actual.csv")
    trend = _read_csv(reports / "trend_forecast" / "trend_forecast.csv")
    event = _read_csv(reports / "event_adjusted_ranking" / "event_adjusted_ranking.csv")
    latest_price_date = _latest_price_date(root / "data" / "prices.csv")
    symbols = [_text(value, "") for value in holdings.get("symbol", [])] if not holdings.empty else []
    latest_prices = _latest_prices(root / "data" / "prices.csv", symbols)
    holding_rows = _holding_rows(holdings, trend, event, latest_prices)
    summary = _holdings_summary(holding_rows)

    return {
        "as_of": latest_price_date,
        "summary": summary,
        "control_tower": _holdings_control_tower(summary, latest_price_date),
        "holdings": holding_rows,
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }


def build_symbol_analysis_payload(project_root: Path | str, stock: str = "") -> dict[str, Any]:
    root = Path(project_root).resolve()
    stock_text = _text(stock, "")
    if not stock_text:
        row = _latest_symbol_analysis_row(root)
        requested = {}
    else:
        resolved = resolve_stock_input(stock_text, universe_csv=root / "configs" / "research_universe.actual.csv")
        requested = {
            "raw_input": stock_text,
            "symbol": resolved.symbol,
            "code": resolved.code,
            "company_name": resolved.company_name,
            "market": resolved.market,
            "sector": resolved.sector,
            "source": resolved.source,
        }
        row = _symbol_analysis_row(root, resolved.symbol)

    if row:
        analysis = _symbol_analysis_payload_from_row(row)
        found = True
    else:
        analysis = {}
        found = False

    return {
        "requested": requested,
        "found": found,
        "analysis": analysis,
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
        "external_api_requested": "NO",
    }


def build_stock_detail_payload(project_root: Path | str, stock: str = "") -> dict[str, Any]:
    root = Path(project_root).resolve()
    stock_text = _text(stock, "")
    if not stock_text:
        raise HTTPException(status_code=400, detail="stock is required")

    resolved = resolve_stock_input(stock_text, universe_csv=root / "configs" / "research_universe.actual.csv")
    symbol = resolved.symbol
    code = resolved.code or _stock_code("", symbol)
    reports = root / "reports"
    trend = _rows_by_symbol(_read_csv(reports / "trend_forecast" / "trend_forecast.csv")).get(symbol, {})
    event = _rows_by_symbol(_read_csv(reports / "event_adjusted_ranking" / "event_adjusted_ranking.csv")).get(symbol, {})
    tactical = _rows_by_symbol(_read_csv(reports / "tactical_watchlist" / "tactical_watchlist.csv")).get(symbol, {})
    pre_buy = _rows_by_symbol(_read_csv(reports / "pre_buy_decision" / "pre_buy_decision.csv")).get(symbol, {})
    symbol_analysis = _symbol_analysis_row(root, symbol)
    resolved_name = _text(resolved.company_name, "")
    if resolved_name == symbol or resolved_name == stock_text:
        resolved_name = ""
    company_name = (
        resolved_name
        or _company_name(trend.get("company_name"))
        or _company_name(event.get("company_name"))
        or _company_name(tactical.get("company_name"))
        or _company_name(symbol_analysis.get("company_name"))
        or symbol
    )
    sector = _text(resolved.sector, _text(trend.get("sector"), _text(event.get("sector"), "")))
    latest_price = float(
        _number(trend.get("latest_price"))
        or _number(event.get("latest_price"))
        or _latest_prices(root / "data" / "prices.csv", [symbol]).get(symbol)
    )
    latest_price_date = _text(
        trend.get("latest_price_date"),
        _text(symbol_analysis.get("latest_price_date"), _latest_price_date(root / "data" / "prices.csv")),
    )
    detail_status = "READY" if any([trend, event, tactical, pre_buy, symbol_analysis, latest_price > 0]) else "DATA_REQUIRED"

    return {
        "requested": {
            "raw_input": stock_text,
            "symbol": symbol,
            "code": code,
            "company_name": company_name,
            "market": resolved.market,
            "sector": sector,
            "source": resolved.source,
        },
        "found": detail_status == "READY",
        "detail_status": detail_status,
        "profile": {
            "symbol": symbol,
            "code": code,
            "company_name": _company_name(company_name),
            "market": resolved.market,
            "sector": sector,
            "latest_price": latest_price,
            "latest_price_date": latest_price_date,
        },
        "quant": _stock_quant_detail(trend, event, tactical, pre_buy, symbol_analysis),
        "investor_flow": _stock_investor_flow(root, symbol=symbol, code=code),
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
        "external_api_requested": "NO",
    }


def _stock_quant_detail(
    trend: dict[str, Any],
    event: dict[str, Any],
    tactical: dict[str, Any],
    pre_buy: dict[str, Any],
    symbol_analysis: dict[str, Any],
) -> dict[str, Any]:
    decision_summary = _candidate_decision_summary(tactical, pre_buy) if tactical or pre_buy else {}
    return {
        "analysis_status": _text(symbol_analysis.get("analysis_status"), "UNKNOWN"),
        "price_data_status": _text(symbol_analysis.get("price_data_status"), "UNKNOWN"),
        "price_rows": int(_number(symbol_analysis.get("price_rows"))),
        "research_score": float(_number(symbol_analysis.get("research_score")) or _number(trend.get("research_score"))),
        "research_view": _text(symbol_analysis.get("research_view"), "UNKNOWN"),
        "decision": _text(pre_buy.get("decision_status"), _text(symbol_analysis.get("decision"), "UNKNOWN")),
        "tactical_status": _text(tactical.get("tactical_status"), "UNKNOWN"),
        "tactical_priority": int(_number(tactical.get("tactical_priority"))),
        "priority_score": float(_number(tactical.get("priority_score"))),
        "final_watch_status": _text(event.get("final_watch_status"), _text(tactical.get("final_watch_status"), "UNKNOWN")),
        "final_rank_score": float(_number(event.get("final_rank_score")) or _number(tactical.get("final_rank_score"))),
        "entry_watch_status": _text(tactical.get("entry_watch_status"), "UNKNOWN"),
        "trend_regime": _text(trend.get("trend_regime"), "UNKNOWN"),
        "forecast_bias": _text(trend.get("forecast_bias"), "UNKNOWN"),
        "trend_score": float(_number(trend.get("trend_score"))),
        "return_5d": float(_number(trend.get("return_5d"))),
        "return_20d": float(_number(trend.get("return_20d"))),
        "return_60d": float(_number(trend.get("return_60d"))),
        "ma20_position": float(_number(trend.get("ma20_position"))),
        "ma60_position": float(_number(trend.get("ma60_position"))),
        "expected_20d_return": float(_number(event.get("expected_20d_return"))),
        "upside_probability": float(_number(event.get("upside_probability"))),
        "entry_price_low": float(_number(pre_buy.get("entry_price_low"))),
        "entry_price_high": float(_number(pre_buy.get("entry_price_high"))),
        "readiness_blockers": _text(pre_buy.get("readiness_blockers"), ""),
        "buy_reasons": _text(pre_buy.get("buy_reasons"), ""),
        "buy_ban_reasons": _text(pre_buy.get("buy_ban_reasons"), ""),
        "stop_loss_rule": _text(pre_buy.get("stop_loss_rule"), ""),
        "key_reason": _text(tactical.get("key_reason"), _text(event.get("action_summary"), "")),
        "operator_action": _text(tactical.get("operator_action"), ""),
        "decision_summary": decision_summary,
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }


def _stock_investor_flow(root: Path, symbol: str, code: str) -> dict[str, Any]:
    directory = root / "reports" / "investor_flow"
    candidates = [
        directory / f"investor_flow_{code}.csv",
        directory / f"investor_flow_{symbol.replace('.', '_')}.csv",
        directory / "investor_flow.csv",
    ]
    frame = pd.DataFrame()
    for path in candidates:
        frame = _read_csv(path)
        if frame.empty:
            continue
        if "symbol" in frame.columns:
            frame = frame.loc[frame["symbol"].astype(str) == symbol]
        elif "code" in frame.columns:
            frame = frame.loc[frame["code"].astype(str).str.zfill(6) == code]
        if not frame.empty:
            break

    if frame.empty:
        return {
            "data_status": "DATA_REQUIRED",
            "summary": "기관/외국인 수급 캐시가 없습니다. pykrx 등 외부 데이터 조회는 별도 승인 후 갱신해야 합니다.",
            "recent": [],
            "order_status": "NO_ORDER",
            "external_api_requested": "NO",
            "broker_order_requested": "NO",
        }

    records = frame.tail(10).to_dict(orient="records")
    recent = [
        {
            "date": _text(row.get("date"), _text(row.get("날짜"), "")),
            "institution": float(_number(row.get("institution")) or _number(row.get("기관"))),
            "foreign": float(_number(row.get("foreign")) or _number(row.get("외국인"))),
            "individual": float(_number(row.get("individual")) or _number(row.get("개인"))),
            "broker": _text(row.get("broker"), _text(row.get("거래원"), "")),
        }
        for row in records
    ]
    institution_total = sum(float(_number(row.get("institution"))) for row in recent)
    foreign_total = sum(float(_number(row.get("foreign"))) for row in recent)
    return {
        "data_status": "CACHED_LOCAL",
        "summary": f"최근 {len(recent)}개 로컬 수급 행: 기관 {institution_total:,.0f}, 외국인 {foreign_total:,.0f}",
        "recent": recent,
        "order_status": "NO_ORDER",
        "external_api_requested": "NO",
        "broker_order_requested": "NO",
    }


def write_holding_watch(project_root: Path | str, holdings: list[HoldingInput]) -> None:
    root = Path(project_root).resolve()
    path = root / "configs" / "holding_watch.actual.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in holdings:
        symbol = _text(item.symbol, "")
        if not symbol:
            raise ValueError("symbol is required")
        if symbol in seen:
            raise ValueError(f"duplicate holding symbol: {symbol}")
        seen.add(symbol)
        entry_price = float(_number(item.entry_price))
        quantity = float(_number(item.quantity))
        if entry_price < 0:
            raise ValueError(f"entry_price must be non-negative for {symbol}")
        if quantity < 0:
            raise ValueError(f"quantity must be non-negative for {symbol}")
        rows.append(
            {
                "symbol": symbol,
                "company_name": _text(item.company_name, ""),
                "entry_price": entry_price if entry_price > 0 else "",
                "quantity": quantity if quantity > 0 else "",
                "notes": _text(item.notes, ""),
            }
        )
    pd.DataFrame(rows, columns=["symbol", "company_name", "entry_price", "quantity", "notes"]).to_csv(
        path,
        index=False,
    )


def record_manual_trade(project_root: Path | str, trade: TradeInput) -> None:
    root = Path(project_root).resolve()
    side = _text(trade.side, "").upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    price = float(_number(trade.price))
    quantity = float(_number(trade.quantity))
    if price <= 0:
        raise ValueError("price must be positive")
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    resolved = resolve_stock_input(trade.stock, universe_csv=root / "configs" / "research_universe.actual.csv")
    trade_date = _text(trade.trade_date, "") or datetime.now().strftime("%Y-%m-%d")
    _apply_trade_to_holding_watch(
        root=root,
        symbol=resolved.symbol,
        company_name=resolved.company_name,
        side=side,
        price=price,
        quantity=quantity,
        notes=f"manual {side.lower()} recorded on {trade_date}",
    )
    _append_trade_event(
        root=root,
        row={
            "trade_date": trade_date,
            "symbol": resolved.symbol,
            "company_name": resolved.company_name,
            "side": side,
            "price": price,
            "quantity": quantity,
            "notes": _text(trade.notes, ""),
            "order_status": "NO_ORDER",
            "broker_order_requested": "NO",
        },
    )


def _append_trade_event(root: Path, row: dict[str, Any]) -> None:
    path = root / "configs" / "trade_events.actual.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "trade_date",
        "symbol",
        "company_name",
        "side",
        "price",
        "quantity",
        "notes",
        "order_status",
        "broker_order_requested",
    ]
    frame = pd.DataFrame([row], columns=columns)
    frame.to_csv(path, mode="a", header=not path.exists(), index=False, encoding="utf-8-sig")


def _apply_trade_to_holding_watch(
    root: Path,
    symbol: str,
    company_name: str,
    side: str,
    price: float,
    quantity: float,
    notes: str,
) -> None:
    path = root / "configs" / "holding_watch.actual.csv"
    columns = ["symbol", "company_name", "entry_price", "quantity", "notes"]
    frame = _read_csv(path)
    if frame.empty:
        frame = pd.DataFrame(columns=columns)
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""

    matches = frame.index[frame["symbol"].astype(str) == symbol].tolist()
    if matches:
        idx = matches[0]
        old_price = float(_number(frame.at[idx, "entry_price"]))
        old_quantity = float(_number(frame.at[idx, "quantity"]))
    else:
        idx = None
        old_price = 0.0
        old_quantity = 0.0

    if side == "BUY":
        new_quantity = old_quantity + quantity
        new_price = ((old_price * old_quantity) + (price * quantity)) / new_quantity
    else:
        if old_quantity <= 0:
            raise ValueError(f"cannot sell {symbol}: no holding quantity recorded")
        if quantity > old_quantity:
            raise ValueError(f"cannot sell {symbol}: sell quantity exceeds holding quantity")
        new_quantity = old_quantity - quantity
        new_price = old_price

    if idx is None:
        frame = pd.concat(
            [
                frame,
                pd.DataFrame(
                    [
                        {
                            "symbol": symbol,
                            "company_name": company_name,
                            "entry_price": new_price,
                            "quantity": new_quantity,
                            "notes": notes,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    elif new_quantity <= 0:
        frame = frame.drop(index=idx)
    else:
        frame.at[idx, "company_name"] = company_name or frame.at[idx, "company_name"]
        frame.at[idx, "entry_price"] = new_price
        frame.at[idx, "quantity"] = new_quantity
        frame.at[idx, "notes"] = notes

    frame.loc[:, columns].to_csv(path, index=False, encoding="utf-8-sig")


def _symbol_analysis_row(root: Path, symbol: str) -> dict[str, Any]:
    path = root / "reports" / "symbol_analysis" / f"symbol_analysis_{symbol.replace('.', '_')}.csv"
    frame = _read_csv(path)
    if frame.empty:
        return {}
    return frame.iloc[0].to_dict()


def _latest_symbol_analysis_row(root: Path) -> dict[str, Any]:
    directory = root / "reports" / "symbol_analysis"
    if not directory.exists():
        return {}
    paths = [path for path in directory.glob("symbol_analysis_*.csv") if path.is_file()]
    if not paths:
        return {}
    latest = max(paths, key=lambda path: path.stat().st_mtime)
    frame = _read_csv(latest)
    if frame.empty:
        return {}
    return frame.iloc[0].to_dict()


def _symbol_analysis_payload_from_row(row: dict[str, Any]) -> dict[str, Any]:
    symbol = _text(row.get("symbol"), "")
    return {
        "symbol": symbol,
        "company_name": _company_name(row.get("company_name")),
        "sector": _text(row.get("sector"), ""),
        "market": _text(row.get("market"), ""),
        "code": _stock_code(row.get("code"), symbol),
        "analysis_status": _text(row.get("analysis_status"), "UNKNOWN"),
        "local_pipeline_ready": _text(row.get("local_pipeline_ready"), "NO"),
        "price_data_status": _text(row.get("price_data_status"), "UNKNOWN"),
        "price_rows": int(_number(row.get("price_rows"))),
        "min_samples_required": int(_number(row.get("min_samples_required"))),
        "blocking_reason": _text(row.get("blocking_reason"), ""),
        "company_research_rank": _text(row.get("company_research_rank"), ""),
        "latest_price": float(_number(row.get("latest_price"))),
        "latest_price_date": _text(row.get("latest_price_date"), ""),
        "research_score": float(_number(row.get("research_score"))),
        "research_view": _text(row.get("research_view"), "UNKNOWN"),
        "decision": _text(row.get("decision"), "UNKNOWN"),
        "why_summary": _text(row.get("why_summary"), ""),
        "company_research_csv": _text(row.get("company_research_csv"), ""),
        "company_research_md": _text(row.get("company_research_md"), ""),
        "next_step": _text(row.get("next_step"), ""),
        "order_status": "NO_ORDER",
        "external_api_requested": "NO",
        "broker_order_requested": "NO",
    }


def _stock_code(value: object, symbol: str) -> str:
    text = _text(value, "")
    if text and text.isdigit():
        return text.zfill(6)
    if symbol and "." in symbol:
        return symbol.split(".", maxsplit=1)[0].zfill(6)
    return text


def _market_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        row: dict[str, Any] = {}
    elif "scope" in frame.columns and (frame["scope"] == "MARKET").any():
        row = frame.loc[frame["scope"] == "MARKET"].iloc[0].to_dict()
    else:
        row = frame.iloc[0].to_dict()

    return {
        "regime_status": _text(row.get("regime_status"), "UNKNOWN"),
        "risk_posture": _text(row.get("risk_posture"), "UNKNOWN"),
        "bullish_ratio": float(_number(row.get("bullish_ratio"))),
        "bearish_ratio": float(_number(row.get("bearish_ratio"))),
        "average_trend_score": float(_number(row.get("average_trend_score"))),
        "action_summary": _text(row.get("action_summary"), ""),
        "order_status": "NO_ORDER",
    }


def _candidate_control_tower(
    market: dict[str, Any],
    candidates: list[dict[str, Any]],
    latest_price_date: str,
) -> dict[str, Any]:
    regime = _text(market.get("regime_status"), "UNKNOWN")
    posture = _text(market.get("risk_posture"), "UNKNOWN")
    if regime == "RISK_OFF" or posture == "DEFENSIVE":
        policy = "DEFENSIVE_REVIEW"
        risk_note = "Market/sector breadth is defensive; review candidates without automatic entry."
    elif regime in {"RISK_ON", "RECOVERY_CONFIRMED"}:
        policy = "SELECTIVE_BUY_REVIEW"
        risk_note = "Market posture allows selective manual review; orders remain manual."
    else:
        policy = "SELECTIVE_REVIEW"
        risk_note = "Market posture is mixed; require price and manual gates before action."

    label_counts: dict[str, int] = {}
    for row in candidates:
        label = _text(row.get("decision_summary", {}).get("label"), "UNKNOWN")
        label_counts[label] = label_counts.get(label, 0) + 1

    return {
        "market_entry_policy": policy,
        "market_regime_status": regime,
        "market_risk_posture": posture,
        "latest_price_date": latest_price_date,
        "data_status": "CACHED_LOCAL",
        "candidate_count": len(candidates),
        "buy_review_count": label_counts.get("BUY_REVIEW", 0),
        "wait_review_count": label_counts.get("WAIT_REVIEW", 0)
        + label_counts.get("MARKET_WAIT", 0)
        + label_counts.get("WAIT_PULLBACK", 0),
        "avoid_count": label_counts.get("AVOID_FOR_NOW", 0),
        "risk_note": risk_note,
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }


def _candidate_rows(tactical: pd.DataFrame, pre_buy: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    if tactical.empty:
        return []

    capped_limit = max(1, min(int(_number(limit) or 12), 50))
    pre_buy_by_symbol = _rows_by_symbol(pre_buy)
    rows: list[dict[str, Any]] = []

    for row in tactical.head(capped_limit).to_dict(orient="records"):
        symbol = _text(row.get("symbol"), "")
        review = pre_buy_by_symbol.get(symbol, {})
        decision_summary = _candidate_decision_summary(row, review)
        rows.append(
            {
                "symbol": symbol,
                "company_name": _company_name(row.get("company_name")),
                "sector": _text(row.get("sector"), ""),
                "tactical_status": _text(row.get("tactical_status"), "UNKNOWN"),
                "tactical_priority": int(_number(row.get("tactical_priority"))),
                "priority_score": float(_number(row.get("priority_score"))),
                "final_watch_status": _text(row.get("final_watch_status"), "UNKNOWN"),
                "entry_watch_status": _text(row.get("entry_watch_status"), "UNKNOWN"),
                "sector_rotation_status": _text(row.get("sector_rotation_status"), "UNKNOWN"),
                "sector_recovery_status": _text(row.get("sector_recovery_status"), "UNKNOWN"),
                "sector_regime_status": _text(row.get("sector_regime_status"), "UNKNOWN"),
                "final_rank_score": float(_number(row.get("final_rank_score"))),
                "chase_risk": _text(row.get("chase_risk"), "UNKNOWN"),
                "latest_price": float(_number(row.get("latest_price"))),
                "key_reason": _text(row.get("key_reason"), ""),
                "next_check": _text(row.get("next_check"), ""),
                "operator_action": _text(row.get("operator_action"), ""),
                "decision_status": _text(review.get("decision_status"), "UNKNOWN"),
                "final_action": _text(review.get("final_action"), "NO_ORDER"),
                "manual_proposal_status": _text(review.get("manual_proposal_status"), "UNKNOWN"),
                "capital_status": _text(review.get("capital_status"), "UNKNOWN"),
                "readiness_blockers": _text(review.get("readiness_blockers"), ""),
                "buy_reasons": _text(review.get("buy_reasons"), ""),
                "buy_ban_reasons": _text(review.get("buy_ban_reasons"), ""),
                "entry_price_low": float(_number(review.get("entry_price_low"))),
                "entry_price_high": float(_number(review.get("entry_price_high"))),
                "staged_buy_plan": _text(review.get("staged_buy_plan"), ""),
                "stop_loss_rule": _text(review.get("stop_loss_rule"), ""),
                "next_review_date": _text(review.get("next_review_date"), ""),
                "decision_summary": decision_summary,
                "order_status": "NO_ORDER",
                "broker_order_requested": "NO",
            }
        )
    return rows


def _candidate_decision_summary(row: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    decision = _text(review.get("decision_status"), "UNKNOWN")
    final_watch = _text(row.get("final_watch_status"), "UNKNOWN")
    entry_watch = _text(row.get("entry_watch_status"), "")
    chase_risk = _text(row.get("chase_risk"), "UNKNOWN")
    if decision == "REJECT":
        label = "AVOID_FOR_NOW"
    elif final_watch == "MARKET_WAIT" or "MARKET" in entry_watch:
        label = "MARKET_WAIT"
    elif final_watch in {"WAIT_PULLBACK", "OVERHEATED_WAIT"} or "PULLBACK" in entry_watch or chase_risk in {
        "YES",
        "HIGH",
    }:
        label = "WAIT_PULLBACK"
    elif decision == "BUY_READY":
        label = "BUY_REVIEW"
    else:
        label = "WAIT_REVIEW"

    watch_low = float(_number(review.get("entry_price_low")))
    watch_high = float(_number(review.get("entry_price_high")))
    risk_line = (
        _text(review.get("stop_loss_rule"), "")
        or _text(review.get("readiness_blockers"), "")
        or _text(review.get("buy_ban_reasons"), "")
        or _text(row.get("next_check"), "")
    )
    reason = (
        _text(row.get("operator_action"), "")
        or _text(row.get("key_reason"), "")
        or _text(review.get("buy_reasons"), "")
        or _text(review.get("readiness_blockers"), "")
    )
    return {
        "label": label,
        "reason": reason,
        "watch_price_low": watch_low,
        "watch_price_high": watch_high,
        "risk_line": risk_line,
        "market_gate": final_watch,
        "chase_risk": chase_risk,
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }


def _holding_rows(
    holdings: pd.DataFrame,
    trend: pd.DataFrame,
    event: pd.DataFrame,
    latest_prices: dict[str, float],
) -> list[dict[str, Any]]:
    if holdings.empty:
        return []

    trend_by_symbol = _rows_by_symbol(trend)
    event_by_symbol = _rows_by_symbol(event)
    rows: list[dict[str, Any]] = []
    for row in holdings.to_dict(orient="records"):
        symbol = _text(row.get("symbol"), "")
        entry_price = float(_number(row.get("entry_price")))
        trend_row = trend_by_symbol.get(symbol, {})
        event_row = event_by_symbol.get(symbol, {})
        latest_price = float(_number(trend_row.get("latest_price")) or latest_prices.get(symbol, 0.0))
        unrealized_return = (latest_price / entry_price - 1.0) if entry_price > 0 and latest_price > 0 else 0.0
        quantity = float(_number(row.get("quantity")))
        quantity_known = quantity > 0
        cost_basis = entry_price * quantity if quantity_known else 0.0
        market_value = latest_price * quantity if quantity_known else 0.0
        unrealized_pnl = (latest_price - entry_price) * quantity if quantity_known else 0.0
        risk_stop_price = entry_price * 0.93 if entry_price > 0 else 0.0
        hard_stop_price = entry_price * 0.90 if entry_price > 0 else 0.0
        action, reason = _holding_action(
            latest_price=latest_price,
            risk_stop_price=risk_stop_price,
            hard_stop_price=hard_stop_price,
            trend_regime=_text(trend_row.get("trend_regime"), "UNKNOWN"),
            forecast_bias=_text(trend_row.get("forecast_bias"), "UNKNOWN"),
            ma20_position=float(_number(trend_row.get("ma20_position"))),
        )
        rows.append(
            {
                "symbol": symbol,
                "company_name": _company_name(row.get("company_name")),
                "entry_price": entry_price,
                "quantity": quantity,
                "quantity_known": quantity_known,
                "latest_price": latest_price,
                "cost_basis": cost_basis,
                "market_value": market_value,
                "unrealized_return": unrealized_return,
                "unrealized_pnl": unrealized_pnl,
                "risk_stop_price": risk_stop_price,
                "hard_stop_price": hard_stop_price,
                "action_status": action,
                "action_reason": reason,
                "trend_regime": _text(trend_row.get("trend_regime"), "UNKNOWN"),
                "forecast_bias": _text(trend_row.get("forecast_bias"), "UNKNOWN"),
                "chase_risk": _text(trend_row.get("chase_risk"), "UNKNOWN"),
                "trend_score": float(_number(trend_row.get("trend_score"))),
                "return_5d": float(_number(trend_row.get("return_5d"))),
                "return_20d": float(_number(trend_row.get("return_20d"))),
                "return_60d": float(_number(trend_row.get("return_60d"))),
                "ma20_position": float(_number(trend_row.get("ma20_position"))),
                "ma60_position": float(_number(trend_row.get("ma60_position"))),
                "final_watch_status": _text(event_row.get("final_watch_status"), "UNKNOWN"),
                "quant_decision": _text(event_row.get("quant_decision"), "UNKNOWN"),
                "final_rank_score": float(_number(event_row.get("final_rank_score"))),
                "market_regime_status": _text(event_row.get("market_regime_status"), "UNKNOWN"),
                "market_risk_posture": _text(event_row.get("market_risk_posture"), "UNKNOWN"),
                "action_summary": _text(event_row.get("action_summary"), ""),
                "decision_summary": _holding_decision_summary(
                    action=action,
                    reason=reason,
                    risk_stop_price=risk_stop_price,
                    hard_stop_price=hard_stop_price,
                    trend_regime=_text(trend_row.get("trend_regime"), "UNKNOWN"),
                    forecast_bias=_text(trend_row.get("forecast_bias"), "UNKNOWN"),
                ),
                "notes": _text(row.get("notes"), ""),
                "order_status": "NO_ORDER",
                "broker_order_requested": "NO",
            }
        )
    return rows


def _holding_decision_summary(
    action: str,
    reason: str,
    risk_stop_price: float,
    hard_stop_price: float,
    trend_regime: str,
    forecast_bias: str,
) -> dict[str, Any]:
    return {
        "label": action,
        "reason": reason,
        "watch_price_low": float(hard_stop_price),
        "watch_price_high": float(risk_stop_price),
        "risk_line": reason,
        "trend_regime": trend_regime,
        "forecast_bias": forecast_bias,
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }


def _holdings_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    known_rows = [row for row in rows if bool(row.get("quantity_known"))]
    action_counts: dict[str, int] = {}
    for row in rows:
        action = _text(row.get("action_status"), "UNKNOWN")
        action_counts[action] = action_counts.get(action, 0) + 1

    cost_basis = sum(float(_number(row.get("cost_basis"))) for row in known_rows)
    market_value = sum(float(_number(row.get("market_value"))) for row in known_rows)
    unrealized_pnl = sum(float(_number(row.get("unrealized_pnl"))) for row in known_rows)
    return {
        "holding_count": len(rows),
        "quantity_known_count": len(known_rows),
        "quantity_missing_count": len(rows) - len(known_rows),
        "risk_review_count": action_counts.get("SELL_REVIEW", 0) + action_counts.get("REDUCE_REVIEW", 0),
        "defensive_hold_count": action_counts.get("HOLD_DEFENSIVE", 0),
        "known_cost_basis": cost_basis,
        "known_market_value": market_value,
        "known_unrealized_pnl": unrealized_pnl,
        "known_unrealized_return": (unrealized_pnl / cost_basis) if cost_basis > 0 else 0.0,
        "highest_priority_action": _highest_holding_action(rows),
        "next_operator_step": _holding_next_step(rows, action_counts),
        "order_status": "NO_ORDER",
    }


def _holdings_control_tower(summary: dict[str, Any], latest_price_date: str) -> dict[str, Any]:
    risk_count = int(_number(summary.get("risk_review_count")))
    if risk_count:
        posture = "DEFENSE_FIRST"
        note = "Review risk labels before adding exposure; no automated selling."
    elif int(_number(summary.get("holding_count"))) == 0:
        posture = "NO_HOLDINGS"
        note = "No holding watch rows are available for portfolio defense."
    else:
        posture = "MONITOR"
        note = "Monitor stops and trend recovery; orders remain manual."
    return {
        "portfolio_defense_posture": posture,
        "latest_price_date": latest_price_date,
        "holding_count": int(_number(summary.get("holding_count"))),
        "risk_review_count": risk_count,
        "highest_priority_action": _text(summary.get("highest_priority_action"), "UNKNOWN"),
        "next_operator_step": _text(summary.get("next_operator_step"), note),
        "risk_note": note,
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }


def _highest_holding_action(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "NO_HOLDINGS"
    priority = {
        "SELL_REVIEW": 5,
        "REDUCE_REVIEW": 4,
        "DATA_REQUIRED": 3,
        "HOLD_DEFENSIVE": 2,
        "HOLD_REVIEW": 1,
    }
    return max(
        (_text(row.get("action_status"), "UNKNOWN") for row in rows),
        key=lambda action: priority.get(action, 0),
    )


def _holding_next_step(rows: list[dict[str, Any]], action_counts: dict[str, int]) -> str:
    if not rows:
        return "add holding_watch.actual.csv rows before portfolio review"
    if action_counts.get("SELL_REVIEW", 0):
        return "review hard-stop names first; no automated selling"
    if action_counts.get("REDUCE_REVIEW", 0):
        return "review reduce labels before adding exposure"
    missing_count = sum(1 for row in rows if not bool(row.get("quantity_known")))
    if missing_count:
        return "enter quantities to unlock total valuation and PnL"
    return "monitor stops and trend recovery; no automated order"


def _holding_action(
    latest_price: float,
    risk_stop_price: float,
    hard_stop_price: float,
    trend_regime: str,
    forecast_bias: str,
    ma20_position: float,
) -> tuple[str, str]:
    if latest_price <= 0:
        return "DATA_REQUIRED", "cached latest price is unavailable"
    if hard_stop_price > 0 and latest_price <= hard_stop_price:
        return "SELL_REVIEW", "hard stop level reached"
    if risk_stop_price > 0 and latest_price <= risk_stop_price:
        return "REDUCE_REVIEW", "risk stop level reached"
    if trend_regime == "DOWNTREND" or forecast_bias == "BEARISH":
        return "REDUCE_REVIEW", "bearish trend; protect capital before new upside review"
    if forecast_bias == "WATCH_REBOUND" and ma20_position < -0.10:
        return "HOLD_DEFENSIVE", "below MA20; hold only if rebound appears, no add"
    if forecast_bias in {"WATCH_PULLBACK", "WATCH_REBOUND"}:
        return "HOLD_REVIEW", "wait for trend confirmation before changing exposure"
    return "HOLD_REVIEW", "no local stop trigger; keep manual review"


def _rows_by_symbol(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if frame.empty or "symbol" not in frame.columns:
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        symbol = _text(row.get("symbol"), "")
        if symbol and symbol not in rows:
            rows[symbol] = row
    return rows


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


def _latest_prices(path: Path, symbols: list[str]) -> dict[str, float]:
    if not path.exists() or not symbols:
        return {}
    columns = set(pd.read_csv(path, nrows=0).columns)
    usecols = ["date"] + [symbol for symbol in symbols if symbol in columns]
    if len(usecols) == 1:
        return {}
    frame = pd.read_csv(path, usecols=usecols)
    if frame.empty:
        return {}
    row = frame.iloc[-1].to_dict()
    return {symbol: float(_number(row.get(symbol))) for symbol in symbols if symbol in row}


def _company_name(value: object) -> str:
    text = _text(value, "")
    return COMPANY_NAME_KO.get(text, text)


def _text(value: object, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
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
