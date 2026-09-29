import gettext
import locale
from pathlib import Path


# Directorio donde estarán las traducciones compiladas.
LOCALE_DIR = Path(__file__).resolve().parent.parent.parent / "locale"

# Obtiene el idioma preferido del sistema.
system_locale = locale.getlocale()[0]

# Si no se pudo detectar el idioma, usa inglés como fallback.
language = system_locale or "en"

# Carga la traducción correspondiente.
_translation = gettext.translation(
    "cinnamon-clipboard",
    localedir=LOCALE_DIR,
    languages=[language],
    fallback=True,
)

# Función que usaremos en toda la aplicación para marcar textos traducibles.
_ = _translation.gettext