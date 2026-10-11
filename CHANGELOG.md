# Changelog

## [1.0.2] - 2026-10-11

### Added
- Added Italian, Brazilian Portuguese, French, German, Russian, and Japanese translation catalogs.
- Added localized application names and descriptions to the desktop launcher.
- Added a tooltip explaining that clearing history removes unpinned items while preserving pinned items.

### Fixed
- Prevented clearing unpinned history from deleting image files still referenced by pinned items.
- Centralized application version information in a single version source.
- Updated the Debian package build script to compile and include all available translation catalogs.

## [1.0.1] - 2026-10-11

### Fixed
- Fixed opening the About window.
- Fixed the Open application button in the quick menu.
- Centralized window management and opening.
- Fixed global keyboard shortcut updates from Preferences.

## [1.0.0] - 2026-10-10

### Added
- Clipboard history support for text, images, and files.
- Application version information through the `--version` command-line option.
- Localized application naming in the main window and system tray tooltip.

### Fixed
- Fixed duplicate clipboard history entries when the same file selection is detected repeatedly.
- Finalized application metadata and Debian package versioning for the stable release.

### Notes
- First stable release of Cinnamon Clipboard.
