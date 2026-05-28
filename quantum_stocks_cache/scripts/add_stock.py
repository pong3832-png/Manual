from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.research_universe import add_research_symbol
from quantum_trainer.symbol_input import resolve_stock_input

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="쉬운 종목 입력을 받아 로컬 분석 universe에 추가합니다. 예: 삼성전자, 현대차, 005930"
    )
    parser.add_argument("stock", help="종목명, 별칭, 6자리 코드, 또는 005930.KS 형식 심볼.")
    parser.add_argument(
        "--universe-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.actual.csv"),
        help="분석 universe CSV. 기본값은 configs/research_universe.actual.csv",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="출력 CSV. 생략하면 universe CSV를 그대로 갱신합니다.",
    )
    parser.add_argument("--replace", action="store_true", help="이미 있는 종목이면 이름/섹터를 갱신합니다.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        universe_csv = Path(args.universe_csv)
        output_csv = Path(args.output_csv) if args.output_csv else universe_csv
        resolved = resolve_stock_input(args.stock, universe_csv=universe_csv)
        result = add_research_symbol(
            universe_csv=universe_csv,
            output_csv=output_csv,
            code=resolved.code,
            company_name=resolved.company_name,
            market=resolved.market,
            sector=resolved.sector,
            replace=args.replace,
        )
        print(f"종목={resolved.company_name}")
        print(f"표준심볼={resolved.symbol}")
        print(f"처리결과={_action_korean(result.action)}")
        print(f"분석대상수={result.row_count}")
        print("외부조회=안함")
        print("주문실행=안함")
        logger.info("Easy stock add complete.")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.error("%s", exc)
        return 1


def _action_korean(action: str) -> str:
    return {
        "ADDED": "추가됨",
        "UPDATED": "갱신됨",
        "UNCHANGED_EXISTING": "이미 있음",
    }.get(action, action)


if __name__ == "__main__":
    raise SystemExit(main())
