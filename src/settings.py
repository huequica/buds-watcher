from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from applog import log_file_path

logger = logging.getLogger(__name__)


def settings_file_path() -> Path:
    return log_file_path().parent / "buds-watcher.yaml"


@dataclass
class Settings:
    dump_log_file: bool = False
    monitor_name: str | None = None

    @classmethod
    def load(cls) -> Settings:
        path = settings_file_path()
        if not path.exists():
            return cls()
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
            with path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        except Exception:
            logger.exception("failed to save settings to %s", path)
