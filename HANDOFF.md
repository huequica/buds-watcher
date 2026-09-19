# 引き継ぎ: INZONE Buds 左右切断検知アプリ

## ゴール

Sony INZONE Buds の左右どちらかのイヤホンが切断されたときに、
OS標準の通知(Windowsのアクションセンター等)を使わず、独自のオーバーレイで
画面に通知する常駐アプリ(トレイアイコン付き、Windows/Linux両対応)を作る。

## 重要な前提・制約

- ユーザーはイヤホンとPCを**付属のUSBレシーバー(2.4GHzトランシーバー、Bluetoothではない)**
  で接続している。
- このUSBレシーバーの通信プロトコルはSonyの独自仕様で、公開されているドキュメントは無い。
  左右どちらが切断されたかを検知するには、実機のUSBパケットをキャプチャして
  プロトコルをリバースエンジニアリングする必要がある。
- Windowsでの USBPcap + Wireshark によるキャプチャは、USBデバイス数が多く流速も速いため
  対象を絞り込めず断念。Linux + usbmon の方が(バスごとにキャプチャが分かれるため)
  ノイズが少なく現実的、との結論になっている。

## 現在の状態

### 1. UIスケルトンは完成済み(動作確認済み)

`inzone-buds-monitor/` に以下を実装済み:

- `main.py` — エントリーポイント
- `tray.py` — システムトレイアイコン(右クリックで「アプリケーション画面を開く」
  「テスト通知」「終了」)。L/Rの状態に応じてアイコンの色が変わる。
- `notify.py` — OS標準通知を使わない、自前の常時最前面オーバーレイ通知
  (フェードイン/アウト、画面右上に表示)
- `mainwindow.py` — 簡易ステータスウィンドウ
- `device.py` — **イヤホン監視部分。現状はダミー実装**。
  `DeviceMonitor._poll()` に実プロトコルを実装すれば完成する設計になっている。
  `simulate_disconnect("left"/"right")` / `simulate_connect(...)` でテスト通知を
  発火できるようになっている(トレイメニューから呼べる)。
- `requirements.txt` — 依存は今のところ `PySide6` のみ。実プロトコル実装時に
  `hidapi`(pip: `hid`)などが必要になる見込み。

動作確認方法:
```bash
pip install -r requirements.txt
python3 main.py
```
オフスクリーンモードでの起動確認は `QT_QPA_PLATFORM=offscreen python3 main.py` で実施済み(クラッシュなし)。

既知の制約として README.md に記載済み:
- Windowsの排他的フルスクリーンゲームには重ねて表示できない場合がある
- Linux/WaylandのKDEでは通常のQt「常に最前面」がコンポジタ依存。X11なら安定動作。
  将来的に layer-shell 対応を検討の余地あり。

### 2. プロトコル解析はこれから

`capture_inzone.sh` を用意済み(同梱)。これはLinux上で:

1. `lsusb` からSony製レシーバーを自動検出(手動選択にもフォールバック)
2. `usbmon` を使って該当バスだけをキャプチャ
3. 対話式に「基準トラフィック取得」→「左切断」→「左再接続」→「右切断」→「右再接続」
   の各イベントを実行させ、タイムスタンプを `*_markers.txt` に記録
4. キャプチャ終了後、`usb.device_address` で対象デバイスだけに絞った読みやすいログ
   (`*_filtered.txt`)を自動生成

というスクリプト。**このタスクを引き継いだら、まずこのスクリプトを実行して
実際のキャプチャを取ってほしい。**

## 次にやること

1. `capture_inzone.sh` を実行し、キャプチャ一式(`.pcapng` / `_markers.txt` / `_filtered.txt`)を取得する
   - `tshark` が無ければ先にインストールする(`sudo apt install tshark` 等)
2. `_markers.txt` のタイムスタンプを手がかりに、`_filtered.txt` または `.pcapng` を解析し、
   「左切断の瞬間」「右切断の瞬間」でそれぞれ変化したバイト位置・値を特定する
   - 基準トラフィック(何も起きていない状態)と比較して差分を見るのが近道
   - 左右で異なるバイトが変化していれば、それが「どちらが切断されたか」を示すフラグの候補
3. 特定できたら `device.py` の `_poll()` を実装する:
   - `hidapi`(`import hid`)等でそのUSBデバイス(VID/PID判明済みのはず)を開く
   - 定期的に読み取り、該当バイトを見て `_set_left(bool)` / `_set_right(bool)` を呼ぶ
4. Windows側でも同じVID/PIDのデバイスを同様に開けるか確認する
   (Windows特有の権限・ドライバ問題が出る可能性はある。`hidapi`はクロスプラットフォーム
   対応だが、Sonyの独自ドライバがインストールされている環境だと生HIDアクセスが
   ブロックされる可能性もあるため要検証)
5. 一通り動いたら、`.gitignore` や配布方法(PyInstallerでの実行ファイル化など)も検討する

## 参考: これまでの会話で決めた設計判断

- UIフレームワークはPySide6(Qt)を選定。理由: Windows/Linux両対応、
  システムトレイ(`QSystemTrayIcon`)とトップモストのフレームレスウィンドウの両方を
  標準機能でカバーできるため。
- GNOMEは標準でシステムトレイが無いため、`AppIndicator and KStatusNotifierItem Support`
  拡張機能が必要な旨をREADMEに明記済み。KDEは標準対応。
