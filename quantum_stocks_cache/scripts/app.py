from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.local_app import run_local_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="퀀트 트레이너 로컬 웹앱을 실행합니다.")
    parser.add_argument("--host", default="127.0.0.1", help="로컬 웹앱 host.")
    parser.add_argument("--port", type=int, default=8765, help="로컬 웹앱 port.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    url = f"http://{args.host}:{args.port}"
    print("퀀트 트레이너 로컬 웹앱")
    print(f"주소: {url}")
    print("주문 실행: 안함")
    print("최신 가격 갱신 체크박스는 외부 데이터 호출입니다.")
    logger.info("Starting local app at %s", url)
    run_local_app(project_root=PROJECT_ROOT, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
