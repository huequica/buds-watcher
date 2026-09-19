from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("INZONE Buds Monitor")
        self.resize(320, 160)

        layout = QVBoxLayout(self)

        self._left_label = QLabel("左: 接続中")
        self._right_label = QLabel("右: 接続中")

        for label in (self._left_label, self._right_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = label.font()
            font.setPointSize(14)
            label.setFont(font)

        layout.addWidget(self._left_label)
        layout.addWidget(self._right_label)

        note = QLabel(
            "※現在はプロトコル未実装のため、実際のイヤホン状態は反映されません。\n"
            "トレイアイコンの右クリックメニューからテスト通知を試せます。"
        )
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)

    def update_status(self, left_ok: bool, right_ok: bool) -> None:
        self._left_label.setText(f"左: {'接続中' if left_ok else '切断'}")
        self._left_label.setStyleSheet("color: %s;" % ("green" if left_ok else "red"))
        self._right_label.setText(f"右: {'接続中' if right_ok else '切断'}")
        self._right_label.setStyleSheet("color: %s;" % ("green" if right_ok else "red"))

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # ウィンドウを閉じてもアプリ自体は常駐し続ける(トレイに残る)
        event.ignore()
        self.hide()
