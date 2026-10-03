# Cinnamon Clipboard

A lightweight clipboard manager designed for Linux desktop environments.

Cinnamon Clipboard keeps a persistent history of copied content and provides quick access to previously copied items through a system tray menu.

## Features

* Persistent clipboard history using SQLite.
* Support for:

  * Plain text.
  * Images.
  * Files and folders.
* Image previews.
* Search through clipboard history.
* Pin important items to keep them at the top of the history.
* One-click copy back to the system clipboard.
* Delete individual items or clear the entire history.
* System tray integration.
* Quick menu for fast access to recent clipboard items.
* Configurable global keyboard shortcut.
* Desktop notifications for unavailable files or images.
* Privacy filter for password managers.
* Native GTK integration with Linux desktop environments.
* File clipboard interoperability with common Linux file managers.

## Requirements

* Linux
* Python 3.12 or newer
* GTK 3
* A Linux desktop environment with GTK support
* Python GObject (PyGObject)
* python-xlib

Cinnamon Clipboard is designed to integrate well with Cinnamon, while also supporting other GTK-based desktop environments such as Xfce and MATE.

## Installation

### Debian / Ubuntu / Linux Mint

Download the latest `.deb` package from the project's GitHub Releases page.

Then install it with:

```bash
sudo apt install ./cinnamon-clipboard_1.0.0~rc1_all.deb
```

The package installs the application, desktop entry, icon, and Spanish translation.

### From source

Clone the repository:

```bash
git clone https://github.com/Vaider13/cinnamon-clipboard.git
cd cinnamon-clipboard
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies required for development:

```bash
pip install PyGObject python-xlib
```

Run the application:

```bash
python -m cinnamon_clipboard.app
```

## Building the Debian package

The repository includes a build script for creating a Debian package:

```bash
./build_deb.sh
```

The resulting `.deb` package is created in the project root.

Generated build files and `.deb` packages are intentionally excluded from version control.

## Clipboard and file handling

Text and image clipboard entries are stored in the application's local history database.

For files and folders, Cinnamon Clipboard stores their paths rather than copying the actual file contents into the history database.

This means that deleting or moving a file after it has been copied may make the corresponding history entry unavailable. When this happens, Cinnamon Clipboard displays a notification instead of silently failing.

File clipboard support uses standard X11 clipboard targets and has been tested with common Linux file managers. Compatibility may vary between file managers.

## Keyboard shortcuts

The global keyboard shortcut can be configured from the application's preferences.

The default shortcut and user-configured shortcuts depend on the Cinnamon desktop environment and its existing global keybindings.

## Data and privacy

Cinnamon Clipboard stores its clipboard history locally.

No cloud service or external account is required.

Clipboard contents remain on the local machine unless the user explicitly copies or moves them elsewhere.

The application also provides a privacy filter intended to prevent password managers and other sensitive applications from being stored in the clipboard history.

## Project status

Cinnamon Clipboard is currently in **Release Candidate 1 (RC1)**.

The project is functional and usable, but additional testing and refinement may still take place before the first stable release.

## License

Cinnamon Clipboard is free software licensed under the **GNU General Public License, version 3 or later (GPL-3.0-or-later)**.

See the [`LICENSE`](LICENSE) file for the complete license text.

## Author

**Pablo / Vaider13**

GitHub: [Vaider13](https://github.com/Vaider13)
