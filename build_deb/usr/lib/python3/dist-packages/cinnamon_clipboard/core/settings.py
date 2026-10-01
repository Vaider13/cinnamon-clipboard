import json
import os
import logging
from pathlib import Path
from ..i18n import _

logger = logging.getLogger(__name__)


class SettingsManager:
    """Handles persistence of application settings in JSON format."""

    DEFAULTS = {
        "max_history": 50,
        "autostart": False,
        "save_images": True,
        "save_files": True,
        "enable_history": True,
        "shortcut": "<Ctrl><Alt>v",
    }

    def __init__(self):
        config_dir = Path.home() / ".config" / "cinnamon-clipboard"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_dir / "config.json"
        self.settings = self.DEFAULTS.copy()
        self.config_was_reset = False
        self.load()

    def load(self):
        """Load and validate the configuration, restoring default values if it is invalid."""
        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("The configuration does not contain a valid JSON object.")

            valid = True

            if "max_history" in data and data["max_history"] not in (10, 25, 50):
                valid = False

            for key in ("autostart", "save_images", "save_files", "enable_history"):
                if key in data and not isinstance(data[key], bool):
                    valid = False

            if "shortcut" in data and not isinstance(data["shortcut"], str):
                valid = False

            if not valid:
                raise ValueError("One or more configuration values are invalid.")

            self.settings.update(data)

        except Exception as e:

            self.settings = self.DEFAULTS.copy()
            self.config_was_reset = True
            self.save()

    def save(self):
        """Save the current settings to the JSON file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error("Failed to save config.json: %s", e)

    def get(self, key):
        return self.settings.get(key, self.DEFAULTS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def set_autostart(self, enable):
        """Create or remove the .desktop file in ~/.config/autostart for automatic startup with the session."""
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_file = autostart_dir / "cinnamon-clipboard.desktop"

        if enable:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            content = f"""[Desktop Entry]
Type=Application
Name=Cinnamon Clipboard
Comment={_("Clipboard manager for Cinnamon")}
Exec=cinnamon-clipboard
Icon=cinnamon-clipboard
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
"""
            try:
                with open(autostart_file, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                logger.error("Failed to create autostart .desktop file: %s", e)
        else:
            if autostart_file.exists():
                try:
                    autostart_file.unlink()
                except Exception as e:
                    logger.error("Failed to delete autostart .desktop file: %s", e)

        self.set("autostart", enable)