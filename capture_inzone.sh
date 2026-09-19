#!/usr/bin/env bash
#
# INZONE Buds USBレシーバーのトラフィックを usbmon + tshark でキャプチャするスクリプト。
# Claude Code に「このスクリプトを実行して」と頼んで使うことを想定。
#
# 前提:
#   - tshark がインストールされていること (無ければ apt/dnf/pacman で install)
#   - sudo が使えること(usbmonのロードとtsharkの実行に必要)
#
set -euo pipefail

echo "=== Step 1: tshark の確認 ==="
if ! command -v tshark >/dev/null 2>&1; then
    echo "tshark が見つかりません。インストールしてください。例:"
    echo "  Debian/Ubuntu系: sudo apt install tshark"
    echo "  Fedora系:        sudo dnf install wireshark-cli"
    echo "  Arch系:           sudo pacman -S wireshark-cli"
    exit 1
fi
echo "OK: tshark が見つかりました。"

echo ""
echo "=== Step 2: Sonyレシーバーを自動検出 ==="
echo "現在接続されているUSBデバイス一覧:"
lsusb
echo ""

MATCHES=$(lsusb | grep -i "sony" || true)
BUSNUM=""
DEVNUM=""

if [ -n "$MATCHES" ] && [ "$(echo "$MATCHES" | wc -l)" -eq 1 ]; then
    echo "Sony製と思われるデバイスを自動検出しました:"
    echo "  $MATCHES"
    BUSNUM=$(echo "$MATCHES" | sed -E 's/Bus ([0-9]+).*/\1/')
    DEVNUM=$(echo "$MATCHES" | sed -E 's/.*Device ([0-9]+):.*/\1/')
    read -rp "このデバイスで合っていますか? [Y/n]: " CONFIRM
    if [[ "$CONFIRM" =~ ^[Nn] ]]; then
        BUSNUM=""
        DEVNUM=""
    fi
fi

if [ -z "$BUSNUM" ]; then
    echo "自動検出できなかった、または不一致でした。上の一覧から対象デバイスを選んでください。"
    read -rp "Bus番号 (例: 001 の場合は 1): " BUSNUM
    read -rp "Device番号 (例: 005 の場合は 5): " DEVNUM
fi

BUS_NOPAD=$((10#$BUSNUM))
echo "使用するバス番号: ${BUS_NOPAD} / デバイス番号: ${DEVNUM}"

echo ""
echo "=== Step 3: usbmon の準備 ==="
echo "この後 tshark をバックグラウンドで起動するため、先にsudo認証を済ませておきます。"
sudo -v
if ! lsmod | grep -q usbmon; then
    echo "usbmon カーネルモジュールをロードします"
    sudo modprobe usbmon
fi

MON_IF="usbmon${BUS_NOPAD}"
echo "使用するキャプチャインターフェース: ${MON_IF}"

OUTFILE="inzone_capture_$(date +%Y%m%d_%H%M%S).pcapng"
MARKERS="${OUTFILE%.pcapng}_markers.txt"
FILTERED_TXT="${OUTFILE%.pcapng}_filtered.txt"
# dumpcap はネットワークインターフェースを開いた後、書き込み前に root 権限を落とすため、
# プロジェクトディレクトリ(所有者以外書き込み不可)には直接書けない。
# 誰でも書き込める /tmp に一旦書き、後で正式な場所へ sudo mv する。
TMP_OUTFILE="/tmp/${OUTFILE}"

echo ""
echo "=== Step 4: キャプチャ開始 ==="
echo "出力ファイル: ${OUTFILE}"
echo "マーカーファイル: ${MARKERS}"

: > "$MARKERS"
CAPTURE_START=$(date +%s.%N)
echo "capture_start ${CAPTURE_START}" >> "$MARKERS"

TSHARK_LOG="${OUTFILE%.pcapng}_tshark.log"
sudo tshark -i "$MON_IF" -w "$TMP_OUTFILE" > "$TSHARK_LOG" 2>&1 &
TSHARK_PID=$!
sleep 2  # インターフェースが立ち上がるまでの猶予

if [ ! -e "$TMP_OUTFILE" ]; then
    echo "エラー: tshark が出力ファイルを作成できませんでした。ログ:"
    cat "$TSHARK_LOG"
    exit 1
fi
echo "OK: キャプチャファイルの作成を確認しました。"

mark() {
    local label="$1"
    local now offset
    now=$(date +%s.%N)
    offset=$(awk -v a="$now" -v b="$CAPTURE_START" 'BEGIN{printf "%.3f", a-b}')
    echo "${label} ${offset}" >> "$MARKERS"
    echo ">> マーク記録: ${label} (キャプチャ開始から約 ${offset} 秒)"
}

echo ""
echo "--- 基準トラフィック取得 ---"
echo "両方のイヤホンを装着し、正常に接続された状態にしてください。"
read -rp "準備ができたら Enter を押してください... " _
mark "baseline_start"
sleep 10
mark "baseline_end"
echo "基準トラフィックの記録完了。"

run_event() {
    local side="$1"    # left / right
    local action="$2"  # disconnect / reconnect
    echo ""
    echo "--- ${side} を ${action} ---"
    read -rp "${side} のイヤホンを ${action} する準備ができたら Enter を押してください... " _
    mark "${side}_${action}_about_to_happen"
    echo "今すぐ ${side} のイヤホンを ${action} してください。"
    read -rp "実行したら Enter を押してください... " _
    mark "${side}_${action}_confirmed"
    sleep 5
}

run_event "left" "disconnect"
run_event "left" "reconnect"
run_event "right" "disconnect"
run_event "right" "reconnect"

echo ""
echo "=== Step 5: キャプチャ終了 ==="
sudo -v
sudo kill "$TSHARK_PID" 2>/dev/null || true
wait "$TSHARK_PID" 2>/dev/null || true
sleep 1
sudo mv "$TMP_OUTFILE" "$OUTFILE"
sudo chown "$(id -u):$(id -g)" "$OUTFILE"

echo ""
echo "=== Step 6: 対象デバイスだけに絞った読みやすいログを生成 ==="
tshark -r "$OUTFILE" -Y "usb.device_address == ${DEVNUM}" \
    -T fields -e frame.time_relative -e usb.endpoint_address -e usb.capdata \
    > "$FILTERED_TXT" || true
echo "絞り込みログ: ${FILTERED_TXT} ($(wc -l < "$FILTERED_TXT") 行)"

echo ""
echo "=== 完了 ==="
echo "以下の3つのファイルを Claude にアップロードしてください:"
echo "  1. ${OUTFILE}       (生のキャプチャ)"
echo "  2. ${MARKERS}       (イベントのタイムスタンプ)"
echo "  3. ${FILTERED_TXT}  (対象デバイスだけに絞ったログ、事前確認用)"
