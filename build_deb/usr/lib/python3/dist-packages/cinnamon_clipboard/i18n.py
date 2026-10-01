import gettext
import locale
from pathlib import Path


# 1. Local development directory (relative to the repository)
LOCAL_DIR = Path(__file__).resolve().parent.parent.parent / "locale"

# 2. Standard system installation directory (/usr/share/locale)
SYSTEM_DIR = Path("/usr/share/locale")

# Select the directory: if a local translation exists, use it; otherwise, use the system one
if LOCAL_DIR.exists() and (LOCAL_DIR / "es" / "LC_MESSAGES" / "cinnamon-clipboard.mo").exists():
    LOCALE_DIR = LOCAL_DIR
else:
    LOCALE_DIR = SYSTEM_DIR

# Get the system's preferred language.
system_locale = locale.getlocale()[0]

# If the language could not be detected, use English as the fallback.
language = system_locale or "en"

# Load the corresponding translation.
_translation = gettext.translation(
    "cinnamon-clipboard",
    localedir=LOCALE_DIR,
    languages=[language],
    fallback=True,
)

# Function used throughout the application to mark translatable text.
_ = _translation.gettext