from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)


def append_ledger_entry(
    ledger_path: Path | str,
    row: Dict[str, object],
) -> Path:
    try:
        path = Path(ledger_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        new_row = pd.DataFrame([row])
        if path.exists():
            existing = pd.read_csv(path)
            output = pd.concat([existing, new_row], ignore_index=True)
        else:
            output = new_row
        output.to_csv(path, index=False, encoding="utf-8-sig")
        return path
    except Exception as exc:
        logger.exception("Research ledger append failed: %s", exc)
        raise
