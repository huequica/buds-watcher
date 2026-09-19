"""
システムトレイアイコンとその右クリックメニュー。

注意:
  - GNOME (標準設定) はシステムトレイ自体を廃止しているため、
    "AppIndicator and KStatusNotifierItem Support" 等の拡張機能を
    入れないとアイコンが表示されない。README にその旨を記載する。
  - KDE Plasma はKStatusNotifierItemを標準でサポートしているため問題なく動く。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


def make_status_icon(left_ok: bool, right_ok: bool) -> QIcon:
    """L/Rの状態に応じて色分けした簡易アイコンを動的に生成する。"""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)

    ok_color = QColor(70, 190, 120)
    ng_color = QColor(220, 60, 60)

    # 左半分・右半分の円でL/Rの状態を表現する
    painter.setBrush(ok_color if left_ok else ng_color)
    painter.drawPie(4, 4, size - 8, size - 8, 90 * 16, 180 * 16)

    painter.setBrush(ok_color if right_ok else ng_color)
    painter.drawPie(4, 4, size - 8, size - 8, -90 * 16, 180 * 16)

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, main_window, device_monitor, parent=None) -> None:
        super().__init__(parent)
        self._main_window = main_window
        self._device = device_monitor

        self.setIcon(make_status_icon(True, True))
        self.setToolTip("INZONE Buds Monitor")

        menu = QMenu()

        open_action = QAction("アプリケーション画面を開く", menu)
        open_action.triggered.connect(self._open_window)
        menu.addAction(open_action)

        menu.addSeparator()

        quit_action = QAction("アプリを終了する", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

        self._device.status_changed.connect(self._on_status_changed)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # ダブルクリックでも開けるようにしておく(右クリックメニューは別途表示される)
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_window()

    def _open_window(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _on_status_changed(self, left_ok: bool, right_ok: bool) -> None:
        self.setIcon(make_status_icon(left_ok, right_ok))
