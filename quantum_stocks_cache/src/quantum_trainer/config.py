from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from quantum_trainer.data_quality import DataQualityConfig
from quantum_trainer.market_data import MarketDataConfig
from quantum_trainer.pretrade import PreTradeConfig
from quantum_trainer.risk import RiskConfig
from quantum_trainer.sizing import SizingConfig
from quantum_trainer.trend import BacktestConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeConfig:
    prices_csv: Path
    reports_dir: Path
    backtest: BacktestConfig
    risk: RiskConfig
    sizing: SizingConfig
    market_data: MarketDataConfig
    data_quality: DataQualityConfig
    pretrade: PreTradeConfig
    current_weights: Dict[str, float]


def _resolve_config_path(config_path: Path, raw_path: str) -> Path:
    try:
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate
        return (config_path.parent / candidate).resolve()
    except Exception as exc:
        logger.exception("Failed to resolve config path %s: %s", raw_path, exc)
        raise


def _required_mapping(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    try:
        value = data.get(key)
        if not isinstance(value, dict):
            raise ValueError(f"Config section '{key}' must be a mapping.")
        return value
    except Exception as exc:
        logger.exception("Invalid config section %s: %s", key, exc)
        raise


def load_runtime_config(config_path: Path | str) -> RuntimeConfig:
    try:
        path = Path(config_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open("r", encoding="utf-8") as file:
            raw = yaml.safe_load(file) or {}
        if not isinstance(raw, dict):
            raise ValueError("Config root must be a mapping.")

        data_cfg = _required_mapping(raw, "data")
        reports_cfg = _required_mapping(raw, "reports")
        strategy_cfg = _required_mapping(raw, "strategy")
        portfolio_cfg = _required_mapping(raw, "portfolio")
        risk_cfg = raw.get("risk", {})
        if risk_cfg is None:
            risk_cfg = {}
        if not isinstance(risk_cfg, dict):
            raise ValueError("Config section 'risk' must be a mapping when provided.")
        sizing_cfg = raw.get("sizing", {})
        if sizing_cfg is None:
            sizing_cfg = {}
        if not isinstance(sizing_cfg, dict):
            raise ValueError("Config section 'sizing' must be a mapping when provided.")
        market_data_cfg = raw.get("market_data", {})
        if market_data_cfg is None:
            market_data_cfg = {}
        if not isinstance(market_data_cfg, dict):
            raise ValueError("Config section 'market_data' must be a mapping when provided.")
        data_quality_cfg = raw.get("data_quality", {})
        if data_quality_cfg is None:
            data_quality_cfg = {}
        if not isinstance(data_quality_cfg, dict):
            raise ValueError("Config section 'data_quality' must be a mapping when provided.")
        pretrade_cfg = raw.get("pretrade", {})
        if pretrade_cfg is None:
            pretrade_cfg = {}
        if not isinstance(pretrade_cfg, dict):
            raise ValueError("Config section 'pretrade' must be a mapping when provided.")
        current_weights_cfg = raw.get("current_weights", {})
        if current_weights_cfg is None:
            current_weights_cfg = {}
        if not isinstance(current_weights_cfg, dict):
            raise ValueError("Config section 'current_weights' must be a mapping when provided.")

        prices_csv = _resolve_config_path(path, str(data_cfg["prices_csv"]))
        reports_dir = _resolve_config_path(path, str(reports_cfg["output_dir"]))
        weights = {str(symbol): float(weight) for symbol, weight in portfolio_cfg.items()}

        return RuntimeConfig(
            prices_csv=prices_csv,
            reports_dir=reports_dir,
            backtest=BacktestConfig(
                weights=weights,
                trend_window=int(strategy_cfg.get("trend_window", 20)),
                cost_bps=float(strategy_cfg.get("cost_bps", 5.0)),
                periods_per_year=int(strategy_cfg.get("periods_per_year", 252)),
            ),
            risk=RiskConfig(
                max_portfolio_mdd=float(risk_cfg.get("max_portfolio_mdd", -0.12)),
                max_daily_turnover=float(risk_cfg.get("max_daily_turnover", 0.50)),
                max_cash_exposure=float(risk_cfg.get("max_cash_exposure", 0.80)),
            ),
            sizing=SizingConfig(
                enabled=bool(sizing_cfg.get("enabled", True)),
                target_volatility=float(sizing_cfg.get("target_volatility", 0.15)),
                realized_vol_window=int(sizing_cfg.get("realized_vol_window", 20)),
                volatility_floor=float(sizing_cfg.get("volatility_floor", 0.05)),
                max_position_weight=float(sizing_cfg.get("max_position_weight", 1.0)),
                max_leverage=float(sizing_cfg.get("max_leverage", 1.0)),
            ),
            market_data=MarketDataConfig(
                provider=str(market_data_cfg.get("provider", "yfinance")),
                start=str(market_data_cfg.get("start", "2024-01-01")),
                end=market_data_cfg.get("end"),
                auto_adjust=bool(market_data_cfg.get("auto_adjust", True)),
                progress=bool(market_data_cfg.get("progress", False)),
            ),
            data_quality=DataQualityConfig(
                max_stale_days=int(data_quality_cfg.get("max_stale_days", 5)),
                max_abs_daily_return=float(data_quality_cfg.get("max_abs_daily_return", 0.35)),
            ),
            pretrade=PreTradeConfig(
                max_order_delta=float(pretrade_cfg.get("max_order_delta", 0.25)),
                max_gross_exposure=float(pretrade_cfg.get("max_gross_exposure", 1.0)),
            ),
            current_weights={
                str(symbol): float(weight) for symbol, weight in current_weights_cfg.items()
            },
        )
    except Exception as exc:
        logger.exception("Failed to load runtime config: %s", exc)
        raise
