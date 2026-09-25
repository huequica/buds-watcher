"""
Wayland の wlr-layer-shell プロトコルで画面端に固定表示するオーバーレイ通知。

QtWidgetsの通常ウィンドウはWaylandではクライアント側から絶対位置を指定できず
コンポジタ任せの位置(だいたい中央)に出てしまう(notify.py参照)。KDEの
layer-shell-qt が提供する公式QMLモジュール `org.kde.layershell` を使うと、
layer-shellサーフェスとして画面端にアンカーできる。

`org.kde.layershell` はシステムにインストールされている前提(Linux固有・
Wayland+wlr-layer-shell対応コンポジタ限定)。無い/読み込めない環境では
インポートまたはQMLロードが失敗するので、呼び出し側でフォールバックすること。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlApplicationEngine

_QML_PATH = Path(__file__).resolve().parent / "qml" / "overlay_notification.qml"


class LayerShellOverlayNotification:
    """notify.OverlayNotification と同じインターフェースを持つlayer-shell版。"""

    def __init__(self) -> None:
        self._engine = QQmlApplicationEngine()
        self._engine.load(str(_QML_PATH))
        if not self._engine.rootObjects():
            raise RuntimeError(f"failed to load {_QML_PATH}")
        self._window = self._engine.rootObjects()[0]
        self._seq = 0

    def show_message(self, title: str, message: str, accent: QColor) -> None:
        self._seq += 1
        self._window.setProperty("titleText", title)
        self._window.setProperty("messageText", message)
        self._window.setProperty("accentColor", accent)
        self._window.setProperty("messageSeq", self._seq)
