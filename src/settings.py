from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from applog import log_file_path

logger = logging.getLogger(__name__)


SETTINGS_FILE_NAME = "buds-watcher.yaml"


def _xdg_config_home() -> Path:
    # XDG Base Directory 仕様に従い、未設定または相対パスの場合は ~/.config を使う
    value = os.environ.get("XDG_CONFIG_HOME", "")
    if value and Path(value).is_absolute():
        return Path(value)
    return Path.home() / ".config"


def _legacy_settings_file_path() -> Path:
    return log_file_path().parent / SETTINGS_FILE_NAME


def settings_file_path() -> Path:
    if sys.platform.startswith("linux"):
        # nix store 等の読み取り専用領域に書き込まないよう XDG_CONFIG_HOME 配下に置く
        return _xdg_config_home() / "huequica" / "buds-watcher" / SETTINGS_FILE_NAME
    return _legacy_settings_file_path()


@dataclass
class Settings:
    dump_log_file: bool = False
    monitor_name: str | None = None

    @classmethod
    def load(cls) -> Settings:
        path = settings_file_path()
        if not path.exists():
            # 旧バージョンの保存場所に設定が残っていればそちらを読み込む
            legacy = _legacy_settings_file_path()
            if not legacy.exists():
                return cls()
            path = legacy
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(
                dump_log_file=bool(data.get("dumpLogFile", False)),
                monitor_name=data.get("monitorName"),
            )
        except Exception:
            logger.exception("failed to load settings from %s, using defaults", path)
            return cls()

    def save(self) -> None:
        data = {
            "dumpLogFile": self.dump_log_file,
            "monitorName": self.monitor_name,
        }
        path = settings_file_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        except Exception:
            logger.exception("failed to save settings to %s", path)
