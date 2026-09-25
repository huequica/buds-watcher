{
  description = "buds-watcher dev environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      # PySide6のPyPIホイールは自前のQt6を同梱しているが、GL/X11/Waylandなど
      # ホストが提供すべき下位ライブラリはNixOSではFHSパスに無いため明示する。
      runtimeLibs = pkgs.lib.makeLibraryPath [
        pkgs.stdenv.cc.cc.lib
        pkgs.zlib
        pkgs.libGL
        pkgs.fontconfig
        pkgs.dbus
        pkgs.glib
        pkgs.freetype
        pkgs.libpng
        pkgs.expat
        pkgs.harfbuzz
        pkgs.zstd
        pkgs.libxkbcommon
        pkgs.wayland
        pkgs.libx11
        pkgs.libxcb
        pkgs.libxrender
        pkgs.libxi
        pkgs.libsm
        pkgs.libice
        pkgs.libxext
        pkgs.libxfixes
        pkgs.libxrandr
        pkgs.libxcomposite
        pkgs.libxdamage
        pkgs.libxshmfence
        pkgs.libxcursor
        pkgs.libxtst
        # QtQml/QtQuick(layer-shell-qtのQMLプラグインを使うのに必要)が推移的に要求するもの
        pkgs.krb5.lib
        pkgs.brotli.lib
      ];
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pkgs.uv
          pkgs.python312
          # USBキャプチャ(capture_inzone.sh)用
          pkgs.wireshark-cli # tshark
          pkgs.usbutils # lsusb
        ];

        env = {
          UV_PYTHON = "${pkgs.python312}/bin/python3.12";
          UV_PYTHON_DOWNLOADS = "never";
        };

        shellHook = ''
          export LD_LIBRARY_PATH="${runtimeLibs}:$LD_LIBRARY_PATH"
          # WaylandでのオーバーレイをlayerShellQtのQMLモジュール
          # (org.kde.layershell)で固定表示するために必要(notify_layershell.py)。
          export QML2_IMPORT_PATH="${pkgs.kdePackages.layer-shell-qt}/lib/qt-6/qml:$QML2_IMPORT_PATH"
        '';
      };
    };
}
