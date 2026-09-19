from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("INZONE Buds Monitor")
        self.resize(320, 160)

        self._left_ok = True
        self._right_ok = True
        self._left_battery: int | None = None
        self._right_battery: int | None = None

        layout = QVBoxLayout(self)

        self._left_label = QLabel()
        self._right_label = QLabel()

        for label in (self._left_label, self._right_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = label.font()
            font.setPointSize(14)
            label.setFont(font)

        layout.addWidget(self._left_label)
        layout.addWidget(self._right_label)

        self._render()

    def update_status(self, left_ok: bool, right_ok: bool) -> None:
        self._left_ok = left_ok
        self._right_ok = right_ok
        self._render()

    def update_battery(self, left_battery: int, right_battery: int) -> None:
        # デバイス側は不明値を -1 で送ってくる(device.py の BATTERY_UNKNOWN)。
        self._left_battery = left_battery if left_battery >= 0 else None
        self._right_battery = right_battery if right_battery >= 0 else None
        self._render()

    def _render(self) -> None:
        self._left_label.setText(self._format_line("左", self._left_ok, self._left_battery))
        self._left_label.setStyleSheet("color: %s;" % ("green" if self._left_ok else "red"))
        self._right_label.setText(self._format_line("右", self._right_ok, self._right_battery))
        self._right_label.setStyleSheet("color: %s;" % ("green" if self._right_ok else "red"))

    @staticmethod
    def _format_line(side: str, connected: bool, battery: int | None) -> str:
        status = "接続中" if connected else "切断"
        if connected and battery is not None:
            return f"{side}: {status} ({battery}%)"
        return f"{side}: {status}"

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # ウィンドウを閉じてもアプリ自体は常駐し続ける(トレイに残る)
        event.ignore()
        self.hide()
