
import json
import logging
import re
import threading
import urllib.request

from gi.repository import Gio, GLib, Gtk

from ._version import __version__
from .i18n import _
from .installation import PACKAGE_MANAGED

logger = logging.getLogger(__name__)

RELEASES_URL = (
    "https://api.github.com/repos/"
    "Vaider13/cinnamon-clipboard/releases/latest"
)


def _version_tuple(version):
    """Convert a version string into a comparable tuple."""
    version = version.strip().lstrip("v")

    if not re.fullmatch(r"\d+(?:\.\d+)*", version):
        return None

    return tuple(int(part) for part in version.split("."))


def _fetch_latest_release():
    """Fetch release information from GitHub."""
    request = urllib.request.Request(
        RELEASES_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Cinnamon-Clipboard",
        },
    )

    with urllib.request.urlopen(request, timeout=5) as response:
        release = json.loads(response.read().decode("utf-8"))

    version = release.get("tag_name", "")
    url = release.get("html_url", "")

    if (
        _version_tuple(version) is None
        or not url.startswith("https://github.com/Vaider13/cinnamon-clipboard/")
    ):
        raise ValueError("Invalid GitHub release information")

    return {
        "version": version,
        "url": url,
        "body": release.get("body") or "",
        "is_newer": _version_tuple(version) > _version_tuple(__version__),
    }


def _show_update_notification(app, release):
    """Show a native desktop notification for a newer release."""
    notification = Gio.Notification.new(_("Cinnamon Clipboard update available"))
    notification.set_body(
        _("Version %(version)s is available.")
        % {"version": release["version"]}
    )
    notification.set_icon(
        Gio.ThemedIcon.new("cinnamon-clipboard")
    )
    notification.add_button_with_target(
        _("View release"),
        "app.view-release",
        GLib.Variant.new_string(release["url"]),
    )

    app.send_notification("cinnamon-clipboard-update", notification)
    return GLib.SOURCE_REMOVE


def check_for_updates(app, callback=None, notify_if_new=True):
    """Check for updates asynchronously.

    callback receives (status, release), where status is:
    'update', 'current', or 'error'.
    """
    if PACKAGE_MANAGED:
        return

    def worker():
        try:
            release = _fetch_latest_release()
            status = "update" if release["is_newer"] else "current"
        except Exception as exc:
            logger.debug("Update check unavailable: %s", exc)
            release = None
            status = "error"

        def finish():
            if status == "update" and notify_if_new:
                _show_update_notification(app, release)

            if callback is not None:
                callback(status, release)

            return GLib.SOURCE_REMOVE

        GLib.idle_add(finish)

    threading.Thread(target=worker, daemon=True).start()
