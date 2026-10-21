# Cinnamon Clipboard

A lightweight clipboard manager for Linux desktop environments, designed to integrate naturally with Cinnamon and other GTK-based desktops.

Cinnamon Clipboard maintains a persistent history of copied content and provides quick access to previously copied items through a system tray menu.

## Features

- Persistent clipboard history using SQLite.
- Support for:
  - Plain text.
  - Images.
  - Files and folders.
- Image previews.
- Search through clipboard history.
- Pin important items to keep them at the top of the history.
- One-click copy back to the system clipboard.
- Delete individual items or clear the entire history.
- System tray integration.
- Quick menu for fast access to recent clipboard items, with keyboard navigation, type-to-search, first-item focus, and optional automatic paste on selection.
- Configurable global keyboard shortcut.
- Desktop notifications when previously copied files or images are unavailable.
- Privacy filter for clipboard content marked as sensitive by supported password managers.
- Native GTK integration with Linux desktop environments.
- File clipboard interoperability with common Linux file managers using X11 clipboard targets.

## Requirements

- Linux
- Python 3.12 or newer
- GTK 3
- Python GObject (PyGObject)
- python-xlib
- A compatible Linux desktop environment

Cinnamon Clipboard is designed primarily for Cinnamon, with support for other GTK-based desktop environments such as Xfce and MATE. File clipboard interoperability relies on X11 and may not work in Wayland sessions or with all file managers.

## Installation

## Languages

Cinnamon Clipboard includes translations for the following languages:

- English
- Spanish
- Italian
- Portuguese (Brazil)
- French
- German
- Russian
- Japanese

The application uses the available system locale to select the appropriate translation. English is used as the fallback when a translation is unavailable.

### Debian / Ubuntu / Linux Mint

Download the latest `.deb` package from the project's [GitHub Releases page](https://github.com/Vaider13/cinnamon-clipboard/releases).

Install it with:

```bash
sudo apt install ./cinnamon-clipboard_1.0.2_all.deb
```

The package installs the application, desktop entry, icon, and available translation catalogs.

### From source

Clone the repository:

```bash
git clone https://github.com/Vaider13/cinnamon-clipboard.git
cd cinnamon-clipboard
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies required by the application:

```bash
pip install PyGObject python-xlib
```

Depending on your distribution, PyGObject may also require GTK and GObject Introspection development packages provided by the system package manager.

Run the application from the repository root:

```bash
PYTHONPATH=src python3 -m cinnamon_clipboard.app
```

Display the application version:

```bash
PYTHONPATH=src python3 -m cinnamon_clipboard.app --version
```

## Building the Debian package

The repository includes a build script for creating a Debian package:

```bash
bash build_deb.sh
```

The resulting `.deb` package is created in the project root.

Generated build files and Debian packages are intentionally excluded from version control.

## Clipboard and file handling

Text and image clipboard entries are stored in the application's local history database.

For files and folders, Cinnamon Clipboard stores their paths rather than copying the actual file contents into the history database.

Moving or deleting a file after it has been copied may make the corresponding history entry unavailable. When this happens, Cinnamon Clipboard displays a notification instead of silently failing.

File clipboard support uses X11 clipboard targets and has been tested with common Linux file managers. Compatibility may vary depending on the file manager and desktop session. Wayland compatibility for file clipboard operations is not guaranteed.

## Keyboard shortcuts

The global keyboard shortcut can be configured from the application's preferences.

Shortcut availability and behavior depend on the desktop environment and its existing global keybindings.

## Data and privacy

Cinnamon Clipboard stores its clipboard history locally. No cloud service or external account is required.

Clipboard contents are stored on the local machine unless the user explicitly copies or moves them elsewhere. As with any local clipboard history, stored content may be accessible to other processes or users who have sufficient access to the same account.

The application includes a privacy filter that checks for the `x-kde-passwordManagerHint` clipboard metadata used by supported password managers to identify sensitive content.

**This filter is a best-effort measure, not a universal security guarantee.** Not every password manager or sensitive application necessarily provides this metadata. If the metadata is missing or cannot be read, sensitive content may still be recorded in the history.

Users should not treat the privacy filter as a substitute for the security features of their password manager or operating system.

## Project status

Cinnamon Clipboard **1.0.2 is the first stable release**.

The application provides persistent clipboard history for text, images, and files, along with search, pinned items, preferences, and system tray integration.

This is an independently developed open-source project. Feedback, bug reports, and contributions are welcome.

## Development and AI assistance

A substantial part of Cinnamon Clipboard was developed with assistance from artificial intelligence tools.

AI assistance was used during implementation and problem-solving. The project was tested and refined through practical use, with development decisions, testing, corrections, and release preparation carried out as part of the project owner's work.

This disclosure is included to be transparent about how the project was developed.

## License

Cinnamon Clipboard is free software licensed under the **GNU General Public License, version 3 or later (GPL-3.0-or-later)**.

See the [`LICENSE`](LICENSE) file for the complete license text.

## Author

**Pablo / Vaider13**

GitHub: [Vaider13](https://github.com/Vaider13)

Repository: [Vaider13/cinnamon-clipboard](https://github.com/Vaider13/cinnamon-clipboard)

Releases: [Download Cinnamon Clipboard](https://github.com/Vaider13/cinnamon-clipboard/releases)