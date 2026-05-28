from __future__ import annotations

import importlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def test_load_total_capital_returns_none_when_actual_config_is_missing() -> None:
    module = importlib.import_module("quantum_trainer.capital_config")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        path = Path(tmp_dir) / "configs" / "capital.actual.csv"

        assert module.load_total_capital_krw(path) is None


def test_load_total_capital_reads_positive_amount_from_actual_config() -> None:
    module = importlib.import_module("quantum_trainer.capital_config")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        path = Path(tmp_dir) / "configs" / "capital.actual.csv"
        path.parent.mkdir()
        path.write_text("total_capital_krw,notes\n3000000,first review capital\n", encoding="utf-8")

        assert module.load_total_capital_krw(path) == 3_000_000


def test_load_total_capital_rejects_non_positive_amount() -> None:
    module = importlib.import_module("quantum_trainer.capital_config")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        path = Path(tmp_dir) / "configs" / "capital.actual.csv"
        path.parent.mkdir()
        path.write_text("total_capital_krw,notes\n0,invalid\n", encoding="utf-8")

        try:
            module.load_total_capital_krw(path)
        except ValueError as exc:
            assert "total_capital_krw must be greater than 0" in str(exc)
        else:
            raise AssertionError("Expected ValueError for non-positive total capital.")
