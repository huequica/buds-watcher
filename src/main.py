from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from appinfo import ICON_PNG_PATH
from applog import setup_logging
from device import DeviceMonitor
from mainwindow import MainWindow
from notify import (
    ACCENT_CONNECTED,
    ACCENT_DISCONNECTED,
    ACCENT_WARNING,
    create_overlay_notification,
)
from settings import Settings
from tray import TrayIcon


def main() -> int:
    settings = Settings.load()
    setup_logging(settings.dump_log_file)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(ICON_PNG_PATH)))

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.warning(
            None,
            "システムトレイが見つかりません",
            "このデスクトップ環境ではシステムトレイが利用できないようです。\n"
            "GNOMEの場合は 'AppIndicator and KStatusNotifierItem Support' 拡張機能を\n"
            "インストールすると表示されるようになります。",
        )

    window = MainWindow()
    device = DeviceMonitor()
    notification = create_overlay_notification(settings.monitor_name)

    tray = TrayIcon(
        main_window=window, device_monitor=device, settings=settings, notification=notification
    )
    tray.show()

    def on_left_disconnected() -> None:
        notification.show_message(
            "INZONE Buds", "左のイヤホンが切断されました", ACCENT_DISCONNECTED
        )

    def on_right_disconnected() -> None:
        notification.show_message(
            "INZONE Buds", "右のイヤホンが切断されました", ACCENT_DISCONNECTED
        )

    def on_left_connected() -> None:
        message = "左のイヤホンが接続されました"
        if device.left_battery is not None:
            message += f"\nバッテリー {device.left_battery}%"
        notification.show_message("INZONE Buds", message, ACCENT_CONNECTED)

    def on_right_connected() -> None:
        message = "右のイヤホンが接続されました"
        if device.right_battery is not None:
            message += f"\nバッテリー {device.right_battery}%"
        notification.show_message("INZONE Buds", message, ACCENT_CONNECTED)

    # 起動直後の初回検出でドングルが刺さっていた場合は、通常の状態なので通知しない
    receiver_checked = False

    def on_receiver_presence_changed(present: bool) -> None:
        nonlocal receiver_checked
        first_check = not receiver_checked
        receiver_checked = True
        if present:
            if not first_check:
                notification.show_message(
                    "INZONE Buds", "ドングルが接続されました", ACCENT_CONNECTED
                )
            return
        notification.show_message("INZONE Buds", "ドングルが接続されていません", ACCENT_WARNING)

    device.receiver_presence_changed.connect(on_receiver_presence_changed)
    device.left_disconnected.connect(on_left_disconnected)
    device.right_disconnected.connect(on_right_disconnected)
    device.left_connected.connect(on_left_connected)
    device.right_connected.connect(on_right_connected)
    device.status_changed.connect(window.update_status)
    device.battery_changed.connect(window.update_battery)
    device.receiver_presence_changed.connect(window.update_receiver_presence)

    device.start()
    app.aboutToQuit.connect(device.stop)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
