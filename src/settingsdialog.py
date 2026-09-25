from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from settings import Settings

_AUTO_MONITOR_LABEL = "自動(アクティブな画面)"


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("設定")

        self._dump_log_checkbox = QCheckBox("ログファイルを出力する")
        self._dump_log_checkbox.setChecked(settings.dump_log_file)

        self._monitor_combo = QComboBox()
        self._monitor_combo.addItem(_AUTO_MONITOR_LABEL, None)
        for screen in QGuiApplication.screens():
            name = screen.name()
            model = screen.model()
            label = f"{name} ({model})" if model else name
            self._monitor_combo.addItem(label, name)
        index = self._monitor_combo.findData(settings.monitor_name)
        self._monitor_combo.setCurrentIndex(index if index >= 0 else 0)

        form = QFormLayout()
        form.addRow(self._dump_log_checkbox)
        form.addRow("通知を表示するモニター", self._monitor_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        note = QLabel("※ Wayland環境でのモニター指定は環境によって反映されない場合があります。")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def result_settings(self) -> Settings:
        return Settings(
            dump_log_file=self._dump_log_checkbox.isChecked(),
            monitor_name=self._monitor_combo.currentData(),
        )
