from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.web_api import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FastAPI + React quant trainer app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host.")
    parser.add_argument("--port", type=int, default=8766, help="Port.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import uvicorn

        app = create_app(PROJECT_ROOT)
        url = f"http://{args.host}:{args.port}"
        _safe_print("퀀트 트레이너 FastAPI + React")
        _safe_print(f"주소: {url}")
        _safe_print("주문 실행: 안함")
        logger.info("Starting web app at %s", url)
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return 0
    except Exception as exc:
        logger.exception("Web app failed: %s", exc)
        return 1


def _safe_print(message: str) -> None:
    if sys.stdout is not None:
        print(message)


if __name__ == "__main__":
    raise SystemExit(main())
