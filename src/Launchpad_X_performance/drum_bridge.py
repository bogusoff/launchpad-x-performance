from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import liveobj_valid


BRIDGE_DEVICE_NAME = "LPX Drum Bridge"
NOTE_PARAMETER_NAME = "Note"
VELOCITY_PARAMETER_NAME = "Velocity"
GATE_PARAMETER_NAME = "Gate"
TRIGGER_PARAMETER_NAME = "Trigger"


class LPXDrumBridgeTarget(object):
    def __init__(self, track=None, device=None, parameters=None):
        self.track = track
        self.device = device
        self.parameters = parameters or {}
        self._trigger_value = 0

    @property
    def valid(self):
        return bool(
            liveobj_valid(self.track)
            and liveobj_valid(self.device)
            and all(
                liveobj_valid(parameter)
                for parameter in self.parameters.values()
            )
        )

    def send_note_on(self, note, velocity):
        self._send_note(note, velocity, 1)

    def send_note_off(self, note):
        self._send_note(note, 0, 0)

    def _send_note(self, note, velocity, gate):
        if not self.valid:
            return False

        try:
            self.parameters[NOTE_PARAMETER_NAME].value = int(note)
            self.parameters[VELOCITY_PARAMETER_NAME].value = int(velocity)
            self.parameters[GATE_PARAMETER_NAME].value = int(gate)
            self._trigger_value = 1 - self._trigger_value
            self.parameters[TRIGGER_PARAMETER_NAME].value = self._trigger_value
            return True
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False


class LPXDrumBridgeManager(object):
    def __init__(self, surface=None, *a, **k):
        super(LPXDrumBridgeManager, self).__init__(*a, **k)
        self._surface = surface
        self._song = surface.song
        self._target = None
        self._song_listeners = []
        self._track_listeners = []
        self._device_listeners = []
        self._install_song_listeners()
        self.refresh_target()

    @property
    def target_track(self):
        return self._target.track if self._target is not None else None

    @property
    def has_target(self):
        return bool(self._target is not None and self._target.valid)

    def send_note_on(self, note, velocity, source="unknown"):
        self._log_message(
            "[LPX-DRUM-BRIDGE] send note_on note={} velocity={} source={}".format(
                note,
                velocity,
                source,
            )
        )
        return self.has_target and self._target.send_note_on(note, velocity)

    def send_note_off(self, note, source="unknown"):
        self._log_message(
            "[LPX-DRUM-BRIDGE] send note_off note={} source={}".format(
                note,
                source,
            )
        )
        return self.has_target and self._target.send_note_off(note)

    def refresh_target(self):
        old_track = self.target_track
        self._remove_device_listeners()
        self._target = self._find_bridge_target()
        self._install_device_listeners()

        if self.target_track != old_track:
            self._log_target()

    def _find_bridge_target(self):
        for track in self._song.tracks:
            target = self._bridge_target_for_track(track)

            if target is not None:
                return target

        return None

    def _bridge_target_for_track(self, track):
        if not liveobj_valid(track):
            return None

        for device in getattr(track, "devices", ()):
            if getattr(device, "name", None) != BRIDGE_DEVICE_NAME:
                continue

            parameters = self._bridge_parameters(device)
            if parameters is not None:
                return LPXDrumBridgeTarget(track, device, parameters)

        return None

    def _bridge_parameters(self, device):
        parameters = {}

        for parameter in getattr(device, "parameters", ()):
            name = getattr(parameter, "name", None)

            if name in (
                NOTE_PARAMETER_NAME,
                VELOCITY_PARAMETER_NAME,
                GATE_PARAMETER_NAME,
                TRIGGER_PARAMETER_NAME,
            ):
                parameters[name] = parameter

        required = (
            NOTE_PARAMETER_NAME,
            VELOCITY_PARAMETER_NAME,
            GATE_PARAMETER_NAME,
            TRIGGER_PARAMETER_NAME,
        )

        if all(name in parameters for name in required):
            return parameters

        return None

    def _install_song_listeners(self):
        self._add_listener(
            self._song,
            "tracks",
            self._on_song_tracks_changed,
            self._song_listeners,
        )
        self._install_track_listeners()

    def _install_track_listeners(self):
        for track in self._song.tracks:
            self._add_listener(track, "name", self._on_track_changed, self._track_listeners)
            self._add_listener(track, "devices", self._on_track_changed, self._track_listeners)

    def _install_device_listeners(self):
        for track in self._song.tracks:
            for device in getattr(track, "devices", ()):
                self._add_listener(device, "name", self._on_track_changed, self._device_listeners)

    def _on_song_tracks_changed(self):
        self._remove_track_listeners()
        self._install_track_listeners()
        self.refresh_target()

    def _on_track_changed(self):
        self.refresh_target()

    def _add_listener(self, obj, event_name, callback, listener_store):
        if obj is None:
            return

        add_name = "add_{}_listener".format(event_name)
        has_name = "{}_has_listener".format(event_name)

        if not hasattr(obj, add_name):
            return

        try:
            has_listener = getattr(obj, has_name, None)

            if has_listener is None or not has_listener(callback):
                getattr(obj, add_name)(callback)
                listener_store.append((obj, event_name, callback))
        except (AttributeError, RuntimeError):
            pass

    def _remove_track_listeners(self):
        self._remove_listeners(self._track_listeners)
        self._track_listeners = []

    def _remove_device_listeners(self):
        self._remove_listeners(self._device_listeners)
        self._device_listeners = []

    def _remove_listeners(self, listeners):
        for obj, event_name, callback in listeners:
            remove_name = "remove_{}_listener".format(event_name)
            has_name = "{}_has_listener".format(event_name)

            try:
                if hasattr(obj, remove_name):
                    has_listener = getattr(obj, has_name, None)

                    if has_listener is None or has_listener(callback):
                        getattr(obj, remove_name)(callback)
            except (AttributeError, RuntimeError):
                pass

    def _log_target(self):
        track_name = getattr(self.target_track, "name", None)
        if track_name is not None:
            self._log_message("[LPX-DRUM-BRIDGE] found track={}".format(track_name))
            return

        self._log_message(
            "[LPX-DRUM-BRIDGE] target_track=None"
        )

    def _log_message(self, message):
        try:
            self._surface.log_message(message)
            return
        except (AttributeError, RuntimeError, TypeError):
            pass

        try:
            self._surface._c_instance.log_message(message)
        except (AttributeError, RuntimeError, TypeError):
            pass
