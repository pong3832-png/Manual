from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResearchUniverseResult:
    output_csv: Path
    row_count: int
    universe: pd.DataFrame


@dataclass(frozen=True)
class AddResearchSymbolResult:
    output_csv: Path
    row_count: int
    action: str
    symbol: str
    universe: pd.DataFrame


@dataclass(frozen=True)
class AddResearchSymbolsResult:
    output_csv: Path
    row_count: int
    added_count: int
    updated_count: int
    unchanged_count: int
    symbols: list[str]
    actions: pd.DataFrame
    universe: pd.DataFrame


def build_research_universe(
    source_csv: Path | str,
    output_csv: Path | str,
) -> ResearchUniverseResult:
    source_path = Path(source_csv).resolve()
    output_path = Path(output_csv).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Universe source CSV not found: {source_path}")

    source = pd.read_csv(source_path, dtype=str).fillna("")
    universe = normalize_research_universe(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    universe.to_csv(output_path, index=False, encoding="utf-8-sig")
    return ResearchUniverseResult(
        output_csv=output_path,
        row_count=len(universe),
        universe=universe,
    )


def merge_research_universe(
    source_csvs: Sequence[Path | str],
    output_csv: Path | str,
    limit: int | None = None,
) -> ResearchUniverseResult:
    if not source_csvs:
        raise ValueError("source_csvs must not be empty.")
    frames: list[pd.DataFrame] = []
    for source_csv in source_csvs:
        source_path = Path(source_csv).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Universe source CSV not found: {source_path}")
        source = pd.read_csv(source_path, dtype=str).fillna("")
        frames.append(normalize_research_universe(source))

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.drop_duplicates(subset=["symbol"], keep="first").reset_index(drop=True)
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be greater than 0 when provided.")
        merged = merged.head(limit).copy()

    output_path = Path(output_csv).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False, encoding="utf-8-sig")
    return ResearchUniverseResult(
        output_csv=output_path,
        row_count=len(merged),
        universe=merged,
    )


def add_research_symbol(
    universe_csv: Path | str,
    output_csv: Path | str,
    code: str | None = None,
    symbol: str | None = None,
    company_name: str = "",
    market: str = "KOSPI",
    sector: str = "UNKNOWN",
    replace: bool = False,
) -> AddResearchSymbolResult:
    universe_path = Path(universe_csv).resolve()
    output_path = Path(output_csv).resolve()
    if not universe_path.exists():
        raise FileNotFoundError(f"Research universe CSV not found: {universe_path}")
    if not code and not symbol:
        raise ValueError("Either code or symbol must be provided.")

    existing = pd.read_csv(universe_path, dtype=str).fillna("")
    existing = normalize_research_universe(existing)
    raw_row = {
        "company_name": company_name,
        "market": market,
        "sector": sector,
    }
    if symbol:
        raw_row["symbol"] = symbol
    else:
        raw_row["code"] = code or ""
    new_row = normalize_research_universe(pd.DataFrame([raw_row])).iloc[0]

    new_symbol = str(new_row["symbol"])
    matched = existing["symbol"] == new_symbol
    if matched.any():
        if replace:
            for column in ["company_name", "sector", "market", "code"]:
                existing.loc[matched, column] = str(new_row[column])
            action = "UPDATED"
        else:
            action = "UNCHANGED_EXISTING"
        universe = existing
    else:
        universe = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
        action = "ADDED"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    universe.to_csv(output_path, index=False, encoding="utf-8-sig")
    return AddResearchSymbolResult(
        output_csv=output_path,
        row_count=len(universe),
        action=action,
        symbol=new_symbol,
        universe=universe,
    )


def add_research_symbols_from_csv(
    universe_csv: Path | str,
    symbols_csv: Path | str,
    output_csv: Path | str,
    replace: bool = False,
) -> AddResearchSymbolsResult:
    universe_path = Path(universe_csv).resolve()
    symbols_path = Path(symbols_csv).resolve()
    output_path = Path(output_csv).resolve()
    if not universe_path.exists():
        raise FileNotFoundError(f"Research universe CSV not found: {universe_path}")
    if not symbols_path.exists():
        raise FileNotFoundError(f"Research symbols CSV not found: {symbols_path}")

    existing = pd.read_csv(universe_path, dtype=str).fillna("")
    existing = normalize_research_universe(existing)
    source = pd.read_csv(symbols_path, dtype=str).fillna("")
    additions = normalize_research_universe(source)

    action_rows: list[dict[str, str]] = []
    for new_row in additions.itertuples(index=False):
        new_symbol = str(new_row.symbol)
        matched = existing["symbol"] == new_symbol
        if matched.any():
            if replace:
                for column in ["company_name", "sector", "market", "code"]:
                    existing.loc[matched, column] = str(getattr(new_row, column))
                action = "UPDATED"
            else:
                action = "UNCHANGED_EXISTING"
        else:
            existing = pd.concat([existing, pd.DataFrame([new_row._asdict()])], ignore_index=True)
            action = "ADDED"
        action_rows.append(
            {
                "symbol": new_symbol,
                "company_name": str(new_row.company_name),
                "sector": str(new_row.sector),
                "market": str(new_row.market),
                "code": str(new_row.code),
                "action": action,
            }
        )

    actions = pd.DataFrame(action_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing.to_csv(output_path, index=False, encoding="utf-8-sig")
    return AddResearchSymbolsResult(
        output_csv=output_path,
        row_count=len(existing),
        added_count=int((actions["action"] == "ADDED").sum()) if not actions.empty else 0,
        updated_count=int((actions["action"] == "UPDATED").sum()) if not actions.empty else 0,
        unchanged_count=int((actions["action"] == "UNCHANGED_EXISTING").sum()) if not actions.empty else 0,
        symbols=actions["symbol"].tolist() if not actions.empty else [],
        actions=actions,
        universe=existing,
    )


def normalize_research_universe(source: pd.DataFrame) -> pd.DataFrame:
    if "symbol" not in source.columns and "code" not in source.columns:
        raise ValueError("Universe CSV must include either 'symbol' or 'code'.")

    normalized = source.copy()
    normalized["company_name"] = (
        normalized["company_name"].astype(str).str.strip()
        if "company_name" in normalized.columns
        else ""
    )
    normalized["sector"] = (
        normalized["sector"].astype(str).str.strip()
        if "sector" in normalized.columns
        else "UNKNOWN"
    )
    normalized["market"] = (
        normalized["market"].astype(str).str.strip().str.upper()
        if "market" in normalized.columns
        else "UNKNOWN"
    )

    if "symbol" in normalized.columns:
        normalized["symbol"] = normalized["symbol"].astype(str).str.strip()
        normalized["code"] = normalized["symbol"].map(_code_from_symbol)
    else:
        normalized["code"] = normalized["code"].astype(str).map(_normalize_code)
        normalized["symbol"] = [
            _symbol_from_code_and_market(code=code, market=market)
            for code, market in zip(normalized["code"], normalized["market"])
        ]

    if (normalized["symbol"] == "").any():
        raise ValueError("Universe CSV contains rows with empty symbols.")
    if normalized["symbol"].duplicated().any():
        duplicates = normalized.loc[normalized["symbol"].duplicated(), "symbol"].tolist()
        raise ValueError(f"Universe CSV contains duplicate symbols: {duplicates}")

    normalized.loc[normalized["company_name"] == "", "company_name"] = normalized["symbol"]
    normalized.loc[normalized["sector"] == "", "sector"] = "UNKNOWN"
    normalized.loc[normalized["market"] == "", "market"] = "UNKNOWN"

    return normalized.loc[:, ["symbol", "company_name", "sector", "market", "code"]]


def _normalize_code(value: object) -> str:
    text = str(value).strip()
    if text.endswith(".KS") or text.endswith(".KQ"):
        text = text.split(".", maxsplit=1)[0]
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(6)
    return text


def _code_from_symbol(symbol: object) -> str:
    return _normalize_code(str(symbol).strip())


def _symbol_from_code_and_market(code: str, market: str) -> str:
    normalized_code = _normalize_code(code)
    normalized_market = str(market).strip().upper()
    if normalized_code.endswith(".KS") or normalized_code.endswith(".KQ"):
        return normalized_code
    if normalized_market in {"KOSDAQ", "KQ"}:
        return f"{normalized_code}.KQ"
    return f"{normalized_code}.KS"
