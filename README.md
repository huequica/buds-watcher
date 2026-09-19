# INZONE Buds Monitor (v0.1 スケルトン)

Sony INZONE Buds の左右イヤホンの切断を検知し、OS標準の通知を使わずに
常時最前面のオーバーレイでプッシュ通知するための常駐アプリです。

## 現状でできること

- システムトレイに常駐し、右クリックで以下を選べる
  - 「アプリケーション画面を開く」
  - 「テスト通知: 左/右を切断・再接続」(動作確認用)
  - 「アプリを終了する」
- USBレシーバー(VID 0x054c / PID 0x0ec2)のHIDレポートをイベント駆動で監視し、
  左右どちらかが切断/再接続されると画面にオーバーレイ通知が出る(OS標準通知は不使用)
- トレイアイコンの色でL/Rの状態を表示(緑=OK / 赤=切断)

実プロトコルの解析結果は `src/device.py` のコメントと `HANDOFF.md` を参照。

## セットアップ

Nix (flakes) を使う場合:

```bash
nix develop
uv sync
uv run poe app
```

[direnv](https://direnv.net/) を使っていれば `.envrc`(`use flake`)により
ディレクトリに入るだけで自動的に devShell に入る。

Nixを使わない場合は [uv](https://docs.astral.sh/uv/) を直接インストールして:

```bash
uv sync
uv run poe app
```

### タスク一覧

uv自体にはnpmの`package.json`の`scripts`に相当する機能は無いため、
[Poe the Poet](https://poethepoet.natn.io/) で代用している(`pyproject.toml`の
`[tool.poe.tasks]`)。`uv run poe <タスク名>`で実行する:

| タスク | 内容 |
| --- | --- |
| `app` | アプリを起動する |
| `lint` | `ruff check .` |
| `format` | `ruff format .` |
| `format-check` | `ruff format --check .`(CIと同じ) |
| `check` | `lint` + `format-check` |

### Linuxでの追加設定(hidrawへのアクセス権限)

`src/device.py` は `/dev/hidraw*` を直接読むため、root以外のユーザーでもレシーバーの
HIDデバイスに読み取りアクセスできるよう udev ルールが必要。例:

```
# /etc/udev/rules.d/99-inzone-buds.rules
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="0ec2", MODE="0660", GROUP="input"
```

ユーザーを `input` グループに追加し、ルールを反映(`udevadm control --reload-rules && udevadm trigger`、
または再ログイン/再起動)すること。

### GNOMEを使っている場合の注意

GNOMEは標準でシステムトレイ機能を廃止しているため、このままだとトレイアイコンが
表示されません。GNOME Extensions から
**"AppIndicator and KStatusNotifierItem Support"** を入れてください。
KDE Plasma はこの対応が標準で入っているので追加設定は不要です。

### オーバーレイ通知の既知の制約(正直な注意点)

- Windowsで「排他的フルスクリーン」で動くゲーム(まれに存在)には、OS側の制約で
  重ねて表示できない場合があります。多くの現代のゲームはボーダレス/フルスクリーン
  最適化で動くため、その場合は問題なく表示されます。
- **Linux/Wayland**: 通知の表示・フェード自体は動作するが、**画面上の位置を
  指定通り(右上)に固定できない**。Waylandはセキュリティ上の理由でクライアントが
  ウィンドウの絶対位置を指定することを許可しておらず、コンポジタ(KWin等)が
  決めたデフォルト位置(多くは画面中央)に表示される。正しく右上に固定するには
  `wlr-layer-shell` プロトコル(KDEなら `layer-shell-qt`)への対応が必要だが、
  PySide6用の公式バインディングが無いため未対応。**X11セッションでは正しく
  右上に固定表示される**ため、位置を重視する場合はX11セッションの使用を推奨する。

## Windows用実行ファイル

Python環境を用意せずに使いたい場合向けに、[PyInstaller](https://pyinstaller.org/)で
単一exeにまとめられる。`master`にpushすると GitHub Actions
(`.github/workflows/release.yml`)がWindows上で自動ビルドし、[Releases](../../releases)に
`pyproject.toml`の`version`(`v0.1.0`のような形式)をタグ名として`buds-watcher.exe`を
アップロードする。リリースするバージョンは、masterへのPRを作る際に`pyproject.toml`の
`version`を上げておくこと(上げ忘れて同じバージョンでpushすると、既存リリースが上書きされる)。

手元でビルドする場合(Windows上で):

```bash
uv sync --group build
uv run poe build
```

`dist/buds-watcher.exe` が生成される。署名していないため、初回起動時にWindows Defender
SmartScreenの警告が出る場合がある。

Windows実機での動作確認はまだ行っていない(hidrawの代わりにhidapiのWindowsバックエンドを
使う想定だが、権限やドライバの問題が出る可能性がある)。
