"""
INZONE Buds の左右接続状態を監視するモジュール。

USBレシーバー(VID=0x054c, PID=0x0ec2)は標準のHIDインターフェースを持ち、
状態変化(切断/再接続)のたびに64バイトのHIDレポートをイベント駆動で送ってくる。
実機USBキャプチャ(capture_inzone.sh で取得、usbmon + tshark)を解析した結果、
以下のことが判明している:

- byte[8] == 0x12 かつ byte[9] == 0x01 のレポートが「左右接続状態」を示す
- byte[13] が左の接続状態(1=接続, 0=切断)
- byte[14] が右の接続状態(1=接続, 0=切断)

このレポートは定期ポーリングでは来ないため(内部イベント駆動)、バックグラウンド
スレッドで hidraw を blocking read し続け、レポートが来たらその都度状態を更新する。

このUSBインターフェースはHIDレポートディスクリプタ上、複数のトップレベル
コレクション(usage_page/usage)を持っている。Linuxではこれらが1つの
hidrawノードに統合されて見えるため vid/pid 指定でオープンすれば十分だったが、
Windowsではコレクションごとに別々のHIDデバイスパスとして列挙される
(参考: Issue #1)。vid/pidだけでオープンすると先頭に列挙された無関係な
コレクションを開いてしまい、目的のレポートが一切届かないことがあるため、
列挙して見つかった全パスをそれぞれ監視する。

HIDアクセスには `hidapi` パッケージ(importすると `hid` という名前で使う。
`hid` パッケージとは別物)を使う。以前は ctypes 経由でシステムのhidapi共有
ライブラリ/DLLを実行時に探して読み込む `hid` パッケージを使っていたが、
PyInstaller onefileビルドではその探索が失敗し(実行時展開先のディレクトリが
DLL検索パスに入らない)、Windows上でimport自体が失敗して検知が完全に
無音で機能しなくなっていた(Issue #1)。`hidapi` パッケージはCython製で
ネイティブライブラリを自身の共有ライブラリに静的にリンク/同梱しているため、
この問題が起きない。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, QTimer, Signal

if TYPE_CHECKING:
    # `hid`はtry/except配下でNoneにフォールバックしうる変数のため、
    # 型チェッカーからは型注釈に使えない(見えない)。型注釈専用に別名でimportする。
    import hid as hid_types

logger = logging.getLogger(__name__)

# `hid`(hidapiパッケージ)はここでは遅延importする: モジュール読み込み直後に
# importすると、main.py の setup_logging() より前に実行されてしまい、一番知りたい
# 「importできたか」のログがロギング設定前に失われるため。
hid = None  # type: ignore[assignment]
_hid_import_attempted = False


def _ensure_hid_imported() -> None:
    global hid, _hid_import_attempted
    if _hid_import_attempted:
        return
    _hid_import_attempted = True
    try:
        import hid as _hid_module
    except ImportError:  # hidapiがインストールされていない環境向けフォールバック
        logger.exception("failed to import `hid` module; device monitoring is disabled")
        return
    hid = _hid_module
    logger.info(
        "hidapi module loaded: %s (version %s)",
        getattr(hid, "__file__", "?"),
        hid.version_str(),
    )


SONY_VENDOR_ID = 0x054C
INZONE_BUDS_PRODUCT_ID = 0x0EC2

# 実機キャプチャ解析で判明したステータスレポートのフォーマット
STATUS_REPORT_CLASS = 0x12
STATUS_REPORT_TYPE = 0x01
LEFT_STATUS_OFFSET = 13
RIGHT_STATUS_OFFSET = 14
MIN_STATUS_REPORT_LEN = 15

READ_TIMEOUT_MS = 1000
RECONNECT_DELAY_MS = 3000
DISCOVERY_INTERVAL_MS = 3000


def _enumerate_receiver_paths() -> list[bytes]:
    """INZONE Budsレシーバーに属するHIDデバイスパスを重複無しで列挙する。"""
    _ensure_hid_imported()
    if hid is None:
        return []
    try:
        entries = hid.enumerate(SONY_VENDOR_ID, INZONE_BUDS_PRODUCT_ID)
    except Exception:
        logger.exception("hid.enumerate() failed")
        return []

    seen: set[bytes] = set()
    paths: list[bytes] = []
    for entry in entries:
        logger.debug("enumerated HID entry: %r", entry)
        path = entry.get("path")
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    logger.debug("enumerated %d unique receiver path(s): %r", len(paths), paths)
    return paths


class _ReceiverReaderThread(QThread):
    """HIDデバイスパスを1つ読み続け、状態レポートを検出したらemitするスレッド。"""

    status_report = Signal(bool, bool)  # (left_connected, right_connected)

    def __init__(self, path: bytes, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        if hid is None:
            return

        while not self._stop_requested:
            device = hid.device()
            try:
                device.open_path(self._path)
            except Exception:
                # レシーバーが抜かれた、権限不足など。少し待って再試行する。
                logger.exception("failed to open HID path %r", self._path)
                self.msleep(RECONNECT_DELAY_MS)
                continue

            logger.info("opened HID path %r", self._path)
            try:
                self._read_loop(device)
            finally:
                try:
                    device.close()
                except Exception:
                    pass

            if not self._stop_requested:
                self.msleep(RECONNECT_DELAY_MS)

    def _read_loop(self, device: "hid_types.device") -> None:
        while not self._stop_requested:
            try:
                data = device.read(64, timeout_ms=READ_TIMEOUT_MS)
            except Exception:
                # レシーバーが抜かれた等。外側のループで開き直しを試みる。
                logger.exception("read() failed on HID path %r", self._path)
                return

            if not data or len(data) < MIN_STATUS_REPORT_LEN:
                continue
            if data[8] != STATUS_REPORT_CLASS or data[9] != STATUS_REPORT_TYPE:
                logger.debug("unrelated report on %r: %r", self._path, data)
                continue

            left_connected = bool(data[LEFT_STATUS_OFFSET])
            right_connected = bool(data[RIGHT_STATUS_OFFSET])
            logger.info(
                "status report on %r: left=%s right=%s",
                self._path,
                left_connected,
                right_connected,
            )
            self.status_report.emit(left_connected, right_connected)


class DeviceMonitor(QObject):
    # 実際に接続状態が変化したときに発火するシグナル
    left_connected = Signal()
    left_disconnected = Signal()
    right_connected = Signal()
    right_disconnected = Signal()

    # 現在の状態をまとめて通知するシグナル(ステータスウィンドウ表示用)
    status_changed = Signal(bool, bool)  # (left_is_connected, right_is_connected)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._left_connected = True
        self._right_connected = True

        self._readers: dict[bytes, _ReceiverReaderThread] = {}
        self._discovery_timer = QTimer(self)
        self._discovery_timer.timeout.connect(self._discover)

    def start(self) -> None:
        logger.info("DeviceMonitor starting")
        self._discover()
        self._discovery_timer.start(DISCOVERY_INTERVAL_MS)

    def stop(self) -> None:
        logger.info("DeviceMonitor stopping")
        self._discovery_timer.stop()
        for reader in self._readers.values():
            reader.request_stop()
        for reader in self._readers.values():
            reader.wait(READ_TIMEOUT_MS + 500)
        self._readers.clear()

    # ------------------------------------------------------------------
    # レシーバーの抜き差しに追従して監視スレッドを増減させる
    # ------------------------------------------------------------------
    def _discover(self) -> None:
        current_paths = set(_enumerate_receiver_paths())

        for path in list(self._readers):
            if path not in current_paths:
                logger.info("receiver path disappeared: %r", path)
                reader = self._readers.pop(path)
                reader.request_stop()
                reader.wait(READ_TIMEOUT_MS + 500)

        for path in current_paths:
            if path not in self._readers:
                logger.info("receiver path found, starting reader: %r", path)
                reader = _ReceiverReaderThread(path, self)
                reader.status_report.connect(self._on_status_report)
                reader.start()
                self._readers[path] = reader

        if not current_paths:
            logger.debug("no receiver path found yet")

    # ------------------------------------------------------------------
    # バックグラウンドスレッドからのレポートを受けて状態を更新する
    # ------------------------------------------------------------------
    def _on_status_report(self, left_connected: bool, right_connected: bool) -> None:
        self._set_left(left_connected)
        self._set_right(right_connected)

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------
    def _set_left(self, connected: bool) -> None:
        if connected == self._left_connected:
            return
        self._left_connected = connected
        if connected:
            self.left_connected.emit()
        else:
            self.left_disconnected.emit()
        self.status_changed.emit(self._left_connected, self._right_connected)

    def _set_right(self, connected: bool) -> None:
        if connected == self._right_connected:
            return
        self._right_connected = connected
        if connected:
            self.right_connected.emit()
        else:
            self.right_disconnected.emit()
        self.status_changed.emit(self._left_connected, self._right_connected)

    # ------------------------------------------------------------------
    # テスト用: トレイメニューの「テスト通知」から呼ばれる
    # ------------------------------------------------------------------
    def simulate_disconnect(self, side: str) -> None:
        if side == "left":
            self._set_left(False)
        elif side == "right":
            self._set_right(False)

    def simulate_connect(self, side: str) -> None:
        if side == "left":
            self._set_left(True)
        elif side == "right":
            self._set_right(True)
