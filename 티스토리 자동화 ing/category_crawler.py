from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ.setdefault("PYTHONPATH", str(SRC_DIR))
os.environ.setdefault("COUPANG_DEBUGGER_ADDRESS", "127.0.0.1:9222")

from tistory_automation.pipeline.category_crawler import main


def prompt_target_count(default_count: int = 50) -> int:
    raw = input(f"총 몇 건 크롤링할까요? [기본 {default_count}]: ").strip()
    if not raw:
        return default_count
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    print(f"잘못된 입력이라 기본값 {default_count}건으로 진행합니다.")
    return default_count


if __name__ == "__main__":
    main(target_count=prompt_target_count())
