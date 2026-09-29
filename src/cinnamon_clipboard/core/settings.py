import json
import os
from pathlib import Path
from ..i18n import _


class SettingsManager:
    """Maneja la persistencia de las configuraciones de la aplicación en formato JSON."""

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
        """Carga y valida la configuración, restaurando los valores predeterminados si es inválida."""
        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("La configuración no contiene un objeto JSON válido.")

            valid = True

            if "max_history" in data and data["max_history"] not in (10, 25, 50):
                valid = False

            for key in ("autostart", "save_images", "save_files", "enable_history"):
                if key in data and not isinstance(data[key], bool):
                    valid = False

            if "shortcut" in data and not isinstance(data["shortcut"], str):
                valid = False

            if not valid:
                raise ValueError("Uno o más valores de configuración son inválidos.")

            self.settings.update(data)

        except Exception as e:
            print(f"[ERROR] Configuración inválida: {e}")
            print("[INFO] Restaurando configuración predeterminada.")

            self.settings = self.DEFAULTS.copy()
            self.config_was_reset = True
            self.save()

    def save(self):
        """Guarda las configuraciones actuales en el archivo JSON."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"[ERROR] No se pudo guardar config.json: {e}")

    def get(self, key):
        return self.settings.get(key, self.DEFAULTS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def set_autostart(self, enable):
        """Crea o elimina el archivo .desktop en ~/.config/autostart para el inicio automático con la sesión."""
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_file = autostart_dir / "cinnamon-clipboard.desktop"

        if enable:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            content = f"""[Desktop Entry]
Type=Application
Name=Cinnamon Clipboard
Comment={_("Clipboard manager for Cinnamon")}
Exec=python3 -m src.cinnamon_clipboard
Icon=edit-paste-symbolic
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
"""
            try:
                with open(autostart_file, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                print(f"[ERROR] No se pudo crear autostart .desktop: {e}")
        else:
            if autostart_file.exists():
                try:
                    autostart_file.unlink()
                except Exception as e:
                    print(f"[ERROR] No se pudo eliminar autostart .desktop: {e}")

        self.set("autostart", enable)