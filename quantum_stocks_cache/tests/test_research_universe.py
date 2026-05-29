from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.research_universe import (
    add_research_symbol,
    add_research_symbols_from_csv,
    build_research_universe,
    merge_research_universe,
    normalize_full_krx_universe,
)


def test_build_research_universe_normalizes_codes_and_markets() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        source_csv = root / "universe_seed.csv"
        output_csv = root / "research_universe.actual.csv"
        source_csv.write_text(
            "\n".join(
                [
                    "code,company_name,market,sector",
                    "005930,Samsung Electronics,KOSPI,Semiconductors",
                    "035420,NAVER,KOSPI,Internet",
                    "035720,Kakao,KOSPI,Internet",
                    "091990,Celltrion Healthcare,KOSDAQ,Biotech",
                ]
            ),
            encoding="utf-8",
        )

        result = build_research_universe(source_csv=source_csv, output_csv=output_csv)

        assert result.output_csv == output_csv
        assert result.row_count == 4
        universe = pd.read_csv(output_csv, dtype=str)
        assert list(universe.columns) == ["symbol", "company_name", "sector", "market", "code"]
        assert universe["symbol"].tolist() == [
            "005930.KS",
            "035420.KS",
            "035720.KS",
            "091990.KQ",
        ]


def test_build_research_universe_accepts_existing_symbol_column() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        source_csv = root / "universe_seed.csv"
        output_csv = root / "research_universe.actual.csv"
        source_csv.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector",
                    "000660.KS,SK hynix,Semiconductors",
                    "005380.KS,Hyundai Motor,Autos",
                ]
            ),
            encoding="utf-8",
        )

        result = build_research_universe(source_csv=source_csv, output_csv=output_csv)

        universe = pd.read_csv(output_csv, dtype=str)
        assert result.row_count == 2
        assert universe.loc[0, "symbol"] == "000660.KS"
        assert universe.loc[0, "market"] == "UNKNOWN"
        assert universe.loc[0, "code"] == "000660"


def test_merge_research_universe_deduplicates_with_first_seed_priority_and_limit() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        first = root / "first.csv"
        second = root / "second.csv"
        output_csv = root / "research_universe.actual.csv"
        first.write_text(
            "\n".join(
                [
                    "code,company_name,market,sector",
                    "005930,Samsung Electronics,KOSPI,Semiconductors",
                    "000660,SK hynix,KOSPI,Semiconductors",
                ]
            ),
            encoding="utf-8",
        )
        second.write_text(
            "\n".join(
                [
                    "code,company_name,market,sector",
                    "005930,Duplicate Samsung,KOSPI,Duplicate",
                    "091990,Celltrion Healthcare,KOSDAQ,Biotech",
                ]
            ),
            encoding="utf-8",
        )

        result = merge_research_universe(
            source_csvs=[first, second],
            output_csv=output_csv,
            limit=3,
        )

        universe = pd.read_csv(output_csv, dtype=str)
        assert result.row_count == 3
        assert universe["symbol"].tolist() == ["005930.KS", "000660.KS", "091990.KQ"]
        assert universe.loc[0, "company_name"] == "Samsung Electronics"
        assert universe.loc[0, "sector"] == "Semiconductors"


def test_add_research_symbol_appends_normalized_company_without_reordering_existing_universe() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "research_universe.actual.csv"
        universe_csv.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector,market,code",
                    "005930.KS,Samsung Electronics,Semiconductors,KOSPI,005930",
                    "003550.KS,LG Corp,Holding,KOSPI,003550",
                ]
            ),
            encoding="utf-8",
        )

        result = add_research_symbol(
            universe_csv=universe_csv,
            output_csv=universe_csv,
            code="006800",
            company_name="Mirae Asset Securities",
            market="KOSPI",
            sector="Securities",
        )

        assert result.output_csv == universe_csv
        assert result.row_count == 3
        assert result.action == "ADDED"
        written = pd.read_csv(universe_csv, dtype=str)
        assert written["symbol"].tolist() == ["005930.KS", "003550.KS", "006800.KS"]
        assert written.loc[2, "company_name"] == "Mirae Asset Securities"
        assert written.loc[2, "sector"] == "Securities"


def test_add_research_symbol_can_update_existing_row_without_duplication() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "research_universe.actual.csv"
        universe_csv.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector,market,code",
                    "006800.KS,Old Name,UNKNOWN,KOSPI,006800",
                ]
            ),
            encoding="utf-8",
        )

        result = add_research_symbol(
            universe_csv=universe_csv,
            output_csv=universe_csv,
            symbol="006800.KS",
            company_name="Mirae Asset Securities",
            sector="Securities",
            replace=True,
        )

        assert result.action == "UPDATED"
        written = pd.read_csv(universe_csv, dtype=str)
        assert len(written) == 1
        assert written.loc[0, "symbol"] == "006800.KS"
        assert written.loc[0, "company_name"] == "Mirae Asset Securities"
        assert written.loc[0, "sector"] == "Securities"


def test_add_research_symbols_from_csv_appends_multiple_without_reordering_existing_universe() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "research_universe.actual.csv"
        batch_csv = root / "symbols.csv"
        universe_csv.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector,market,code",
                    "005930.KS,Samsung Electronics,Semiconductors,KOSPI,005930",
                    "003550.KS,LG Corp,Holding,KOSPI,003550",
                ]
            ),
            encoding="utf-8",
        )
        batch_csv.write_text(
            "\n".join(
                [
                    "code,company_name,market,sector",
                    "006800,Mirae Asset Securities,KOSPI,Securities",
                    "091990,Celltrion Healthcare,KOSDAQ,Biotech",
                    "003550,LG Corp Updated,KOSPI,Holding",
                ]
            ),
            encoding="utf-8",
        )

        result = add_research_symbols_from_csv(
            universe_csv=universe_csv,
            symbols_csv=batch_csv,
            output_csv=universe_csv,
        )

        written = pd.read_csv(universe_csv, dtype=str)
        assert result.row_count == 4
        assert result.added_count == 2
        assert result.updated_count == 0
        assert result.unchanged_count == 1
        assert result.actions["action"].tolist() == ["ADDED", "ADDED", "UNCHANGED_EXISTING"]
        assert written["symbol"].tolist() == ["005930.KS", "003550.KS", "006800.KS", "091990.KQ"]
        assert written.loc[3, "market"] == "KOSDAQ"


def test_add_research_symbols_from_csv_updates_existing_rows_when_replace_enabled() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "research_universe.actual.csv"
        batch_csv = root / "symbols.csv"
        universe_csv.write_text(
            "\n".join(
                [
                    "symbol,company_name,sector,market,code",
                    "003550.KS,Old Name,UNKNOWN,KOSPI,003550",
                ]
            ),
            encoding="utf-8",
        )
        batch_csv.write_text(
            "\n".join(
                [
                    "code,company_name,market,sector",
                    "003550,LG Corp,KOSPI,Holding",
                ]
            ),
            encoding="utf-8",
        )

        result = add_research_symbols_from_csv(
            universe_csv=universe_csv,
            symbols_csv=batch_csv,
            output_csv=universe_csv,
            replace=True,
        )

        written = pd.read_csv(universe_csv, dtype=str)
        assert result.row_count == 1
        assert result.added_count == 0
        assert result.updated_count == 1
        assert result.actions.loc[0, "action"] == "UPDATED"
        assert written.loc[0, "company_name"] == "LG Corp"
        assert written.loc[0, "sector"] == "Holding"


def test_normalize_full_krx_universe_keeps_all_security_types_from_krx_style_csv() -> None:
    source = pd.DataFrame(
        [
            {
                "단축코드": "005930",
                "한글 종목명": "삼성전자",
                "시장구분": "KOSPI",
                "업종명": "반도체",
                "증권구분": "주권",
                "주식종류": "보통주",
            },
            {
                "단축코드": "000545",
                "한글 종목명": "흥국화재2우B",
                "시장구분": "KOSPI",
                "업종명": "보험",
                "증권구분": "주권",
                "주식종류": "우선주",
            },
            {
                "단축코드": "305720",
                "한글 종목명": "TIGER 2차전지테마",
                "시장구분": "KOSPI",
                "업종명": "ETF",
                "증권구분": "ETF",
                "주식종류": "ETF",
            },
            {
                "단축코드": "456789",
                "한글 종목명": "테스트스팩",
                "시장구분": "KOSDAQ",
                "업종명": "금융",
                "증권구분": "SPAC",
                "주식종류": "보통주",
            },
        ]
    )

    universe = normalize_full_krx_universe(source)

    assert universe["symbol"].tolist() == ["005930.KS", "000545.KS", "305720.KS", "456789.KQ"]
    assert universe["company_name"].tolist() == ["삼성전자", "흥국화재2우B", "TIGER 2차전지테마", "테스트스팩"]
    assert universe["security_type"].tolist() == ["주권", "주권", "ETF", "SPAC"]
    assert universe["share_type"].tolist() == ["보통주", "우선주", "ETF", "보통주"]
    assert len(universe) == 4
