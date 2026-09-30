import gettext
import locale
from pathlib import Path


# 1. Directorio de desarrollo local (relativo al repositorio)
LOCAL_DIR = Path(__file__).resolve().parent.parent.parent / "locale"

# 2. Directorio estándar de instalación en el sistema (/usr/share/locale)
SYSTEM_DIR = Path("/usr/share/locale")

# Selecciona el directorio: si existe la traducción local la usa, si no, usa la del sistema
if LOCAL_DIR.exists() and (LOCAL_DIR / "es" / "LC_MESSAGES" / "cinnamon-clipboard.mo").exists():
    LOCALE_DIR = LOCAL_DIR
else:
    LOCALE_DIR = SYSTEM_DIR

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