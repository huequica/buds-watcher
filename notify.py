"""
OS標準の通知センターを使わない、独自の常時最前面オーバーレイ通知。

狙い:
  - Windowsの通知(アクションセンター)は全画面ゲーム中に隠れることがあるため使わない
  - 自前のフレームレス・常時最前面ウィンドウを画面隅に出す

既知の制約(正直に書いておく):
  - Windowsの「排他的フルスクリーン」モードのゲームの上には、OSレベルの制約により
    通常のトップモストウィンドウでは表示されないことがある
    (多くの現代のゲームは「ボーダレス/フルスクリーン最適化」で動くため、その場合は問題なく表示される)
  - Linux/WaylandのKDEでは、通常のQt「常に最前面」フラグだけだと
    コンポジタの設定によって挙動が変わることがある。X11セッションなら安定して動作する。
    より強固にしたい場合は将来的に layer-shell 系の統合を検討する。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import QWidget, QApplication


class OverlayNotification(QWidget):
    DISPLAY_MS = 4000
    FADE_MS = 250
    WIDTH = 340
    HEIGHT = 84
    MARGIN = 24

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.X11BypassWindowManagerHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(self.WIDTH, self.HEIGHT)

        self._title = ""
        self._message = ""

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

    def show_message(self, title: str, message: str) -> None:
        self._title = title
        self._message = message
        self._move_to_corner()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self._fade_anim.stop()
        self._fade_anim.setDuration(self.FADE_MS)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

        self._hide_timer.start(self.DISPLAY_MS)
        self.update()

    def _fade_out(self) -> None:
        self._fade_anim.stop()
        self._fade_anim.setDuration(self.FADE_MS)
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()

    def _move_to_corner(self) -> None:
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None
        if geo is None:
            self.move(QPoint(100, 100))
            return
        x = geo.right() - self.WIDTH - self.MARGIN
        y = geo.top() + self.MARGIN
        self.move(QPoint(x, y))

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(24, 24, 28, 235)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(self.rect(), 14, 14)

        accent = QColor(220, 60, 60)
        painter.setBrush(accent)
        painter.drawRoundedRect(0, 0, 6, self.height(), 3, 3)

        painter.setPen(QColor(255, 255, 255))
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(24, 32, self._title)

        msg_font = QFont()
        msg_font.setPointSize(9)
        painter.setFont(msg_font)
        painter.setPen(QColor(210, 210, 210))
        painter.drawText(24, 56, self._message)
