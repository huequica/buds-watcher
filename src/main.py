from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from applog import setup_logging
from device import DeviceMonitor
from mainwindow import MainWindow
from notify import OverlayNotification
from tray import TrayIcon


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # ウィンドウを閉じても常駐を続ける

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
    notification = OverlayNotification()

    tray = TrayIcon(main_window=window, device_monitor=device)
    tray.show()

    def on_left_disconnected() -> None:
        notification.show_message("INZONE Buds", "左のイヤホンが切断されました")

    def on_right_disconnected() -> None:
        notification.show_message("INZONE Buds", "右のイヤホンが切断されました")

    def on_left_connected() -> None:
        message = "左のイヤホンが接続されました"
        if device.left_battery is not None:
            message += f"\nバッテリー {device.left_battery}%"
        notification.show_message("INZONE Buds", message, OverlayNotification.ACCENT_CONNECTED)

    def on_right_connected() -> None:
        message = "右のイヤホンが接続されました"
        if device.right_battery is not None:
            message += f"\nバッテリー {device.right_battery}%"
        notification.show_message("INZONE Buds", message, OverlayNotification.ACCENT_CONNECTED)

    device.left_disconnected.connect(on_left_disconnected)
    device.right_disconnected.connect(on_right_disconnected)
    device.left_connected.connect(on_left_connected)
    device.right_connected.connect(on_right_connected)
    device.status_changed.connect(window.update_status)

    device.start()
    app.aboutToQuit.connect(device.stop)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
