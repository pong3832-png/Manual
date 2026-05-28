from __future__ import annotations

import logging
from pathlib import Path
from shutil import copy2

logger = logging.getLogger(__name__)


def copy_artifact(source: Path | str, destination: Path | str) -> Path:
    try:
        src = Path(source).resolve()
        dst = Path(destination).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        copy2(src, dst)
        return dst
    except Exception as exc:
        logger.exception("Artifact copy failed: %s", exc)
        raise
