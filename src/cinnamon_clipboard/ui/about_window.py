import gi

import logging

logger = logging.getLogger(__name__)

from pathlib import Path

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gtk, GdkPixbuf

from ..i18n import _


class AboutWindow(Gtk.AboutDialog):
    """Displays Cinnamon Clipboard information."""

    def __init__(self, parent=None):
        super().__init__()

        self.set_wmclass("cinnamon-clipboard", "CinnamonClipboard")

        self.set_transient_for(parent)
        self.set_modal(True)

        self.set_program_name("Cinnamon Clipboard")
        self.set_version("1.0.0 RC1")
        self.set_comments(_("Clipboard manager for Linux desktops."))
        self.set_copyright("© 2026 Vaider13")
        self.set_website("https://github.com/Vaider13/cinnamon-clipboard")
        self.set_website_label("GitHub")
        self.set_authors(["Pablo / Vaider13"])

        # 1. Load the app's native icon using Pixbuf
        icon_path = Path("/usr/share/icons/hicolor/512x512/apps/cinnamon-clipboard.png")
        if not icon_path.exists():
            # Fallback for the local development environment
            icon_path = Path(__file__).parent.parent.parent / "data" / "icons" / "cinnamon-clipboard.png"

        if icon_path.exists():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(icon_path), 128, 128, True
                )
                self.set_logo(pixbuf)
            except Exception as e:
                logger.warning("Failed to load icon in AboutDialog: %s", e)
        else:
            self.set_logo_icon_name("cinnamon-clipboard")

        # 2. Assign the explicit license text so the "License" button responds correctly
        license_text = _(
            "Cinnamon Clipboard is free software: you can redistribute it and/or modify it "
            "under the terms of the GNU General Public License as published by the "
            "Free Software Foundation, either version 3 of the License, or "
            "(at your option) any later version.\n\n"
            "This program is distributed in the hope that it will be useful, "
            "but WITHOUT ANY WARRANTY; without even the implied warranty of "
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. "
            "See the GNU General Public License for more details."
        )
        self.set_license(license_text)
        self.set_wrap_license(True)

        self.connect("response", self._on_response)

    def _on_response(self, dialog, response_id):
        """Close the window when the user responds to the dialog."""
        self.destroy()