from __future__ import annotations

import sys
import tomllib
from pathlib import Path

DEFAULT_APP_NAME = "buds-watcher"


def _frozen_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def _pyproject_path() -> Path:
    return _frozen_base() / "pyproject.toml"


def _load_app_name() -> str:
    try:
        with _pyproject_path().open("rb") as f:
            data = tomllib.load(f)
        return data["project"]["name"]
    except Exception:
        return DEFAULT_APP_NAME


def _icon_path() -> Path:
    return _frozen_base() / "icons" / "app.png"


APP_NAME = _load_app_name()
ICON_PNG_PATH = _icon_path()
