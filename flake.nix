{
  description = "buds-watcher: Sony INZONE Buds 左右切断検知アプリ";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      pyprojectToml = builtins.fromTOML (builtins.readFile ./pyproject.toml);

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

      # `packages.${system}.default`(このリポジトリをflake経由で他のflakeから
      # インストールする場合や `nix run`/`nix bundle` で使う実行環境)用。
      pythonEnv = pkgs.python312.withPackages (
        ps: with ps; [
          pyside6
          hidapi
          pyyaml
        ]
      );

      # ホストの /etc/fonts に頼ると、CJKフォントが入っていない環境
      # (fontconfig未設定のディストリや `nix bundle` のchroot環境など)で
      # 日本語がtofu(□)になる。日本語UIのアプリなので、CJKフォントを
      # 閉包に含めて自己完結したfonts.confをFONTCONFIG_FILEで明示する。
      fontsConf = pkgs.makeFontsConf {
        fontDirectories = [
          pkgs.noto-fonts
          pkgs.noto-fonts-cjk-sans
        ];
      };
    in
    {
      packages.${system}.default = pkgs.stdenv.mkDerivation {
        pname = pyprojectToml.project.name;
        version = pyprojectToml.project.version;
        src = ./.;

        nativeBuildInputs = [ pkgs.makeWrapper ];
        dontBuild = true;

        installPhase = ''
          runHook preInstall

          mkdir -p $out/share/buds-watcher $out/bin
          cp -r src icons pyproject.toml $out/share/buds-watcher/

          makeWrapper ${pythonEnv}/bin/python3.12 $out/bin/buds-watcher \
            --add-flags "$out/share/buds-watcher/src/main.py" \
            --set LD_LIBRARY_PATH "${runtimeLibs}" \
            --set QML2_IMPORT_PATH "${pkgs.kdePackages.layer-shell-qt}/lib/qt-6/qml" \
            --set FONTCONFIG_FILE "${fontsConf}"

          runHook postInstall
        '';

        meta = {
          description = pyprojectToml.project.description;
          mainProgram = "buds-watcher";
          platforms = [ system ];
        };
      };

      apps.${system}.default = {
        type = "app";
        program = "${self.packages.${system}.default}/bin/buds-watcher";
      };

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
          # CJKフォントが無い環境でも日本語UIがtofuにならないようにする。
          export FONTCONFIG_FILE="${fontsConf}"
        '';
      };
    };
}
