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

from PySide6.QtCore import Property, QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QApplication, QWidget


class OverlayNotification(QWidget):
    DISPLAY_MS = 4000
    FADE_MS = 250
    WIDTH = 340
    HEIGHT = 84
    MARGIN = 24

    ACCENT_DISCONNECTED = QColor(220, 60, 60)
    ACCENT_CONNECTED = QColor(70, 190, 120)

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(self.WIDTH, self.HEIGHT)

        self._title = ""
        self._message = ""
        self._accent = self.ACCENT_DISCONNECTED
        # Waylandではウィンドウ単位のopacity(setWindowOpacity)がQtのプラットフォーム
        # プラグインでサポートされていないため、フェードはウィンドウ透明度ではなく
        # 描画内容のアルファ値で自前で行う。
        self._content_opacity = 0.0

        self._fade_anim = QPropertyAnimation(self, b"contentOpacity")
        self._fade_anim.finished.connect(self._on_fade_finished)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

    def _get_content_opacity(self) -> float:
        return self._content_opacity

    def _set_content_opacity(self, value: float) -> None:
        self._content_opacity = value
        self.update()

    contentOpacity = Property(float, _get_content_opacity, _set_content_opacity)

    def show_message(self, title: str, message: str, accent: QColor | None = None) -> None:
        self._title = title
        self._message = message
        self._accent = accent if accent is not None else self.ACCENT_DISCONNECTED
        self._move_to_corner()
        self.contentOpacity = 0.0
        self.show()
        self.raise_()

        self._fade_anim.stop()
        self._fade_anim.setDuration(self.FADE_MS)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

        self._hide_timer.start(self.DISPLAY_MS)

    def _fade_out(self) -> None:
        self._fade_anim.stop()
        self._fade_anim.setDuration(self.FADE_MS)
        self._fade_anim.setStartValue(self._content_opacity)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        if self._content_opacity <= 0.0:
            self.hide()

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

        alpha = self._content_opacity

        bg = QColor(24, 24, 28, round(235 * alpha))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(self.rect(), 14, 14)

        accent = QColor(self._accent)
        accent.setAlpha(round(255 * alpha))
        painter.setBrush(accent)
        painter.drawRoundedRect(0, 0, 6, self.height(), 3, 3)

        painter.setPen(QColor(255, 255, 255, round(255 * alpha)))
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(24, 32, self._title)

        msg_font = QFont()
        msg_font.setPointSize(9)
        painter.setFont(msg_font)
        painter.setPen(QColor(210, 210, 210, round(255 * alpha)))
        line_height = 18
        for i, line in enumerate(self._message.split("\n")):
            painter.drawText(24, 56 + i * line_height, line)
