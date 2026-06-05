from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from quantum_trainer.alpha_forecast import AlphaForecastConfig, run_alpha_forecast
from quantum_trainer.buy_timing import score_buy_timing
from quantum_trainer.config import load_runtime_config
from quantum_trainer.features import build_feature_frame
from quantum_trainer.fundamentals import load_fundamentals_csv
from quantum_trainer.io import load_price_csv

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompanyResearchOutput:
    csv_path: Path
    markdown_path: Path
    report: pd.DataFrame


def run_company_research(
    config_path: Path | str,
    universe_csv: Path | str | None = None,
    fundamentals_csv: Path | str | None = None,
    reports_dir: Path | str | None = None,
    min_samples: int = 80,
) -> CompanyResearchOutput:
    runtime_config = load_runtime_config(config_path)
    prices = load_price_csv(runtime_config.prices_csv, drop_incomplete=False)
    universe = _load_research_universe(universe_csv, prices.columns)
    available_symbols = [symbol for symbol in universe["symbol"].astype(str).tolist() if symbol in prices.columns]
    if not available_symbols:
        raise ValueError("No universe symbols have cached price columns.")
    prices = prices.loc[:, available_symbols].copy()
    latest_price_date = prices.index.max().date().isoformat()
    latest_prices = prices.tail(1).T.reset_index()
    latest_prices.columns = ["symbol", "latest_price"]

    forecast = run_alpha_forecast(
        prices,
        AlphaForecastConfig(min_samples=min_samples),
    )
    timing = score_buy_timing(forecast).reset_index()
    features = _latest_features(prices)

    report = (
        universe.merge(timing, on="symbol", how="left")
        .merge(features, on="symbol", how="left")
        .merge(latest_prices, on="symbol", how="left")
    )
    if fundamentals_csv is not None:
        fundamentals = load_fundamentals_csv(fundamentals_csv)
        fundamentals = fundamentals.drop(columns=["latest_price"], errors="ignore")
        report = report.merge(fundamentals, on="symbol", how="left")
    report["latest_price_date"] = latest_price_date
    report["extension_risk"] = report.apply(_extension_risk, axis=1)
    report["extension_penalty"] = report.apply(_extension_penalty, axis=1)
    report["research_score"] = report.apply(_research_score, axis=1)
    report["research_view"] = report.apply(_research_view, axis=1)
    report["why_summary"] = report.apply(_why_summary, axis=1)
    report = report.sort_values(["research_score", "symbol"], ascending=[False, True]).reset_index(
        drop=True
    )

    output_root = Path(reports_dir).resolve() if reports_dir else runtime_config.reports_dir
    csv_path, markdown_path = _save_company_research(report, output_root)
    return CompanyResearchOutput(csv_path=csv_path, markdown_path=markdown_path, report=report)


def _load_research_universe(
    universe_csv: Path | str | None,
    symbols: pd.Index,
) -> pd.DataFrame:
    if universe_csv is None:
        return pd.DataFrame(
            {
                "symbol": [str(symbol) for symbol in symbols],
                "company_name": [str(symbol) for symbol in symbols],
                "sector": ["UNKNOWN" for _ in symbols],
            }
        )

    path = Path(universe_csv).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Research universe CSV not found: {path}")
    universe = pd.read_csv(path)
    if "symbol" not in universe.columns:
        raise ValueError("Research universe CSV must include a 'symbol' column.")
    universe = universe.copy()
    universe["symbol"] = universe["symbol"].astype(str).str.strip()
    if "company_name" not in universe.columns:
        universe["company_name"] = universe["symbol"]
    if "sector" not in universe.columns:
        universe["sector"] = "UNKNOWN"
    return universe.loc[:, ["symbol", "company_name", "sector"]]


def _latest_features(prices: pd.DataFrame) -> pd.DataFrame:
    features = build_feature_frame(prices)
    latest = features.sort_values("date").groupby("symbol").tail(1).copy()
    return latest.loc[
        :,
        [
            "symbol",
            "return_5d",
            "return_20d",
            "ma20_gap",
            "ma60_gap",
            "realized_vol_20d",
            "drawdown_20d",
        ],
    ]


def _research_score(row: pd.Series) -> float:
    score = float(_number(row.get("buy_timing_score"), default=0.0))
    if _number(row.get("return_20d")) > 0.0:
        score += 10.0
    else:
        score -= 10.0
    if _number(row.get("ma20_gap")) > 0.0:
        score += 5.0
    else:
        score -= 5.0
    if _number(row.get("drawdown_20d")) < -0.10:
        score -= 10.0
    score -= _number(row.get("extension_penalty"))
    if "fundamental_score" in row.index:
        score = score * 0.60 + _number(row.get("fundamental_score")) * 0.40
    return float(np.clip(score, 0.0, 100.0))


def _research_view(row: pd.Series) -> str:
    if row.get("decision") == "AVOID":
        return "AVOID_FOR_NOW"
    if str(row.get("extension_risk", "ENTRY_RANGE_OK")) != "ENTRY_RANGE_OK":
        return "WAIT_PULLBACK"
    if (
        row.get("decision") == "BUY_READY"
        and _number(row.get("return_20d")) > 0.0
        and _number(row.get("ma20_gap")) > 0.0
        and str(row.get("fundamental_view", "FUNDAMENTAL_NEUTRAL")) != "FUNDAMENTAL_WEAK"
    ):
        return "RESEARCH_CANDIDATE"
    return "WATCHLIST"


def _why_summary(row: pd.Series) -> str:
    reasons: list[str] = []
    decision = str(row.get("decision", "UNKNOWN"))
    if decision == "BUY_READY":
        reasons.append("ALPHA_BUY_READY")
    elif decision == "WAIT":
        reasons.append("ALPHA_WAIT")
    elif decision == "AVOID":
        reasons.append("ALPHA_AVOID")

    if _number(row.get("expected_20d_return")) > 0.0:
        reasons.append("POSITIVE_EXPECTED_RETURN")
    if _number(row.get("upside_probability")) >= 0.55:
        reasons.append("UPSIDE_PROBABILITY_OK")
    if _number(row.get("return_20d")) > 0.0:
        reasons.append("POSITIVE_20D_MOMENTUM")
    else:
        reasons.append("NEGATIVE_20D_MOMENTUM")
    if _number(row.get("ma20_gap")) > 0.0:
        reasons.append("ABOVE_SMA20")
    else:
        reasons.append("BELOW_SMA20")
    if _number(row.get("drawdown_20d")) > -0.10:
        reasons.append("DRAWDOWN_CONTROLLED")
    else:
        reasons.append("DRAWDOWN_DEEP")
    extension_risk = str(row.get("extension_risk", "ENTRY_RANGE_OK"))
    if extension_risk == "OVEREXTENDED_WAIT":
        reasons.append("OVEREXTENDED_20D_RETURN")
    elif extension_risk == "EXTREME_EXTENSION":
        reasons.append("EXTREME_PRICE_EXTENSION")
    fundamental_view = row.get("fundamental_view")
    if isinstance(fundamental_view, str) and fundamental_view:
        reasons.append(fundamental_view)
    return ",".join(reasons)


def _extension_risk(row: pd.Series) -> str:
    return_20d = _number(row.get("return_20d"))
    ma20_gap = _number(row.get("ma20_gap"))
    if return_20d >= 0.50 or ma20_gap >= 0.25:
        return "EXTREME_EXTENSION"
    if return_20d >= 0.25 or ma20_gap >= 0.15:
        return "OVEREXTENDED_WAIT"
    return "ENTRY_RANGE_OK"


def _extension_penalty(row: pd.Series) -> float:
    return_20d = _number(row.get("return_20d"))
    ma20_gap = _number(row.get("ma20_gap"))
    penalty = 0.0
    if return_20d >= 0.50:
        penalty += 25.0
    elif return_20d >= 0.25:
        penalty += 12.0
    if ma20_gap >= 0.25:
        penalty += 20.0
    elif ma20_gap >= 0.15:
        penalty += 8.0
    return penalty


def _number(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _save_company_research(report: pd.DataFrame, reports_dir: Path | str) -> tuple[Path, Path]:
    output_dir = Path(reports_dir).resolve() / "company_research"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "company_research.csv"
    markdown_path = output_dir / "company_research.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")
    return csv_path, markdown_path


def _render_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Company Research Candidates",
        "",
        "This is a data-driven research ranking, not an instruction to trade.",
        "No broker order or external API call was performed.",
        "Expected return and upside probability are model outputs, not guaranteed returns.",
        "",
        "## Ranking Summary",
        "",
        "| Rank | Symbol | Company | Sector | Score | View | Alpha | Fundamentals | Why |",
        "|---:|---|---|---|---:|---|---|---|---|",
    ]
    ranked_rows = list(report.itertuples(index=False))
    for rank, row in enumerate(ranked_rows, start=1):
        lines.append(
            "| {rank} | {symbol} | {company_name} | {sector} | {score:.2f} | {view} | {decision} | {fundamentals} | {why} |".format(
                rank=rank,
                symbol=row.symbol,
                company_name=row.company_name,
                sector=row.sector,
                score=float(row.research_score),
                view=row.research_view,
                decision=row.decision,
                fundamentals=getattr(row, "fundamental_view", "NOT_PROVIDED"),
                why=row.why_summary,
            )
        )
    lines.append("")
    for rank, row in enumerate(ranked_rows, start=1):
        lines.extend(_render_company_detail(rank, row))
    return "\n".join(lines)


def _render_company_detail(rank: int, row: object) -> list[str]:
    lines = [
        f"## {rank}. {row.symbol} {row.company_name}",
        "",
        f"- Sector: {row.sector}",
        f"- Research view: {row.research_view}",
        f"- Research score: {float(row.research_score):.2f}",
        f"- Alpha decision: {row.decision}",
        f"- Extension risk: {getattr(row, 'extension_risk', 'ENTRY_RANGE_OK')}",
        f"- Fundamental view: {getattr(row, 'fundamental_view', 'NOT_PROVIDED')}",
        f"- Latest price date: {getattr(row, 'latest_price_date', 'UNKNOWN')}",
        "",
        "### 투자 논리",
        *_bullet_lines(_investment_thesis(row)),
        "",
        "### 주요 리스크",
        *_bullet_lines(_risk_points(row)),
        "",
        "### 확인 질문",
        *_bullet_lines(_review_questions(row)),
        "",
    ]
    return lines


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def _investment_thesis(row: object) -> list[str]:
    items: list[str] = []
    if getattr(row, "decision", "") == "BUY_READY":
        items.append("alpha 모델 기준으로 추가 검토할 만한 매수 후보 신호가 있습니다.")
    elif getattr(row, "decision", "") == "WAIT":
        items.append("alpha 모델은 아직 기다리는 쪽을 가리키며, 추가 확인이 필요합니다.")
    else:
        items.append("alpha 모델은 현재 제외 또는 보류 쪽을 가리킵니다.")

    if _number(getattr(row, "expected_20d_return", 0.0)) > 0.0:
        items.append("20거래일 기대수익률 모델 값이 양수입니다.")
    if _number(getattr(row, "upside_probability", 0.0)) >= 0.55:
        items.append("상승 확률 모델 값이 기준선보다 높습니다.")
    if _number(getattr(row, "return_20d", 0.0)) > 0.0:
        items.append("20일 모멘텀이 양호합니다.")
    if _number(getattr(row, "ma20_gap", 0.0)) > 0.0:
        items.append("현재 가격이 SMA20 위에 있어 단기 추세가 우호적입니다.")
    if str(getattr(row, "fundamental_view", "")) in {"FUNDAMENTAL_STRONG", "FUNDAMENTAL_NEUTRAL"}:
        items.append(f"재무 점수는 {getattr(row, 'fundamental_view')} 등급입니다.")
    return items


def _risk_points(row: object) -> list[str]:
    items: list[str] = []
    if str(getattr(row, "extension_risk", "ENTRY_RANGE_OK")) == "OVEREXTENDED_WAIT":
        items.append("Recent 20-day move is stretched; wait for a pullback before first entry.")
    if str(getattr(row, "extension_risk", "ENTRY_RANGE_OK")) == "EXTREME_EXTENSION":
        items.append("Short-term price extension is extreme; chase-buy risk is high.")
    if _number(getattr(row, "return_20d", 0.0)) <= 0.0:
        items.append("20일 모멘텀이 약해 단기 추세 확인이 필요합니다.")
    if _number(getattr(row, "ma20_gap", 0.0)) <= 0.0:
        items.append("현재 가격이 SMA20 아래에 있어 추세 회복 확인이 필요합니다.")
    if _number(getattr(row, "drawdown_20d", 0.0)) <= -0.10:
        items.append("20일 낙폭이 커서 변동성 리스크가 큽니다.")
    if str(getattr(row, "fundamental_view", "")) == "FUNDAMENTAL_WEAK":
        items.append("재무 점수가 약해 실적/부채/밸류에이션을 추가 확인해야 합니다.")
    if _number(getattr(row, "per", 0.0)) > 30.0:
        items.append("PER이 높아 기대 성장률이 뒷받침되는지 확인해야 합니다.")
    if _number(getattr(row, "pbr", 0.0)) > 3.0:
        items.append("PBR이 높아 자본 대비 가격 부담을 확인해야 합니다.")
    if not items:
        items.append("현재 데이터 기준의 큰 차단 리스크는 제한적이지만, 뉴스/공시 확인이 필요합니다.")
    return items


def _review_questions(row: object) -> list[str]:
    return [
        "최근 실적 발표와 다음 분기 가이던스가 모델 신호를 뒷받침하는가?",
        "현재 밸류에이션이 업종 평균과 비교해 과도하지 않은가?",
        "단기 가격 모멘텀이 이벤트성 급등인지 구조적 개선인지 확인했는가?",
        "실제 투자 전 손절 기준과 최대 비중을 정했는가?",
    ]
