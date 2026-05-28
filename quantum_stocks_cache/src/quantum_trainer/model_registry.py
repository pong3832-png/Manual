from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Sequence

logger = logging.getLogger(__name__)


def config_hash(config_text: str) -> str:
    return hashlib.sha256(config_text.encode("utf-8")).hexdigest()


def register_model_run(
    registry_dir: Path | str,
    run_id: str,
    strategy_name: str,
    config_text: str,
    symbols: Sequence[str],
    artifact_paths: Dict[str, Path],
    statuses: Dict[str, str],
) -> Path:
    try:
        output_dir = Path(registry_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{run_id}.json"
        payload = {
            "run_id": run_id,
            "strategy_name": strategy_name,
            "config_hash": config_hash(config_text),
            "symbols": list(symbols),
            "artifact_paths": {key: str(value) for key, value in artifact_paths.items()},
            "statuses": statuses,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except Exception as exc:
        logger.exception("Model registry write failed: %s", exc)
        raise
