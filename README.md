# buds-watcher

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

Releases aren't packaged as a single binary for Linux yet, so you currently need to clone the code and
run it yourself.  
It also needs to access the device via `libusb`, so read/write permission on `/dev/bus/usb/*/*` is required.

### 1. Set up USB read/write permissions

Create the following file:

```
# /etc/udev/rules.d/99-inzone-buds.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="0ec2", MODE="0660", GROUP="input"
```

Then add your user to the `input` group, and apply the change by rebooting or running `udevadm control --reload-rules && udevadm trigger`.

### 2. Run the application

1. Clone the repository
2. Enter the dev shell with `nix develop`
   - Skip this step if you're not using Nix
   - If you also use direnv, `direnv allow` will drop you into the dev shell automatically
3. Fetch dependencies with `uv sync`
4. Run it with `uv run poe app`
5. You're good to go if an icon shows up in the system tray

### Ubuntu and other GNOME environments

GNOME removed the system tray feature by default, so the icon won't show up as-is.  
Install **"AppIndicator and KStatusNotifierItem Support"** from GNOME Extensions.

### Wayland environments

Running under Wayland currently shows the notification in the center of the screen - this isn't abug, it's how it's designed to work.  
It shows up correctly in the top-right corner under X11, so if that really bothers you, run it under X11 instead.

<details>

<summary>Why does this happen?</summary>

Wayland doesn't let clients specify a window's absolute position, for security reasons, so it ends up
at whatever default position the compositor (e.g. KWin) chooses - usually the center of the screen.  
Placing it correctly in the top-right corner would require support for the `wlr-layer-shell` protocol(`layer-shell-qt` on KDE), but there's no official PySide6 binding for it, so this isn't supported yet.

</details>
