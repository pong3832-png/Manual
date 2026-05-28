from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.scripts_api import run_alpha_research

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run alpha forecast and buy timing research.")
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
        help="Path to portfolio YAML config.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_alpha_research(Path(args.config))
        logger.info("Alpha research complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(output.report.to_string())
        return 0
    except Exception as exc:
        logger.exception("Alpha research failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
