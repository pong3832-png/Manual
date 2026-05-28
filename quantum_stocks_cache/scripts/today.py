from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.today_command import run_today_analysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="오늘 분석을 한 번에 실행합니다. 예: python .\\scripts\\today.py 삼성전자"
    )
    parser.add_argument(
        "stock",
        nargs="?",
        default=None,
        help="선택 입력. 종목명, 별칭, 6자리 코드, 또는 005930.KS 형식 심볼.",
    )
    parser.add_argument(
        "--dry-run",
        "--미리보기",
        action="store_true",
        help="실행하지 않고 어떤 단계가 돌지 미리 확인합니다.",
    )
    parser.add_argument(
        "--refresh-market-data",
        "--latest-price",
        "--최신가격",
        action="store_true",
        help="최신 가격을 외부에서 갱신합니다. 이 옵션은 외부 데이터 호출을 합니다.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_today_analysis(
            project_root=PROJECT_ROOT,
            stock=args.stock,
            refresh_market_data=args.refresh_market_data,
            dry_run=args.dry_run,
        )
        for line in output.lines:
            print(line)
        logger.info("Today analysis complete.")
        return 0
    except Exception as exc:
        logger.exception("Today analysis failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
