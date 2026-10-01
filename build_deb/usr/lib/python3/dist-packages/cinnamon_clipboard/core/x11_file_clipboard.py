"""X11 clipboard owner for file and directory selections."""

import os
import sys
from pathlib import Path
from urllib.parse import quote

from Xlib import X, Xatom, display
from Xlib.protocol import event

from gi.repository import GLib


class X11FileClipboard:
    """Publish files and directories through the X11 CLIPBOARD selection."""

    def __init__(self):
        """Initialize the X11 clipboard owner."""
        self.display = display.Display()
        self.screen = self.display.screen()

        self.window = self.screen.root.create_window(
            0,
            0,
            1,
            1,
            0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
        )

        self.window.change_attributes(
            event_mask=X.PropertyChangeMask
        )

        self.clipboard = self.display.intern_atom("CLIPBOARD")

        self.targets = self.display.intern_atom("TARGETS")
        self.multiple = self.display.intern_atom("MULTIPLE")
        self.timestamp = self.display.intern_atom("TIMESTAMP")
        self.atom_pair = self.display.intern_atom("ATOM_PAIR")

        self.mate_files = self.display.intern_atom(
            "x-special/mate-copied-files"
        )
        self.gnome_files = self.display.intern_atom(
            "x-special/gnome-copied-files"
        )
        self.uri_list = self.display.intern_atom("text/uri-list")

        self._paths = []
        self._timestamp = 0

        self._timestamp_property = self.display.intern_atom(
            "_CINNAMON_CLIPBOARD_TIMESTAMP"
        )

        # GLib source used to process X11 clipboard requests.
        self._io_watch_id = None

    def _path_to_uri(self, path):
        """Convert a local filesystem path to a file URI."""
        return "file://" + quote(
            os.path.abspath(path),
            safe="/~!$&'()*+,;=:@",
        )

    def _build_payloads(self):
        """Build payloads for the supported file clipboard targets."""
        uris = [self._path_to_uri(path) for path in self._paths]

        copied_files_payload = (
            "copy\n" + "\n".join(uris)
        ).encode("utf-8")

        uri_list_payload = (
            "\r\n".join(uris) + "\r\n"
        ).encode("utf-8")

        return {
            self.mate_files: copied_files_payload,
            self.gnome_files: copied_files_payload,
            self.uri_list: uri_list_payload,
        }

    def _supported_targets(self):
        """Return the targets supported by this clipboard owner."""
        return [
            self.targets,
            self.multiple,
            self.timestamp,
            self.mate_files,
            self.gnome_files,
            self.uri_list,
        ]

    def _get_server_timestamp(self):
        """Obtain a real X11 server timestamp."""
        self.display.flush()

        self.window.delete_property(self._timestamp_property)
        self.display.flush()

        self.window.change_property(
            self._timestamp_property,
            Xatom.STRING,
            8,
            b"timestamp",
            X.PropModeReplace,
        )
        self.display.flush()

        while True:
            received_event = self.display.next_event()

            if (
                received_event.type == X.PropertyNotify
                and received_event.atom == self._timestamp_property
            ):
                return received_event.time

    def _set_property(self, requestor, property_atom, target, data):
        """Write clipboard data to the requestor's property."""
        requestor.change_property(
            property_atom,
            target,
            8,
            data,
            X.PropModeReplace,
        )

    def _send_notify(self, request, property_atom):
        """Send a SelectionNotify event to the requesting client."""
        notify = event.SelectionNotify(
            time=request.time,
            requestor=request.requestor,
            selection=request.selection,
            target=request.target,
            property=property_atom,
        )

        request.requestor.send_event(
            notify,
            event_mask=0,
        )

        self.display.flush()

    def _handle_targets(self, request, property_atom):
        """Return the list of supported clipboard targets."""
        request.requestor.change_property(
            property_atom,
            Xatom.ATOM,
            32,
            self._supported_targets(),
            X.PropModeReplace,
        )

        return True

    def _handle_timestamp(self, request, property_atom):
        """Return the X11 timestamp associated with clipboard ownership."""
        request.requestor.change_property(
            property_atom,
            Xatom.INTEGER,
            32,
            [self._timestamp],
            X.PropModeReplace,
        )

        return True

    def _handle_file_target(self, request, property_atom):
        """Return data for a file-related clipboard target."""
        payloads = self._build_payloads()
        data = payloads.get(request.target)

        if data is None:
            return False

        self._set_property(
            request.requestor,
            property_atom,
            request.target,
            data,
        )

        return True

    def _convert_target(self, requestor, target, property_atom):
        """Convert one requested target into the corresponding property."""
        if target == self.targets:
            request = type(
                "TargetRequest",
                (),
                {"requestor": requestor},
            )()

            return self._handle_targets(
                request,
                property_atom,
            )

        if target == self.timestamp:
            request = type(
                "TargetRequest",
                (),
                {"requestor": requestor},
            )()

            return self._handle_timestamp(
                request,
                property_atom,
            )

        payloads = self._build_payloads()
        data = payloads.get(target)

        if data is None:
            return False

        self._set_property(
            requestor,
            property_atom,
            target,
            data,
        )

        return True

    def _handle_multiple(self, request):
        """Handle an X11 MULTIPLE selection request."""
        property_data = request.requestor.get_full_property(
            request.property,
            self.atom_pair,
        )

        if property_data is None:
            self._send_notify(request, X.NONE)
            return

        pairs = list(property_data.value)

        if len(pairs) % 2 != 0:
            self._send_notify(request, X.NONE)
            return

        for index in range(0, len(pairs), 2):
            target = pairs[index]
            property_atom = pairs[index + 1]

            if property_atom == X.NONE:
                continue

            success = self._convert_target(
                request.requestor,
                target,
                property_atom,
            )

            if not success:
                pairs[index + 1] = X.NONE

        request.requestor.change_property(
            request.property,
            self.atom_pair,
            32,
            pairs,
            X.PropModeReplace,
        )

        self._send_notify(
            request,
            request.property,
        )

    def _handle_selection_request(self, request):
        """Handle an X11 SelectionRequest event."""
        if request.selection != self.clipboard:
            return

        property_atom = request.property

        if property_atom == X.NONE:
            property_atom = request.target

        if request.target == self.multiple:
            self._handle_multiple(request)
            return

        if request.target == self.targets:
            success = self._handle_targets(
                request,
                property_atom,
            )
        elif request.target == self.timestamp:
            success = self._handle_timestamp(
                request,
                property_atom,
            )
        else:
            success = self._handle_file_target(
                request,
                property_atom,
            )

        if success:
            self._send_notify(
                request,
                property_atom,
            )
        else:
            self._send_notify(
                request,
                X.NONE,
            )

    def _process_x11_events(self):
        """Process pending X11 events from the GLib main loop."""
        try:
            while self.display.pending_events():
                received_event = self.display.next_event()

                if received_event.type == X.SelectionRequest:
                    self._handle_selection_request(
                        received_event
                    )

                elif received_event.type == X.SelectionClear:
                    self._stop_event_processing()
                    return False

        except Exception:
            self._stop_event_processing()
            return False

        return True

    def _start_event_processing(self):
        """Register the X11 connection with the GLib main loop."""
        if self._io_watch_id is not None:
            return

        self._io_watch_id = GLib.io_add_watch(
            self.display.fileno(),
            GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR,
            self._on_x11_io,
        )

    def _on_x11_io(self, source, condition):
        """Process X11 events when the connection becomes readable."""
        if condition & (GLib.IO_HUP | GLib.IO_ERR):
            self._stop_event_processing()
            return False

        return self._process_x11_events()

    def _stop_event_processing(self):
        """Remove the GLib watch used for X11 clipboard events."""
        if self._io_watch_id is not None:
            GLib.source_remove(self._io_watch_id)
            self._io_watch_id = None

    def set_files(self, paths):
        """Take ownership of CLIPBOARD and publish the given files."""
        valid_paths = []

        for path in paths:
            path = os.path.abspath(
                os.path.expanduser(path)
            )

            if os.path.exists(path):
                valid_paths.append(path)

        if not valid_paths:
            return False

        self._paths = valid_paths

        # Obtain a real X11 server timestamp before acquiring ownership.
        self._timestamp = self._get_server_timestamp()

        self.window.set_selection_owner(
            self.clipboard,
            self._timestamp,
        )

        self.display.flush()

        owner = self.display.get_selection_owner(
            self.clipboard
        )

        if owner is None or owner.id != self.window.id:
            return False

        self._start_event_processing()

        return True

    def run(self):
        """Process X11 clipboard requests until ownership is lost."""
        print("X11 file clipboard helper is running.")
        print("Press Ctrl+C to release the clipboard and exit.")

        try:
            while True:
                received_event = self.display.next_event()

                if received_event.type == X.SelectionRequest:
                    self._handle_selection_request(
                        received_event
                    )

                elif received_event.type == X.SelectionClear:
                    print("X11 clipboard ownership lost.")
                    return

        except KeyboardInterrupt:
            print("\nX11 file clipboard helper stopped.")

        finally:
            self._stop_event_processing()
            self.display.close()

    def close(self):
        """Release X11 clipboard resources."""
        self._stop_event_processing()

        try:
            self.display.close()
        except Exception:
            pass


def main():
    """Run the standalone file clipboard helper."""
    if len(sys.argv) < 2:
        print(
            f"Usage: {Path(sys.argv[0]).name} FILE [FILE ...]",
            file=sys.stderr,
        )
        return 1

    helper = X11FileClipboard()

    if not helper.set_files(sys.argv[1:]):
        print(
            "Failed to acquire X11 clipboard ownership.",
            file=sys.stderr,
        )
        return 1

    helper.run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())