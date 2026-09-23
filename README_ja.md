# buds-watcher

Sony Inzone buds のイヤホンの切断、再接続を画面に通知するアプリ

# 機能

- イヤホンの切断、接続を画面に通知します
  - OS に搭載された通知機能は使用せず最前面に出すのでゲーム中などでも確認できます
  - 接続された際は通知にバッテリーの残量が表示されます
- メインウィンドウで現時点のバッテリー残量を確認できます
- Windows/Linux 対応
  - MacOS には現状対応していません
  - Linux で使用する際はセットアップが必要です(後述)

# 使い方

## Windows

1. [Releases](https://github.com/huequica/buds-watcher/releases) から最新の `buds-watcher.exe` をダウンロードする
2. `buds-watcher.exe` を実行
3. システムトレイにアイコンが表示されていれば　OK

## Linux

リリースの際に Linux 向けにシングルバイナリに固めていないので現状コードを clone して自分で実行する必要があります  
また `libusb` を経由してアクセスしないといけないので `/dev/bus/usb/*/*` への読み書き権限も必要になります

### 1. USB 読み書き権限の設定

以下のファイルを作成してください

```
# /etc/udev/rules.d/99-inzone-buds.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="0ec2", MODE="0660", GROUP="input"
```

その後ユーザーを `input` グループに入れた後再起動 or `udevadm control --reload-rules && udevadm trigger` で設定を反映してください

### 2. アプリケーション起動

1. リポジトリを clone する
2. `nix develop` で DevShell に入る
   - nix を使用していなければこのステップは無視してください
   - direnv を併用していれば `direnv allow` で自動的に DevShell に入れます
3. `uv sync` で依存を落とす
4. `uv run poe app` で実行
5. システムトレイにアイコンが表示されていれば　OK

### Ubuntu などの GNOME 環境

GNOME は標準でシステムトレイ機能を廃止しているためこのままだとアイコンが表示されません  
GNOME Extensions から **"AppIndicator and KStatusNotifierItem Support"** を入れてください

### Wayland 環境

現状 Wayland 環境で動かす場合は通知が画面中央に表示されますがバグではなく仕様です  
X11 環境では正しく右上に出ますのでどうしても気になりすぎて発狂しそうな方は X11 で動かしてください

<details>

<summary>なんでこんなことになっているか</summary>

Wayland はセキュリティ上の理由でクライアントがウィンドウの絶対位置を指定することを許可しておらずコンポジタ(KWin など)が決めたデフォルト位置、たいてい画面中央に表示されます  
正しく右上に固定するには `wlr-layer-shell` プロトコル(KDE では`layer-shell-qt`)への対応が必要だけど PySide6 用の公式バインディングが無いため未対応となっています

</details>
