import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LayerShell

Window {
    id: root
    visible: false
    width: 340
    height: 84
    color: "transparent"

    // Waylandのlayer-shellプロトコルで画面端に固定表示する。
    // 「プライマリモニター」はWaylandに統一的な概念が無くQtのprimaryScreen()も
    // 信頼できないため、wantsToBeOnActiveScreenで「今フォーカスがある画面」に
    // 出す方針にしている(実機検証済み)。
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorRight
    LayerShell.Window.margins.top: 24
    LayerShell.Window.margins.right: 24
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.wantsToBeOnActiveScreen: true
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    property string titleText: ""
    property string messageText: ""
    property color accentColor: "#dc3c3c"
    // Pythonからはこの値をインクリメントするだけで新しい通知を出せる
    // (invokeMethodの型変換に頼らず、プロパティ設定だけで完結させるため)。
    property int messageSeq: 0

    readonly property int displayMs: 4000
    readonly property int fadeMs: 250

    onMessageSeqChanged: {
        root.visible = true
        fadeInAnim.stop()
        fadeOutAnim.stop()
        content.opacity = 0
        fadeInAnim.start()
        hideTimer.restart()
    }

    Item {
        id: content
        anchors.fill: parent
        opacity: 0

        Rectangle {
            anchors.fill: parent
            radius: 14
            color: "#18181c"
            opacity: 0.92
        }

        Rectangle {
            width: 6
            height: parent.height
            radius: 3
            color: root.accentColor
        }

        Column {
            anchors.left: parent.left
            anchors.leftMargin: 24
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            Text {
                text: root.titleText
                color: "white"
                font.pixelSize: 15
                font.bold: true
            }
            Text {
                text: root.messageText
                color: "#d2d2d2"
                font.pixelSize: 12
                width: parent.width
                wrapMode: Text.NoWrap
            }
        }
    }

    NumberAnimation {
        id: fadeInAnim
        target: content
        property: "opacity"
        from: 0
        to: 1
        duration: root.fadeMs
        easing.type: Easing.OutCubic
    }

    NumberAnimation {
        id: fadeOutAnim
        target: content
        property: "opacity"
        from: 1
        to: 0
        duration: root.fadeMs
        easing.type: Easing.InCubic
        onStopped: {
            if (content.opacity <= 0) {
                root.visible = false
            }
        }
    }

    Timer {
        id: hideTimer
        interval: root.displayMs
        onTriggered: fadeOutAnim.start()
    }
}
