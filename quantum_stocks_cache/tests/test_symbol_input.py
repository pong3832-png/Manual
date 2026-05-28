from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.symbol_input import resolve_stock_input, search_stock_inputs


def test_resolve_stock_input_accepts_korean_common_company_name() -> None:
    resolved = resolve_stock_input("삼성전자")

    assert resolved.symbol == "005930.KS"
    assert resolved.code == "005930"
    assert resolved.company_name == "삼성전자"
    assert resolved.market == "KOSPI"
    assert resolved.sector == "반도체"
    assert resolved.source == "alias"


def test_resolve_stock_input_accepts_common_short_alias() -> None:
    resolved = resolve_stock_input("현대차")

    assert resolved.symbol == "005380.KS"
    assert resolved.company_name == "현대차"
    assert resolved.market == "KOSPI"


def test_resolve_stock_input_accepts_six_digit_code_without_company_name() -> None:
    resolved = resolve_stock_input("005930")

    assert resolved.symbol == "005930.KS"
    assert resolved.code == "005930"
    assert resolved.company_name == "005930"
    assert resolved.market == "KOSPI"
    assert resolved.source == "code"


def test_resolve_stock_input_accepts_existing_symbol() -> None:
    resolved = resolve_stock_input("091990.KQ")

    assert resolved.symbol == "091990.KQ"
    assert resolved.code == "091990"
    assert resolved.company_name == "091990.KQ"
    assert resolved.market == "KOSDAQ"
    assert resolved.source == "symbol"


def test_resolve_stock_input_uses_existing_universe_company_name() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        universe_csv = Path(tmp_dir) / "research_universe.actual.csv"
        pd.DataFrame(
            [
                {
                    "symbol": "006800.KS",
                    "company_name": "미래에셋증권",
                    "sector": "증권",
                    "market": "KOSPI",
                    "code": "006800",
                }
            ]
        ).to_csv(universe_csv, index=False)

        resolved = resolve_stock_input("미래에셋증권", universe_csv=universe_csv)

        assert resolved.symbol == "006800.KS"
        assert resolved.company_name == "미래에셋증권"
        assert resolved.sector == "증권"
        assert resolved.source == "universe"


def test_resolve_stock_input_accepts_korean_alias_for_actual_universe_name() -> None:
    resolved = resolve_stock_input("삼성바이오로직스")

    assert resolved.symbol == "207940.KS"
    assert resolved.company_name == "삼성바이오로직스"
    assert resolved.source == "alias"


def test_search_stock_inputs_returns_candidates_from_name_without_code() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        universe_csv = Path(tmp_dir) / "research_universe.actual.csv"
        pd.DataFrame(
            [
                {
                    "symbol": "373220.KS",
                    "company_name": "LG Energy Solution",
                    "sector": "Battery",
                    "market": "KOSPI",
                    "code": "373220",
                },
                {
                    "symbol": "051910.KS",
                    "company_name": "LG Chem",
                    "sector": "Chemicals",
                    "market": "KOSPI",
                    "code": "051910",
                },
            ]
        ).to_csv(universe_csv, index=False)

        candidates = search_stock_inputs("에너지", universe_csv=universe_csv)

        assert candidates[0].symbol == "373220.KS"
        assert candidates[0].company_name == "LG에너지솔루션"
        assert candidates[0].code == "373220"


def test_resolve_stock_input_rejects_unknown_name_without_external_lookup() -> None:
    with pytest.raises(ValueError, match="6자리 종목코드"):
        resolve_stock_input("없는회사")
