"""
アプリ全体のファイルログ設定。

`--windowed`(コンソール無し)でビルドしているため、hidapiの読み込み失敗や
デバイス列挙結果などが完全に無音で失われる。実行ファイルの隣に
`buds-watcher.log` を書き出し、後から調査できるようにする。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def log_file_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        # 開発時(src/main.py を直接実行): プロジェクトルートに出す
        base = Path(__file__).resolve().parent.parent
    return base / "buds-watcher.log"


def setup_logging() -> None:
    logging.basicConfig(
        filename=str(log_file_path()),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        # PySide6等が先にrootロガーにハンドラを付けていた場合でも、
        # 必ずこのファイルハンドラで上書き設定する。
        force=True,
    )
