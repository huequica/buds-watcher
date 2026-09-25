<p align="center">
  <img src="./icons/app.png" width="128" height="128" alt="buds-watcher icon">
</p>

# buds-watcher

[日本語の README はこちら](./README_ja.md)

An app that notifies you on screen when your Sony INZONE Buds earbuds disconnect or reconnect.

# Features

- Notifies you on screen when an earbud disconnects or connects
  - Doesn't use the OS's built-in notification system, so it stays on top and is visible even during games
  - Battery level is shown in the notification when an earbud connects
- Check the current battery level anytime from the main window
- Windows/Linux support
  - macOS isn't supported at this time
  - Setup is required to use it on Linux (see below)

# Usage

## Windows

1. Download the latest `buds-watcher.exe` from [Releases](https://github.com/huequica/buds-watcher/releases)
2. Run `buds-watcher.exe`
3. You're good to go if an icon shows up in the system tray

## Linux

It also needs to access the device via `libusb`, so read/write permission on `/dev/bus/usb/*/*` is required.

### 1. Set up USB read/write permissions

Create the following file:

```
# /etc/udev/rules.d/99-inzone-buds.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="0ec2", MODE="0660", GROUP="input"
```

Then add your user to the `input` group, and apply the change by rebooting or running `udevadm control --reload-rules && udevadm trigger`.

### 2. Get the application

Pick whichever fits you:

- Download the latest `buds-watcher` binary from [Releases](https://github.com/huequica/buds-watcher/releases), run `chmod +x buds-watcher`, then run it
- If you use Nix flakes: `nix run github:huequica/buds-watcher`, or add this repo as a flake input and reference `packages.<system>.default`
- Clone the repository and run it from source:
  1. Enter the dev shell with `nix develop`
     - Skip this step if you're not using Nix
     - If you also use direnv, `direnv allow` will drop you into the dev shell automatically
  2. Fetch dependencies with `uv sync`
  3. Run it with `uv run poe app`

You're good to go if an icon shows up in the system tray.

### Ubuntu and other GNOME environments

GNOME removed the system tray feature by default, so the icon won't show up as-is.  
Install **"AppIndicator and KStatusNotifierItem Support"** from GNOME Extensions.

### Wayland environments

On compositors that support the `wlr-layer-shell` protocol with KDE's `layer-shell-qt` installed (e.g. KDE Plasma), the notification is anchored to the top-right corner correctly, same as under X11.  
On other Wayland compositors (e.g. GNOME) or environments without `layer-shell-qt`, it falls back to showing the notification in the center of the screen - this isn't a bug, it's how it's designed to work.

<details>

<summary>Why does this happen?</summary>

Wayland doesn't let clients specify a window's absolute position, for security reasons, so a plain window ends up
at whatever default position the compositor (e.g. KWin) chooses - usually the center of the screen.  
Placing it correctly in the top-right corner requires support for the `wlr-layer-shell` protocol. There's no official PySide6 binding for it, but KDE's `layer-shell-qt` project ships an official QML module (`org.kde.layershell`), so buds-watcher uses a QML-based overlay through that module when it's available, and falls back to the plain widget overlay otherwise.

</details>
