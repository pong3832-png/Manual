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
    "return_5d",
    "return_20d",
    "return_60d",
    "ma20",
    "ma60",
    "ma20_position",
    "ma60_position",
    "volatility_20d",
    "max_drawdown_60d",
    "trend_regime",
    "forecast_bias",
    "chase_risk",
    "trend_score",
    "research_score",
    "order_status",
    "external_api_requested",
    "action_summary",
]


@dataclass(frozen=True)
class TrendForecastOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame
    summary: dict[str, int | str]


def run_trend_forecast(
    prices_csv: Path | str,
    company_research_csv: Path | str,
    output_dir: Path | str,
    min_samples: int = 60,
) -> TrendForecastOutput:
    if min_samples <= 0:
        raise ValueError("min_samples must be greater than 0.")

    prices = _load_prices(Path(prices_csv))
    research = _load_research(Path(company_research_csv))
    report = _build_report(prices=prices, research=research, min_samples=min_samples)

    output_root = Path(output_dir).resolve() / "trend_forecast"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "trend_forecast.csv"
    markdown_path = output_root / "trend_forecast.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = {
        "row_count": int(len(report)),
        "bullish_count": int((report["forecast_bias"] == "BULLISH").sum()) if not report.empty else 0,
        "watch_pullback_count": int((report["forecast_bias"] == "WATCH_PULLBACK").sum()) if not report.empty else 0,
        "bearish_count": int((report["forecast_bias"] == "BEARISH").sum()) if not report.empty else 0,
        "insufficient_count": int((report["trend_regime"] == "INSUFFICIENT_DATA").sum()) if not report.empty else 0,
        "external_api_requested": "NO",
        "order_status": "NO_ORDER",
    }
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return TrendForecastOutput(csv_path=csv_path, markdown_path=markdown_path, report=report, summary=summary)


def _load_prices(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Prices CSV not found: {path}")
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise ValueError("Prices CSV missing required column: date")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return frame


def _load_research(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Company research CSV not found: {path}")
    frame = pd.read_csv(path).fillna("")
    missing = sorted(RESEARCH_REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Company research CSV missing required columns: {missing}")
    return frame


def _build_report(prices: pd.DataFrame, research: pd.DataFrame, min_samples: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for research_row in research.to_dict(orient="records"):
        symbol = str(research_row.get("symbol", "")).strip()
        if not symbol:
            continue
        metrics = _symbol_metrics(prices=prices, symbol=symbol, min_samples=min_samples)
        trend_regime = _trend_regime(metrics=metrics, min_samples=min_samples)
        chase_risk = _chase_risk(metrics=metrics, trend_regime=trend_regime)
        forecast_bias = _forecast_bias(trend_regime=trend_regime, chase_risk=chase_risk)
        rows.append(
            {
                "symbol": symbol,
                "company_name": str(research_row.get("company_name", "")),
                "sector": str(research_row.get("sector", "")),
                "latest_price": metrics["latest_price"],
                "latest_price_date": metrics["latest_price_date"],
                "sample_count": metrics["sample_count"],
                "return_5d": metrics["return_5d"],
                "return_20d": metrics["return_20d"],
                "return_60d": metrics["return_60d"],
                "ma20": metrics["ma20"],
                "ma60": metrics["ma60"],
                "ma20_position": metrics["ma20_position"],
                "ma60_position": metrics["ma60_position"],
                "volatility_20d": metrics["volatility_20d"],
                "max_drawdown_60d": metrics["max_drawdown_60d"],
                "trend_regime": trend_regime,
                "forecast_bias": forecast_bias,
                "chase_risk": chase_risk,
                "trend_score": _trend_score(metrics=metrics, trend_regime=trend_regime),
                "research_score": _number(research_row.get("research_score")),
                "order_status": "NO_ORDER",
                "external_api_requested": "NO",
                "action_summary": _action_summary(forecast_bias=forecast_bias, chase_risk=chase_risk),
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _symbol_metrics(prices: pd.DataFrame, symbol: str, min_samples: int) -> dict[str, object]:
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
    ma20 = _moving_average(series, 20)
    ma60 = _moving_average(series, 60)
    daily_returns = series.pct_change().dropna()
    drawdown_60d = _max_drawdown(series.tail(60))

    return {
        "latest_price": round(latest_price, 4),
        "latest_price_date": symbol_frame["date"].iloc[-1].date().isoformat(),
        "sample_count": int(len(series)),
        "return_5d": round(_period_return(series, 5), 6),
        "return_20d": round(_period_return(series, 20), 6),
        "return_60d": round(_period_return(series, 60), 6),
        "ma20": round(ma20, 4),
        "ma60": round(ma60, 4),
        "ma20_position": round(_position(latest_price, ma20), 6),
        "ma60_position": round(_position(latest_price, ma60), 6),
        "volatility_20d": round(float(daily_returns.tail(20).std()) if not daily_returns.empty else 0.0, 6),
        "max_drawdown_60d": round(drawdown_60d, 6),
    }


def _empty_metrics() -> dict[str, object]:
    return {
        "latest_price": 0.0,
        "latest_price_date": "",
        "sample_count": 0,
        "return_5d": 0.0,
        "return_20d": 0.0,
        "return_60d": 0.0,
        "ma20": 0.0,
        "ma60": 0.0,
        "ma20_position": 0.0,
        "ma60_position": 0.0,
        "volatility_20d": 0.0,
        "max_drawdown_60d": 0.0,
    }


def _trend_regime(metrics: dict[str, object], min_samples: int) -> str:
    if int(metrics["sample_count"]) < min_samples:
        return "INSUFFICIENT_DATA"

    price = float(metrics["latest_price"])
    ma20 = float(metrics["ma20"])
    ma60 = float(metrics["ma60"])
    return_20d = float(metrics["return_20d"])
    return_60d = float(metrics["return_60d"])

    if price > ma20 > ma60 and return_20d > 0.0 and return_60d > 0.0:
        return "UPTREND"
    if price < ma20 and ma20 > ma60 and return_60d > 0.0:
        return "PULLBACK_UPTREND"
    if price < ma20 < ma60 and return_20d < 0.0 and return_60d < 0.0:
        return "DOWNTREND"
    if return_20d <= -0.05 and float(metrics["ma20_position"]) < 0.0:
        return "DOWNTREND"
    return "RANGE"


def _chase_risk(metrics: dict[str, object], trend_regime: str) -> str:
    if trend_regime == "INSUFFICIENT_DATA":
        return "UNKNOWN"
    return_20d = float(metrics["return_20d"])
    ma20_position = float(metrics["ma20_position"])
    volatility_20d = float(metrics["volatility_20d"])
    if return_20d >= 0.20 or ma20_position >= 0.15:
        return "HIGH"
    if return_20d >= 0.10 or ma20_position >= 0.07 or volatility_20d >= 0.04:
        return "MEDIUM"
    return "LOW"


def _forecast_bias(trend_regime: str, chase_risk: str) -> str:
    if trend_regime == "INSUFFICIENT_DATA":
        return "UNKNOWN"
    if trend_regime == "UPTREND":
        if chase_risk == "HIGH":
            return "WATCH_PULLBACK"
        return "BULLISH"
    if trend_regime == "PULLBACK_UPTREND":
        return "WATCH_REBOUND"
    if trend_regime == "DOWNTREND":
        return "BEARISH"
    return "NEUTRAL"


def _trend_score(metrics: dict[str, object], trend_regime: str) -> float:
    if trend_regime == "INSUFFICIENT_DATA":
        return 0.0
    score = (
        50.0
        + float(metrics["return_20d"]) * 120.0
        + float(metrics["return_60d"]) * 60.0
        + float(metrics["ma20_position"]) * 80.0
        + float(metrics["ma60_position"]) * 40.0
        - float(metrics["volatility_20d"]) * 100.0
        - abs(float(metrics["max_drawdown_60d"])) * 20.0
    )
    return round(max(0.0, min(100.0, score)), 4)


def _action_summary(forecast_bias: str, chase_risk: str) -> str:
    if forecast_bias == "BULLISH":
        return "trend favorable; confirm valuation and manual gates; keep order_status=NO_ORDER"
    if forecast_bias == "WATCH_PULLBACK":
        return "trend strong but extended; wait for pullback or consolidation; keep order_status=NO_ORDER"
    if forecast_bias == "WATCH_REBOUND":
        return "longer trend intact but price is pulling back; wait for rebound evidence; keep order_status=NO_ORDER"
    if forecast_bias == "BEARISH":
        return "downtrend; exclude until trend recovers; keep order_status=NO_ORDER"
    if forecast_bias == "UNKNOWN":
        return "insufficient local price history; refresh or add data only with approval; keep order_status=NO_ORDER"
    return f"mixed trend with chase_risk={chase_risk}; keep on watchlist; keep order_status=NO_ORDER"


def _render_markdown(report: pd.DataFrame, summary: dict[str, int | str]) -> str:
    lines = [
        "# Trend Forecast",
        "",
        "Local-only price-flow report. It does not fetch prices, call external APIs, or place orders.",
        "",
        f"- Total symbols: {summary['row_count']}",
        f"- BULLISH: {summary['bullish_count']}",
        f"- WATCH_PULLBACK: {summary['watch_pullback_count']}",
        f"- BEARISH: {summary['bearish_count']}",
        f"- INSUFFICIENT_DATA: {summary['insufficient_count']}",
        "- External API requested: NO",
        "- Order status: NO_ORDER",
        "",
        "| Rank | Symbol | Company | Regime | Bias | Chase | Score | 20D | 60D | Action |",
        "|---:|---|---|---|---|---|---:|---:|---:|---|",
    ]
    ordered = report.copy()
    ordered["_bias_rank"] = ordered["forecast_bias"].map(
        {"BULLISH": 5, "WATCH_PULLBACK": 4, "WATCH_REBOUND": 3, "NEUTRAL": 2, "BEARISH": 1, "UNKNOWN": 0}
    ).fillna(0)
    ordered = ordered.sort_values(["_bias_rank", "trend_score", "research_score"], ascending=[False, False, False])
    for rank, row in enumerate(ordered.head(30).itertuples(index=False), start=1):
        lines.append(
            "| {rank} | {symbol} | {company} | {regime} | {bias} | {chase} | {score:.2f} | {return20:.1%} | {return60:.1%} | {action} |".format(
                rank=rank,
                symbol=row.symbol,
                company=row.company_name,
                regime=row.trend_regime,
                bias=row.forecast_bias,
                chase=row.chase_risk,
                score=float(row.trend_score),
                return20=float(row.return_20d),
                return60=float(row.return_60d),
                action=row.action_summary,
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


def _position(price: float, average: float) -> float:
    if average <= 0:
        return 0.0
    return price / average - 1.0


def _max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    running_max = series.cummax()
    drawdown = series / running_max - 1.0
    return float(drawdown.min())


def _number(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
