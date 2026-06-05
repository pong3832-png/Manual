from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


RESEARCH_REQUIRED_COLUMNS = {"symbol"}

OUTPUT_COLUMNS = [
    "symbol",
    "company_name",
    "sector",
    "latest_price",
    "latest_price_date",
    "sample_count",
    "return_3d",
    "return_5d",
    "return_20d",
    "max_drawdown_20d",
    "max_drawdown_60d",
    "recent_low_20d",
    "rebound_from_20d_low",
    "ma10",
    "ma20",
    "ma10_reclaim",
    "ma20_reclaim",
    "panic_detected",
    "reversal_confirmed",
    "chase_risk",
    "rebound_status",
    "panic_rebound_score",
    "entry_watch_low",
    "entry_watch_high",
    "invalidation_price",
    "action_summary",
    "external_api_requested",
    "order_status",
    "broker_order_requested",
]


@dataclass(frozen=True)
class PanicReboundSignalOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_panic_rebound_signal(
    prices_csv: Path | str,
    company_research_csv: Path | str,
    output_dir: Path | str,
    min_samples: int = 60,
) -> PanicReboundSignalOutput:
    if min_samples <= 0:
        raise ValueError("min_samples must be greater than 0.")

    prices = _load_prices(Path(prices_csv))
    research = _load_research(Path(company_research_csv))
    report = _build_report(prices=prices, research=research, min_samples=min_samples)

    output_root = Path(output_dir).resolve() / "panic_rebound_signal"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "panic_rebound_signal.csv"
    markdown_path = output_root / "panic_rebound_signal.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "ready_rebound_review_count": int((report["rebound_status"] == "READY_REBOUND_REVIEW").sum())
        if not report.empty
        else 0,
        "wait_confirmation_count": int((report["rebound_status"] == "WAIT_CONFIRMATION").sum())
        if not report.empty
        else 0,
        "chase_risk_count": int((report["rebound_status"] == "CHASE_RISK").sum())
        if not report.empty
        else 0,
        "insufficient_count": int((report["rebound_status"] == "INSUFFICIENT_DATA").sum())
        if not report.empty
        else 0,
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
        "broker_order_requested": "NO",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return PanicReboundSignalOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        report=report,
        summary=summary,
    )


def _load_prices(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Prices CSV not found: {path}")
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise ValueError("Prices CSV missing required column: date")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def _load_research(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Company research CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(RESEARCH_REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Company research CSV missing required columns: {missing}")
    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    return frame


def _build_report(prices: pd.DataFrame, research: pd.DataFrame, min_samples: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for research_row in research.to_dict(orient="records"):
        symbol = str(research_row.get("symbol", "")).strip()
        if not symbol:
            continue
        metrics = _symbol_metrics(prices=prices, symbol=symbol)
        status = _rebound_status(metrics=metrics, min_samples=min_samples)
        rows.append(
            {
                "symbol": symbol,
                "company_name": str(research_row.get("company_name", "")),
                "sector": str(research_row.get("sector", "")),
                "latest_price": metrics["latest_price"],
                "latest_price_date": metrics["latest_price_date"],
                "sample_count": metrics["sample_count"],
                "return_3d": metrics["return_3d"],
                "return_5d": metrics["return_5d"],
                "return_20d": metrics["return_20d"],
                "max_drawdown_20d": metrics["max_drawdown_20d"],
                "max_drawdown_60d": metrics["max_drawdown_60d"],
                "recent_low_20d": metrics["recent_low_20d"],
                "rebound_from_20d_low": metrics["rebound_from_20d_low"],
                "ma10": metrics["ma10"],
                "ma20": metrics["ma20"],
                "ma10_reclaim": metrics["ma10_reclaim"],
                "ma20_reclaim": metrics["ma20_reclaim"],
                "panic_detected": _panic_detected(metrics=metrics, min_samples=min_samples),
                "reversal_confirmed": _reversal_confirmed(metrics=metrics, min_samples=min_samples),
                "chase_risk": _chase_risk(metrics=metrics, min_samples=min_samples),
                "rebound_status": status,
                "panic_rebound_score": _panic_rebound_score(metrics=metrics, status=status),
                "entry_watch_low": metrics["entry_watch_low"],
                "entry_watch_high": metrics["entry_watch_high"],
                "invalidation_price": metrics["invalidation_price"],
                "action_summary": _action_summary(status),
                "external_api_requested": "NO",
                "order_status": "NO_ORDER",
                "broker_order_requested": "NO",
            }
        )
    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if report.empty:
        return report
    report["_status_rank"] = report["rebound_status"].map(
        {
            "READY_REBOUND_REVIEW": 0,
            "WAIT_CONFIRMATION": 1,
            "CHASE_RISK": 2,
            "LOW_PRIORITY": 3,
            "INSUFFICIENT_DATA": 4,
        }
    ).fillna(9)
    return (
        report.sort_values(["_status_rank", "panic_rebound_score", "symbol"], ascending=[True, False, True])
        .drop(columns=["_status_rank"])
        .reset_index(drop=True)
    )


def _symbol_metrics(prices: pd.DataFrame, symbol: str) -> dict[str, object]:
    if symbol not in prices.columns:
        return _empty_metrics()

    symbol_frame = prices[["date", symbol]].copy()
    symbol_frame[symbol] = pd.to_numeric(symbol_frame[symbol], errors="coerce")
    symbol_frame = symbol_frame.dropna(subset=[symbol])
    symbol_frame = symbol_frame.loc[symbol_frame[symbol] > 0].reset_index(drop=True)
    if symbol_frame.empty:
        return _empty_metrics()

    series = symbol_frame[symbol]
    latest_price = float(series.iloc[-1])
    recent_low_20d = float(series.tail(20).min())
    ma10 = _moving_average(series, 10)
    ma20 = _moving_average(series, 20)
    return {
        "latest_price": round(latest_price, 4),
        "latest_price_date": symbol_frame["date"].iloc[-1].date().isoformat(),
        "sample_count": int(len(series)),
        "return_3d": round(_period_return(series, 3), 6),
        "return_5d": round(_period_return(series, 5), 6),
        "return_20d": round(_period_return(series, 20), 6),
        "max_drawdown_20d": round(_max_drawdown(series.tail(20)), 6),
        "max_drawdown_60d": round(_max_drawdown(series.tail(60)), 6),
        "recent_low_20d": round(recent_low_20d, 4),
        "rebound_from_20d_low": round(_position(latest_price, recent_low_20d), 6),
        "ma10": round(ma10, 4),
        "ma20": round(ma20, 4),
        "ma10_reclaim": "YES" if latest_price >= ma10 and ma10 > 0 else "NO",
        "ma20_reclaim": "YES" if latest_price >= ma20 and ma20 > 0 else "NO",
        "entry_watch_low": round(max(recent_low_20d * 1.08, ma10 * 0.97), 4),
        "entry_watch_high": round(min(latest_price, ma20 * 1.08 if ma20 > 0 else latest_price), 4),
        "invalidation_price": round(recent_low_20d * 0.97, 4),
    }


def _empty_metrics() -> dict[str, object]:
    return {
        "latest_price": 0.0,
        "latest_price_date": "",
        "sample_count": 0,
        "return_3d": 0.0,
        "return_5d": 0.0,
        "return_20d": 0.0,
        "max_drawdown_20d": 0.0,
        "max_drawdown_60d": 0.0,
        "recent_low_20d": 0.0,
        "rebound_from_20d_low": 0.0,
        "ma10": 0.0,
        "ma20": 0.0,
        "ma10_reclaim": "NO",
        "ma20_reclaim": "NO",
        "entry_watch_low": 0.0,
        "entry_watch_high": 0.0,
        "invalidation_price": 0.0,
    }


def _panic_detected(metrics: dict[str, object], min_samples: int) -> str:
    if int(metrics["sample_count"]) < min_samples:
        return "UNKNOWN"
    return_20d = float(metrics["return_20d"])
    max_drawdown_20d = float(metrics["max_drawdown_20d"])
    max_drawdown_60d = float(metrics["max_drawdown_60d"])
    if return_20d <= -0.10 or max_drawdown_20d <= -0.12 or max_drawdown_60d <= -0.18:
        return "YES"
    return "NO"


def _reversal_confirmed(metrics: dict[str, object], min_samples: int) -> str:
    if int(metrics["sample_count"]) < min_samples:
        return "UNKNOWN"
    if _panic_detected(metrics, min_samples) != "YES":
        return "NO"
    return_3d = float(metrics["return_3d"])
    return_5d = float(metrics["return_5d"])
    rebound_from_low = float(metrics["rebound_from_20d_low"])
    if (
        return_3d > 0.0
        and return_5d >= 0.03
        and rebound_from_low >= 0.08
        and str(metrics["ma10_reclaim"]) == "YES"
    ):
        return "YES"
    return "NO"


def _chase_risk(metrics: dict[str, object], min_samples: int) -> str:
    if int(metrics["sample_count"]) < min_samples:
        return "UNKNOWN"
    rebound_from_low = float(metrics["rebound_from_20d_low"])
    return_5d = float(metrics["return_5d"])
    latest_price = float(metrics["latest_price"])
    ma20 = float(metrics["ma20"])
    ma20_position = _position(latest_price, ma20)
    if rebound_from_low >= 0.35 or return_5d >= 0.18 or ma20_position >= 0.20:
        return "HIGH"
    if rebound_from_low >= 0.25 or return_5d >= 0.12 or ma20_position >= 0.12:
        return "MEDIUM"
    return "LOW"


def _rebound_status(metrics: dict[str, object], min_samples: int) -> str:
    if int(metrics["sample_count"]) < min_samples:
        return "INSUFFICIENT_DATA"
    panic = _panic_detected(metrics=metrics, min_samples=min_samples)
    reversal = _reversal_confirmed(metrics=metrics, min_samples=min_samples)
    chase = _chase_risk(metrics=metrics, min_samples=min_samples)
    if panic != "YES":
        return "LOW_PRIORITY"
    if reversal == "YES" and chase == "HIGH":
        return "CHASE_RISK"
    if reversal == "YES":
        return "READY_REBOUND_REVIEW"
    return "WAIT_CONFIRMATION"


def _panic_rebound_score(metrics: dict[str, object], status: str) -> float:
    if status == "INSUFFICIENT_DATA":
        return 0.0
    drawdown = abs(float(metrics["max_drawdown_20d"]))
    rebound = float(metrics["rebound_from_20d_low"])
    return_5d = float(metrics["return_5d"])
    score = drawdown * 180.0 + rebound * 180.0 + max(0.0, return_5d) * 120.0
    if str(metrics["ma10_reclaim"]) == "YES":
        score += 12.0
    if str(metrics["ma20_reclaim"]) == "YES":
        score += 10.0
    if status == "CHASE_RISK":
        score -= 25.0
    if status == "LOW_PRIORITY":
        return round(max(0.0, min(30.0, score)), 4)
    return round(max(0.0, min(100.0, score)), 4)


def _action_summary(status: str) -> str:
    return {
        "READY_REBOUND_REVIEW": "급락 후 반등 확인 후보. 수급/공시/시장 게이트 확인 전까지 NO_ORDER.",
        "WAIT_CONFIRMATION": "급락은 확인됐지만 반등 확인 부족. 저점 재이탈 여부를 먼저 관찰.",
        "CHASE_RISK": "반등이 이미 과도해 추격위험 높음. 눌림 없이는 검토 금지.",
        "LOW_PRIORITY": "급락-반등 패턴 아님. 낮은 우선순위.",
        "INSUFFICIENT_DATA": "가격 이력 부족. 데이터 보강은 승인 후 진행.",
    }.get(status, "검토 보류. NO_ORDER 유지.")


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Panic Rebound Signal",
        "",
        "Local-only close-price rebound watch. It does not fetch data, place orders, or write manual gates.",
        "",
        f"- row_count: {summary['row_count']}",
        f"- READY_REBOUND_REVIEW: {summary['ready_rebound_review_count']}",
        f"- WAIT_CONFIRMATION: {summary['wait_confirmation_count']}",
        f"- CHASE_RISK: {summary['chase_risk_count']}",
        f"- INSUFFICIENT_DATA: {summary['insufficient_count']}",
        "- external_api_requested: NO",
        "- order_status: NO_ORDER",
        "- broker_order_requested: NO",
        "",
        "| Rank | Symbol | Company | Status | Score | 20D DD | Low Rebound | 5D | Chase | Action | Order |",
        "|---:|---|---|---|---:|---:|---:|---:|---|---|---|",
    ]
    for rank, row in enumerate(report.head(30).itertuples(index=False), start=1):
        lines.append(
            "| {rank} | {symbol} | {company} | {status} | {score:.2f} | {dd:.1%} | {rebound:.1%} | {ret5:.1%} | {chase} | {action} | {order} |".format(
                rank=rank,
                symbol=row.symbol,
                company=row.company_name,
                status=row.rebound_status,
                score=float(row.panic_rebound_score),
                dd=float(row.max_drawdown_20d),
                rebound=float(row.rebound_from_20d_low),
                ret5=float(row.return_5d),
                chase=row.chase_risk,
                action=row.action_summary,
                order=row.order_status,
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _period_return(series: pd.Series, period: int) -> float:
    if len(series) <= period:
        return 0.0
    previous = float(series.iloc[-period - 1])
    if previous <= 0:
        return 0.0
    return float(series.iloc[-1]) / previous - 1.0


def _moving_average(series: pd.Series, window: int) -> float:
    if series.empty:
        return 0.0
    return float(series.tail(window).mean())


def _max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    running_max = series.cummax()
    drawdown = series / running_max - 1.0
    return float(drawdown.min())


def _position(price: float, reference: float) -> float:
    if reference <= 0:
        return 0.0
    return price / reference - 1.0
