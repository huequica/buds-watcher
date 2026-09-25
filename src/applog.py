from __future__ import annotations

import logging
import sys
from pathlib import Path


def log_file_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "buds-watcher.log"


def setup_logging(enabled: bool = True) -> None:
    if not enabled:
        # ファイルハンドラを外し、ログはほぼ出力しない(設定でオフにされた場合)。
        logging.basicConfig(level=logging.CRITICAL + 1, force=True)
        return
    logging.basicConfig(
        filename=str(log_file_path()),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        # PySide6等が先にrootロガーにハンドラを付けていた場合でも、
        # 必ずこのファイルハンドラで上書き設定する。
        force=True,
    )
