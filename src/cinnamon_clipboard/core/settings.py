import json
import os
from pathlib import Path


class SettingsManager:
    """Maneja la persistencia de las configuraciones de la aplicación en formato JSON."""

    DEFAULTS = {
        "max_history": 50,
        "autostart": False,
        "save_images": True,
        "save_files": True,
        "enable_history": True,
        "shortcut": "<Super>v",
    }

    def __init__(self):
        config_dir = Path.home() / ".config" / "cinnamon-clipboard"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_dir / "config.json"
        self.settings = self.DEFAULTS.copy()
        self.load()

    def load(self):
        """Carga las configuraciones desde el disco, completando con valores por defecto si faltan claves."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"[ERROR] No se pudo cargar config.json: {e}")

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
Comment=Gestor de portapapeles para Cinnamon
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