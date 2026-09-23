from __future__ import annotations

import sys
import tomllib
from pathlib import Path

DEFAULT_APP_NAME = "buds-watcher"


def _pyproject_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "pyproject.toml"


def _load_app_name() -> str:
    try:
        with _pyproject_path().open("rb") as f:
            data = tomllib.load(f)
        return data["project"]["name"]
    except Exception:
        return DEFAULT_APP_NAME


APP_NAME = _load_app_name()
