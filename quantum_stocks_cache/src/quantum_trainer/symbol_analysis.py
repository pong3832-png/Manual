from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quantum_trainer.company_research import run_company_research
from quantum_trainer.config import load_runtime_config
from quantum_trainer.io import load_price_csv
from quantum_trainer.research_universe import add_research_symbol, add_research_symbols_from_csv


@dataclass(frozen=True)
class SymbolAnalysisOutput:
    csv_path: Path
    markdown_path: Path
    universe_csv: Path
    symbol: str
    status: str
    summary: dict[str, str | int]
    report: pd.DataFrame


@dataclass(frozen=True)
class SymbolBatchAnalysisOutput:
    csv_path: Path
    markdown_path: Path
    universe_csv: Path
    status: str
    summary: dict[str, str | int]
    report: pd.DataFrame


def run_symbol_analysis(
    config_path: Path | str,
    universe_csv: Path | str,
    output_dir: Path | str | None = None,
    code: str | None = None,
    symbol: str | None = None,
    company_name: str = "",
    market: str = "KOSPI",
    sector: str = "UNKNOWN",
    fundamentals_csv: Path | str | None = None,
    replace: bool = False,
    min_samples: int = 80,
) -> SymbolAnalysisOutput:
    universe_path = Path(universe_csv).resolve()
    runtime_config = load_runtime_config(config_path)
    reports_root = Path(output_dir).resolve() if output_dir else runtime_config.reports_dir

    add_result = add_research_symbol(
        universe_csv=universe_path,
        output_csv=universe_path,
        code=code,
        symbol=symbol,
        company_name=company_name,
        market=market,
        sector=sector,
        replace=replace,
    )
    target_symbol = add_result.symbol
    universe_row = _target_universe_row(add_result.universe, target_symbol)

    price_status = "MISSING"
    price_rows = 0
    blocking_reason = ""
    research_output = None
    research_row: dict[str, object] = {}
    rank = ""

    try:
        prices = load_price_csv(runtime_config.prices_csv)
        if target_symbol not in prices.columns:
            blocking_reason = "missing cached price history; refresh market data with explicit approval or add manual prices"
        else:
            series = prices[target_symbol].dropna()
            price_rows = int(series.shape[0])
            if price_rows < min_samples:
                price_status = "INSUFFICIENT"
                blocking_reason = f"insufficient cached price history: {price_rows}/{min_samples}"
            else:
                price_status = "READY"
    except FileNotFoundError:
        blocking_reason = "price csv missing; refresh market data with explicit approval or add manual prices"
    except ValueError as exc:
        blocking_reason = f"price csv invalid: {exc}"

    if price_status == "READY":
        research_output = run_company_research(
            config_path=config_path,
            universe_csv=universe_path,
            fundamentals_csv=fundamentals_csv,
            reports_dir=reports_root,
            min_samples=min_samples,
        )
        matches = research_output.report.loc[research_output.report["symbol"] == target_symbol]
        if matches.empty:
            price_status = "MISSING"
            blocking_reason = "target symbol missing from company research output"
        else:
            rank = str(int(matches.index[0]) + 1)
            research_row = matches.iloc[0].to_dict()

    status = "ANALYSIS_READY" if price_status == "READY" and not blocking_reason else "DATA_REQUIRED"
    row = _build_output_row(
        universe_row=universe_row,
        target_symbol=target_symbol,
        universe_action=add_result.action,
        status=status,
        price_status=price_status,
        price_rows=price_rows,
        min_samples=min_samples,
        blocking_reason=blocking_reason,
        research_row=research_row,
        rank=rank,
        company_research_csv=research_output.csv_path if research_output else None,
        company_research_md=research_output.markdown_path if research_output else None,
    )
    report = pd.DataFrame([row])
    csv_path, markdown_path = _save_symbol_analysis(report, reports_root, target_symbol)

    return SymbolAnalysisOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        universe_csv=universe_path,
        symbol=target_symbol,
        status=status,
        summary={
            "symbol": target_symbol,
            "status": status,
            "price_rows": price_rows,
            "external_api_requested": "NO",
        },
        report=report,
    )


def run_symbol_batch_analysis(
    config_path: Path | str,
    universe_csv: Path | str,
    symbols_csv: Path | str,
    output_dir: Path | str | None = None,
    fundamentals_csv: Path | str | None = None,
    replace: bool = False,
    min_samples: int = 80,
) -> SymbolBatchAnalysisOutput:
    universe_path = Path(universe_csv).resolve()
    runtime_config = load_runtime_config(config_path)
    reports_root = Path(output_dir).resolve() if output_dir else runtime_config.reports_dir
    add_result = add_research_symbols_from_csv(
        universe_csv=universe_path,
        symbols_csv=symbols_csv,
        output_csv=universe_path,
        replace=replace,
    )

    price_info = _batch_price_info(runtime_config.prices_csv, add_result.symbols, min_samples)
    ready_symbols = [symbol for symbol, info in price_info.items() if info["price_status"] == "READY"]
    research_output = None
    research_by_symbol: dict[str, tuple[str, dict[str, object]]] = {}
    if ready_symbols:
        research_output = run_company_research(
            config_path=config_path,
            universe_csv=universe_path,
            fundamentals_csv=fundamentals_csv,
            reports_dir=reports_root,
            min_samples=min_samples,
        )
        for symbol in ready_symbols:
            matches = research_output.report.loc[research_output.report["symbol"] == symbol]
            if not matches.empty:
                research_by_symbol[symbol] = (str(int(matches.index[0]) + 1), matches.iloc[0].to_dict())

    rows: list[dict[str, object]] = []
    for action_row in add_result.actions.itertuples(index=False):
        target_symbol = str(action_row.symbol)
        info = price_info[target_symbol]
        price_status = str(info["price_status"])
        blocking_reason = str(info["blocking_reason"])
        rank = ""
        research_row: dict[str, object] = {}
        if price_status == "READY":
            if target_symbol in research_by_symbol:
                rank, research_row = research_by_symbol[target_symbol]
            else:
                price_status = "MISSING"
                blocking_reason = "target symbol missing from company research output"
        status = "ANALYSIS_READY" if price_status == "READY" and not blocking_reason else "DATA_REQUIRED"
        rows.append(
            _build_output_row(
                universe_row=_target_universe_row(add_result.universe, target_symbol),
                target_symbol=target_symbol,
                universe_action=str(action_row.action),
                status=status,
                price_status=price_status,
                price_rows=int(info["price_rows"]),
                min_samples=min_samples,
                blocking_reason=blocking_reason,
                research_row=research_row,
                rank=rank,
                company_research_csv=research_output.csv_path if research_output else None,
                company_research_md=research_output.markdown_path if research_output else None,
            )
        )

    report = pd.DataFrame(rows)
    csv_path, markdown_path = _save_symbol_batch_analysis(report, reports_root)
    ready_count = int((report["analysis_status"] == "ANALYSIS_READY").sum()) if not report.empty else 0
    data_required_count = int((report["analysis_status"] == "DATA_REQUIRED").sum()) if not report.empty else 0
    return SymbolBatchAnalysisOutput(
        csv_path=csv_path,
        markdown_path=markdown_path,
        universe_csv=universe_path,
        status="ANALYSIS_READY" if data_required_count == 0 else "DATA_REQUIRED",
        summary={
            "row_count": len(report),
            "analysis_ready_count": ready_count,
            "data_required_count": data_required_count,
            "external_api_requested": "NO",
        },
        report=report,
    )


def _batch_price_info(
    prices_csv: Path,
    symbols: list[str],
    min_samples: int,
) -> dict[str, dict[str, object]]:
    info = {
        symbol: {
            "price_status": "MISSING",
            "price_rows": 0,
            "blocking_reason": "",
        }
        for symbol in symbols
    }
    try:
        prices = load_price_csv(prices_csv)
    except FileNotFoundError:
        for symbol in symbols:
            info[symbol]["blocking_reason"] = "price csv missing; refresh market data with explicit approval or add manual prices"
        return info
    except ValueError as exc:
        for symbol in symbols:
            info[symbol]["blocking_reason"] = f"price csv invalid: {exc}"
        return info

    for symbol in symbols:
        if symbol not in prices.columns:
            info[symbol]["blocking_reason"] = "missing cached price history; refresh market data with explicit approval or add manual prices"
            continue
        series = prices[symbol].dropna()
        row_count = int(series.shape[0])
        info[symbol]["price_rows"] = row_count
        if row_count < min_samples:
            info[symbol]["price_status"] = "INSUFFICIENT"
            info[symbol]["blocking_reason"] = f"insufficient cached price history: {row_count}/{min_samples}"
        else:
            info[symbol]["price_status"] = "READY"
    return info


def _target_universe_row(universe: pd.DataFrame, symbol: str) -> pd.Series:
    matches = universe.loc[universe["symbol"] == symbol]
    if matches.empty:
        raise ValueError(f"Target symbol not found after universe update: {symbol}")
    return matches.iloc[0]


def _build_output_row(
    universe_row: pd.Series,
    target_symbol: str,
    universe_action: str,
    status: str,
    price_status: str,
    price_rows: int,
    min_samples: int,
    blocking_reason: str,
    research_row: dict[str, object],
    rank: str,
    company_research_csv: Path | None,
    company_research_md: Path | None,
) -> dict[str, object]:
    return {
        "symbol": target_symbol,
        "company_name": universe_row.get("company_name", target_symbol),
        "sector": universe_row.get("sector", "UNKNOWN"),
        "market": universe_row.get("market", "UNKNOWN"),
        "code": universe_row.get("code", ""),
        "universe_action": universe_action,
        "analysis_status": status,
        "local_pipeline_ready": "YES" if status == "ANALYSIS_READY" else "NO",
        "price_data_status": price_status,
        "price_rows": price_rows,
        "min_samples_required": min_samples,
        "blocking_reason": blocking_reason,
        "company_research_rank": rank,
        "latest_price": research_row.get("latest_price", ""),
        "latest_price_date": research_row.get("latest_price_date", ""),
        "research_score": research_row.get("research_score", ""),
        "research_view": research_row.get("research_view", ""),
        "decision": research_row.get("decision", ""),
        "why_summary": research_row.get("why_summary", ""),
        "company_research_csv": str(company_research_csv) if company_research_csv else "",
        "company_research_md": str(company_research_md) if company_research_md else "",
        "order_status": "NO_ORDER",
        "external_api_requested": "NO",
        "broker_order_requested": "NO",
        "next_step": _next_step(status),
    }


def _next_step(status: str) -> str:
    if status == "ANALYSIS_READY":
        return "review company_research and today dashboard; do not place orders without manual gate"
    return "refresh market data with explicit approval or add manual price history, then rerun symbol analysis"


def _save_symbol_analysis(
    report: pd.DataFrame,
    reports_root: Path,
    symbol: str,
) -> tuple[Path, Path]:
    output_dir = reports_root / "symbol_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = symbol.replace(".", "_")
    csv_path = output_dir / f"symbol_analysis_{slug}.csv"
    markdown_path = output_dir / f"symbol_analysis_{slug}.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_markdown(report.iloc[0]), encoding="utf-8")
    return csv_path, markdown_path


def _save_symbol_batch_analysis(
    report: pd.DataFrame,
    reports_root: Path,
) -> tuple[Path, Path]:
    output_dir = reports_root / "symbol_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "symbol_analysis_batch.csv"
    markdown_path = output_dir / "symbol_analysis_batch.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown_path.write_text(_render_batch_markdown(report), encoding="utf-8")
    return csv_path, markdown_path


def _render_markdown(row: pd.Series) -> str:
    lines = [
        f"# Symbol Analysis - {row['symbol']}",
        "",
        "Local research intake only. This report does not place orders or call external APIs.",
        "",
        f"- Company: {row['company_name']}",
        f"- Status: {row['analysis_status']}",
        f"- Price data: {row['price_data_status']} ({row['price_rows']} rows)",
        f"- Research view: {row['research_view']}",
        f"- Decision: {row['decision']}",
        f"- Order status: {row['order_status']}",
        f"- External API requested: {row['external_api_requested']}",
        "",
    ]
    if row["blocking_reason"]:
        lines.extend(["## Blocker", "", str(row["blocking_reason"]), ""])
    if row["why_summary"]:
        lines.extend(["## Why", "", str(row["why_summary"]), ""])
    lines.extend(["## Next Step", "", str(row["next_step"]), ""])
    return "\n".join(lines)


def _render_batch_markdown(report: pd.DataFrame) -> str:
    lines = [
        "# Symbol Batch Analysis",
        "",
        "Local batch intake only. This report does not place orders or call external APIs.",
        "",
    ]
    if report.empty:
        lines.append("No symbols were provided.")
        return "\n".join(lines)
    for row in report.itertuples(index=False):
        lines.extend(
            [
                f"## {row.symbol} {row.company_name}",
                "",
                f"- Status: {row.analysis_status}",
                f"- Price data: {row.price_data_status} ({row.price_rows} rows)",
                f"- Order status: {row.order_status}",
                f"- Blocker: {row.blocking_reason}",
                "",
            ]
        )
    return "\n".join(lines)
