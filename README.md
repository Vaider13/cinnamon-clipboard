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
- Temporary clipboard history mode for sessions where you don't want to keep a persistent history.
- Pin important items to keep them at the top of the history.
- One-click copy back to the system clipboard.
- Delete individual items or clear the entire history.
- System tray integration.
- Quick menu for fast access to recent clipboard items, with keyboard navigation, type-to-search.
- Configurable initial focus, contributed by @xsak..
- Optional automatic paste when selecting an item from the menu, contributed by @xsak.
- Configurable global keyboard shortcut.
- Desktop notifications when previously copied files or images are unavailable.
- Privacy filter for clipboard content marked as sensitive by supported password managers.
- Native GTK integration with Linux desktop environments.
- File clipboard interoperability with common Linux file managers using X11 clipboard targets.
- Automatic checks for new releases published on GitHub.
- Native desktop notifications when an update is available.
- Manual update checks and release information from the application preferences.
- Configurable automatic update checks, where supported by the installation method.

## Requirements

- Linux
- Python 3.12 or newer
- GTK 3
- Python GObject (PyGObject)
- python-xlib
- A compatible Linux desktop environment

Cinnamon Clipboard is designed primarily for Cinnamon, with support for other GTK-based desktop environments such as Xfce and MATE. File clipboard interoperability relies on X11 and may not work in Wayland sessions or with all file managers.

## Installation

### Debian / Ubuntu / Linux Mint — `.deb` package

Download the latest `.deb` package from the project's [GitHub Releases page](https://github.com/Vaider13/cinnamon-clipboard/releases).

Install it with:

```bash
sudo apt install ./cinnamon-clipboard_1.1.0_all.deb
```

The package installs the application, desktop entry, icon, and available translation catalogs.

### Ubuntu PPA

Cinnamon Clipboard is distributed through the Launchpad PPA:

**PPA:** [ppa:vaider17/cinnamon-clipboard](https://launchpad.net/~vaider17/+archive/ubuntu/cinnamon-clipboard)

The PPA targets the following Ubuntu releases:

- Ubuntu 24.04 LTS (Noble Numbat).
- Ubuntu 26.04 (Resolute Raccoon).

Add the PPA and install the application:

```bash
sudo add-apt-repository ppa:vaider17/cinnamon-clipboard
sudo apt update
sudo apt install cinnamon-clipboard
```

PPA packages must finish building and be published for your Ubuntu release before they can be installed. If a package is not yet available for your release, use the `.deb` package from GitHub Releases instead.

When installed through APT, application updates are managed by the system package manager rather than the in-app updater.

### Fedora (RPM)

Download the RPM package for Fedora:

Download the latest `.rpm` package from the project's [GitHub Releases page](https://github.com/Vaider13/cinnamon-clipboard/releases).

Install it from the terminal:

```bash
sudo dnf install ./cinnamon-clipboard-1.1.0-1.fc45.noarch.rpm
```

**Note:** The RPM package has been tested on Fedora 45 Beta with Cinnamon. Testing has been limited, and compatibility with other Fedora versions or desktop environments is not guaranteed. Bugs may occur.

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

## Languages

Cinnamon Clipboard includes translations for the following languages:

- English
- Spanish
- Hungarian contributed by @xsak.
- Italian
- Portuguese (Brazil)
- French
- German
- Russian
- Japanese

The application uses the available system locale to select the appropriate translation. English is used as the fallback when a translation is unavailable.

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

Cinnamon Clipboard 1.1.0 is a stable release.

This release introduces a temporary clipboard history mode, improves configuration saving reliability, updates the configuration dialog's visual design, and adds Hungarian translation. It also includes updated translations across all supported languages.

Thanks to **[@xsak](https://github.com/xsak)** for contributing keyboard navigation improvements.

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
