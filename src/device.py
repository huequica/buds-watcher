"""
INZONE Buds の左右接続状態を監視するモジュール。

USBレシーバー(VID=0x054c, PID=0x0ec2)は標準のHIDインターフェースを持ち、
状態変化(切断/再接続)のたびに64バイトのHIDレポートをイベント駆動で送ってくる。
実機USBキャプチャ(capture_inzone.sh で取得、usbmon + tshark)を解析した結果、
以下のことが判明している:

- byte[8] == 0x12 かつ byte[9] == 0x01 のレポートが「左右接続状態」を示す
- byte[13] が左の接続状態(1=接続, 0=切断)
- byte[14] が右の接続状態(1=接続, 0=切断)
- byte[8] == 0x14 かつ byte[9] == 0x04 のレポートが「左右バッテリー残量」を示す
  (INZONE Hubアプリの表示値と実機で一致確認済み)
- byte[14] が左のバッテリー残量(%, 0-100)
- byte[16] が右のバッテリー残量(%, 0-100)

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

BATTERY_REPORT_CLASS = 0x14
BATTERY_REPORT_TYPE = 0x04
LEFT_BATTERY_OFFSET = 14
RIGHT_BATTERY_OFFSET = 16
MIN_BATTERY_REPORT_LEN = 17
# 0xff(255)はバッテリー残量が「まだ不明」であることを示すセンチネル値
# (再接続直後などに見られる)。battery_report シグナルではこれを -1 として
# 伝える(不明なままそのサイドの値だけ無視し、既知の値を保持し続ける)。
BATTERY_UNKNOWN = -1


def _normalize_battery_percent(raw: int) -> int:
    return raw if 0 <= raw <= 100 else BATTERY_UNKNOWN


READ_TIMEOUT_MS = 1000
RECONNECT_DELAY_MS = 3000
DISCOVERY_INTERVAL_MS = 3000

# openには成功するがreadが一度もデータを返さずに毎回即時失敗するパスは、
# OS予約のHIDコレクション(Windowsのコンシューマーコントロール等)など、
# そもそも読めない対象である可能性が高い。この回数連続で「一度も成功データ
# を得られないまま失敗」した場合はそのパスを諦める(ログ肥大化・無駄な
# リトライを防ぐため)。デバイスの抜き差しで状態はリセットされる。
MAX_CONSECUTIVE_EMPTY_FAILURES = 3


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
    battery_report = Signal(int, int)  # (left_battery_percent, right_battery_percent)
    gave_up = Signal(bytes)  # 一度もデータを得られないまま失敗し続け、諦めたパス

    def __init__(self, path: bytes, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self._stop_requested = False
        self._consecutive_empty_failures = 0

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
                got_data = self._read_loop(device)
            finally:
                try:
                    device.close()
                except Exception:
                    pass

            if got_data:
                self._consecutive_empty_failures = 0
            else:
                self._consecutive_empty_failures += 1
                if self._consecutive_empty_failures >= MAX_CONSECUTIVE_EMPTY_FAILURES:
                    logger.warning(
                        "giving up on HID path %r after %d consecutive failures "
                        "without ever reading data (likely an unreadable OS-reserved "
                        "collection)",
                        self._path,
                        self._consecutive_empty_failures,
                    )
                    self.gave_up.emit(self._path)
                    return

            if not self._stop_requested:
                self.msleep(RECONNECT_DELAY_MS)

    def _read_loop(self, device: "hid_types.device") -> bool:
        """状態レポート(不一致含む)を一度でも読めたら True を返す。"""
        got_data = False
        while not self._stop_requested:
            try:
                data = device.read(64, timeout_ms=READ_TIMEOUT_MS)
            except Exception:
                # レシーバーが抜かれた等。外側のループで開き直しを試みる。
                logger.exception("read() failed on HID path %r", self._path)
                return got_data

            if not data:
                continue
            got_data = True
            if len(data) < 10:
                continue
            report_class, report_type = data[8], data[9]

            if (
                report_class == STATUS_REPORT_CLASS
                and report_type == STATUS_REPORT_TYPE
                and len(data) >= MIN_STATUS_REPORT_LEN
            ):
                left_connected = bool(data[LEFT_STATUS_OFFSET])
                right_connected = bool(data[RIGHT_STATUS_OFFSET])
                logger.info(
                    "status report on %r: left=%s right=%s",
                    self._path,
                    left_connected,
                    right_connected,
                )
                self.status_report.emit(left_connected, right_connected)
            elif (
                report_class == BATTERY_REPORT_CLASS
                and report_type == BATTERY_REPORT_TYPE
                and len(data) >= MIN_BATTERY_REPORT_LEN
            ):
                left_battery = _normalize_battery_percent(data[LEFT_BATTERY_OFFSET])
                right_battery = _normalize_battery_percent(data[RIGHT_BATTERY_OFFSET])
                logger.info(
                    "battery report on %r: left=%d right=%d (raw left=%d right=%d)",
                    self._path,
                    left_battery,
                    right_battery,
                    data[LEFT_BATTERY_OFFSET],
                    data[RIGHT_BATTERY_OFFSET],
                )
                self.battery_report.emit(left_battery, right_battery)
            else:
                logger.debug("unrelated report on %r: %r", self._path, data)
        return got_data


class DeviceMonitor(QObject):
    # 実際に接続状態が変化したときに発火するシグナル
    left_connected = Signal()
    left_disconnected = Signal()
    right_connected = Signal()
    right_disconnected = Signal()

    # 現在の状態をまとめて通知するシグナル(ステータスウィンドウ表示用)
    status_changed = Signal(bool, bool)  # (left_is_connected, right_is_connected)

    # バッテリー残量レポートを受信するたびに発火するシグナル
    battery_changed = Signal(int, int)  # (left_battery_percent, right_battery_percent)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._left_connected = True
        self._right_connected = True
        self.left_battery: int | None = None
        self.right_battery: int | None = None

        self._readers: dict[bytes, _ReceiverReaderThread] = {}
        self._given_up_paths: set[bytes] = set()
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

        # 抜き差しされたパスは条件が変わりうるので、諦めていたことを忘れて良い。
        self._given_up_paths &= current_paths

        for path in current_paths:
            if path not in self._readers and path not in self._given_up_paths:
                logger.info("receiver path found, starting reader: %r", path)
                reader = _ReceiverReaderThread(path, self)
                reader.status_report.connect(self._on_status_report)
                reader.battery_report.connect(self._on_battery_report)
                reader.gave_up.connect(self._on_reader_gave_up)
                reader.start()
                self._readers[path] = reader

        if not current_paths:
            logger.debug("no receiver path found yet")

    def _on_reader_gave_up(self, path: bytes) -> None:
        self._given_up_paths.add(path)
        self._readers.pop(path, None)

    # ------------------------------------------------------------------
    # バックグラウンドスレッドからのレポートを受けて状態を更新する
    # ------------------------------------------------------------------
    def _on_status_report(self, left_connected: bool, right_connected: bool) -> None:
        self._set_left(left_connected)
        self._set_right(right_connected)

    def _on_battery_report(self, left_battery: int, right_battery: int) -> None:
        # -1(BATTERY_UNKNOWN)はまだ不明という意味なので、既知の値を保持する。
        if left_battery != BATTERY_UNKNOWN:
            self.left_battery = left_battery
        if right_battery != BATTERY_UNKNOWN:
            self.right_battery = right_battery
        self.battery_changed.emit(
            self.left_battery if self.left_battery is not None else BATTERY_UNKNOWN,
            self.right_battery if self.right_battery is not None else BATTERY_UNKNOWN,
        )

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
