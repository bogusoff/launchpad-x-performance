from __future__ import absolute_import, print_function, unicode_literals

import Live
from ableton.v2.base import liveobj_valid, task
from ableton.v2.control_surface import Component
from ableton.v2.control_surface.input_control_element import ScriptForwarding
from ableton.v2.control_surface.components.clip_slot import find_nearest_color
from ableton.v2.control_surface.elements import Color
from novation.colors import Blink, CLIP_COLOR_TABLE, RGB_COLOR_TABLE, Rgb

from .scene_stop import SCENE_HOLD_SECONDS, exclude_clip_slot_from_pending_scene_stop


CLIP_SELECTOR_EMPTY_COLOR = Color(0)
CLIP_SELECTOR_SELECTED_EMPTY_COLOR = Blink(Color(0), Color(Rgb.WHITE.midi_value))
CLIP_SELECTOR_PLAYING_COLOR = Color(Rgb.GREEN.midi_value)
CLIP_SELECTOR_SELECTED_PLAYING_COLOR = Blink(Color(Rgb.GREEN.midi_value), Color(Rgb.WHITE.midi_value))
CLIP_SELECTOR_TRIGGERED_COLOR = Rgb.GREEN_BLINK
DRUM_COLOR = Color(Rgb.BLUE.midi_value)
DRUM_SELECTED_COLOR = Color(Rgb.AQUA.midi_value)
DRUM_SELECTED_BLINK_COLOR = Color(Rgb.RED.midi_value)
STEP_COLOR = Color(Rgb.WHITE_HALF.midi_value)
STEP_ON_COLOR = Color(Rgb.WHITE.midi_value)
STEP_PLAYHEAD_COLOR = Color(Rgb.AQUA.midi_value)
PATTERN_COLOR = Color(Rgb.PALE_GREEN_HALF.midi_value)
PATTERN_SELECTED_COLOR = Color(Rgb.RED_HALF.midi_value)
BAR_FILLED_COLOR = Color(Rgb.LIGHT_BLUE.midi_value)
BAR_EMPTY_COLOR = Color(Rgb.BLUE.midi_value)
BAR_BEYOND_COLOR = Color(Rgb.DARK_BLUE_HALF.midi_value)
BAR_SELECTED_COLOR = Color(Rgb.GREEN.midi_value)
DRUM_PLAYBACK_COLOR = Color(Rgb.YELLOW.midi_value)
COMMAND_CLEAR_COLOR = Color(Rgb.RED.midi_value)
COMMAND_ERASE_COLOR = Color(Rgb.ORANGE.midi_value)
COMMAND_COPY_COLOR = Color(Rgb.LIGHT_BLUE.midi_value)
COMMAND_VELOCITY_FIXED_COLOR = Color(Rgb.BLUE.midi_value)
COMMAND_VELOCITY_SENSITIVE_COLOR = Color(Rgb.WHITE.midi_value)
COMMAND_OCTAVE_DEFAULT_COLOR = Color(Rgb.GREEN.midi_value)
COMMAND_OCTAVE_ACTIVE_COLOR = Color(Rgb.RED.midi_value)
OFF_COLOR = Color(0)
DRUM_BASE_NOTE = 36
DRUM_NATIVE_CHANNEL = 9
DRUM_PAD_VELOCITY = 100
DRUM_NOTE_COUNT = 16
STEP_COUNT = 16
STEP_DURATION = 0.25
STEP_EPSILON = 0.01
STEP_VELOCITY = 127
INITIAL_TRACK_INDEX = 0
INITIAL_SCENE_INDEX = 0
CLIP_SELECTOR_TRACKS = 4
CLIP_SELECTOR_SCENES = 4
PLAYHEAD_REFRESH = 0.04
BAR_LENGTH = 4.0
BAR_COUNT = 8
BAR_BLINK_REFRESH = 0.35
DRUM_FLASH_MIN_SECONDS = 0.06


class DrumModeLayoutManager(object):
    def __init__(self, surface, component):
        self._surface = surface
        self._component = component
        self._component.set_native_routing_surface(surface)
        self._component.set_drum_pad_logger(self._log_pad)
        self._component.set_session_window_offsets(
            self._session_ring_track_offset(),
            self._session_ring_scene_offset(),
        )
        self._surface._mixer_modes.add_selected_mode_listener(self._on_mode_changed)
        self._surface._session_modes.add_selected_mode_listener(self._on_mode_changed)
        self._surface._main_modes.add_selected_mode_listener(self._on_mode_changed)
        self._add_session_ring_offset_listener()
        self._refresh()

    def _on_mode_changed(self, *_):
        self._refresh()

    def _on_session_ring_offset_changed(self, *_):
        self._component.set_session_window_offsets(
            self._session_ring_track_offset(),
            self._session_ring_scene_offset(),
        )

    def _overlay_should_be_enabled(self):
        return (
            self._surface._main_modes.selected_mode == "session"
            and self._surface._session_modes.selected_mode == "mixer"
            and self._surface._mixer_modes.selected_mode == "pan"
        )

    def _refresh(self):
        enabled = self._overlay_should_be_enabled()
        if enabled:
            self._surface._session_layout_mode()
            self._component.set_session_window_offsets(
                self._session_ring_track_offset(),
                self._session_ring_scene_offset(),
            )
        self._component.set_enabled(enabled)

    def _session_ring_track_offset(self):
        try:
            return max(0, int(self._surface._session_ring.track_offset))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return 0

    def _session_ring_scene_offset(self):
        try:
            return max(0, int(self._surface._session_ring.scene_offset))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return 0

    def _add_session_ring_offset_listener(self):
        session_ring = getattr(self._surface, "_session_ring", None)

        if session_ring is None:
            return

        try:
            if not session_ring.offset_has_listener(self._on_session_ring_offset_changed):
                session_ring.add_offset_listener(self._on_session_ring_offset_changed)
        except (AttributeError, RuntimeError, TypeError):
            pass

    def disconnect(self):
        self._remove_mode_listener(getattr(self._surface, "_mixer_modes", None))
        self._remove_mode_listener(getattr(self._surface, "_session_modes", None))
        self._remove_mode_listener(getattr(self._surface, "_main_modes", None))

        session_ring = getattr(self._surface, "_session_ring", None)

        try:
            if session_ring is not None and session_ring.offset_has_listener(
                self._on_session_ring_offset_changed
            ):
                session_ring.remove_offset_listener(self._on_session_ring_offset_changed)
        except (AttributeError, RuntimeError, TypeError):
            pass

    def _remove_mode_listener(self, modes):
        try:
            if modes.selected_mode_has_listener(self._on_mode_changed):
                modes.remove_selected_mode_listener(self._on_mode_changed)
        except (AttributeError, RuntimeError, TypeError):
            pass

    def _log_pad(self, message):
        self._log_message(message)

    def _log_message(self, message):
        try:
            self._surface.log_message(message)
        except (AttributeError, RuntimeError, TypeError):
            try:
                self._surface._c_instance.log_message(message)
            except (AttributeError, RuntimeError, TypeError):
                pass


class StaticDrumModeLayoutComponent(Component):
    def __init__(self, *a, **k):
        self._drum_bridge = k.pop("drum_bridge_manager", None)
        super(StaticDrumModeLayoutComponent, self).__init__(*a, **k)
        self._matrix = None
        self._drum_pad_logger = None
        self._clip_selector_listeners = []
        self._clip_selector_installing = False
        self._clip_slot_listeners = []
        self._clip_content_listeners = []
        self._track_state_listeners = []
        self._observed_clip_slots = []
        self._observed_tracks = []
        self._drum_pad_listeners = []
        self._native_drum_buttons = {}
        self._native_controlled_track = None
        self._surface = None
        self._step_pad_listeners = []
        self._bar_pad_listeners = []
        self._command_pad_listeners = []
        self._clear_clip_hold_task = None
        self._clear_clip_pressed = False
        self._clear_clip_long_pressed = False
        self._erase_pitch_modifier = False
        self._step_velocity_sensitive = False
        self._drum_octave_offset = 0
        self._held_drum_notes = {}
        self._selected_drum_index = 0
        self._selected_note = self._effective_note_for_drum_index(self._selected_drum_index)
        self._clip_window_track_offset = 0
        self._clip_window_scene_offset = 0
        self._selected_track_index = INITIAL_TRACK_INDEX
        self._selected_scene_index = INITIAL_SCENE_INDEX
        self._selected_bar_index = 0
        self._playhead_task = None
        self._playhead_step_index = None
        self._last_playback_position = None
        self._last_playback_clip = None
        self._bar_blink_task = None
        self._bar_blink_on = False
        self._displayed_active_drum_pitches = set()
        self._drum_flash_ticks = {}
        self._logged_step_onsets = set()

    def set_native_routing_surface(self, surface):
        self._surface = surface

    def set_drum_pad_logger(self, logger):
        self._drum_pad_logger = logger
        self._log_bridge_manager_attached()

    def set_session_window_offsets(self, track_offset, scene_offset):
        track_offset = max(0, int(track_offset))
        scene_offset = max(0, int(scene_offset))

        if (
            track_offset == self._clip_window_track_offset
            and scene_offset == self._clip_window_scene_offset
        ):
            return

        self._clip_window_track_offset = track_offset
        self._clip_window_scene_offset = scene_offset
        self._log_pad(
            "[LPX-DRUM-CLIP] window track_offset={} scene_offset={}".format(
                track_offset,
                scene_offset,
            )
        )
        self._update_clip_slot_listeners()
        self._update_track_state_listeners()
        self._update_layout()

    def set_matrix(self, matrix):
        if matrix != self._matrix:
            self._remove_clip_selector_listeners()
            self._remove_clip_slot_listeners()
            self._remove_clip_content_listeners()
            self._remove_track_state_listeners()
            self._remove_drum_pad_listeners()
            self._remove_step_pad_listeners()
            self._remove_bar_pad_listeners()
            self._remove_command_pad_listeners()
            self._matrix = matrix

        if self.is_enabled() and self._matrix is not None:
            self._install_clip_selector_listeners()
            self._update_clip_slot_listeners()
            self._update_track_state_listeners()
            self._install_drum_pad_listeners()
            self._update_native_drum_routing()
            self._install_step_pad_listeners()
            self._install_bar_pad_listeners()
            self._install_command_pad_listeners()
            self._start_playhead_task()
            self._start_bar_blink_task()
            self._update_layout()

    def update(self):
        super(StaticDrumModeLayoutComponent, self).update()
        self._update_layout()

    def on_enabled_changed(self):
        super(StaticDrumModeLayoutComponent, self).on_enabled_changed()
        if self.is_enabled():
            self._install_clip_selector_listeners()
            self._update_clip_slot_listeners()
            self._update_track_state_listeners()
            self._install_drum_pad_listeners()
            self._update_native_drum_routing()
            self._install_step_pad_listeners()
            self._install_bar_pad_listeners()
            self._install_command_pad_listeners()
            self._start_playhead_task()
            self._start_bar_blink_task()
            self._update_layout()
        else:
            self._clear_command_state()
            self._stop_playhead_task()
            self._stop_bar_blink_task()
            self._clear_active_drum_pitches()
            self._release_native_drum_routing()
            self._remove_clip_selector_listeners()
            self._remove_clip_slot_listeners()
            self._remove_clip_content_listeners()
            self._remove_track_state_listeners()
            self._remove_drum_pad_listeners()
            self._remove_step_pad_listeners()
            self._remove_bar_pad_listeners()
            self._remove_command_pad_listeners()

    def _update_layout(self):
        if not self.is_enabled() or self._matrix is None:
            return

        for button, (x, y) in self._iter_matrix_buttons():
            button.set_light(self._color_for_physical_coordinate(x, y))

        self._apply_playhead_light()

    def _clear_matrix(self):
        if self._matrix is None:
            return

        for button, _ in self._iter_matrix_buttons():
            button.set_light(OFF_COLOR)

    def _iter_matrix_buttons(self):
        width = self._matrix_dimension(self._matrix, "width")
        height = self._matrix_dimension(self._matrix, "height")
        get_button = getattr(self._matrix, "get_button", None)

        if callable(get_button) and width is not None and height is not None:
            for y in range(height):
                for x in range(width):
                    yield get_button(x, y), (x, y)
            return

        for item in self._matrix.iterbuttons():
            button, coordinate = item
            yield button, coordinate

    def _install_clip_selector_listeners(self):
        if self._matrix is None:
            return

        self._remove_clip_selector_listeners()
        self._clip_selector_installing = True

        try:
            for button, (physical_x, physical_y) in self._iter_matrix_buttons():
                local_index = self._clip_selector_index_for_coordinate(physical_x, physical_y)

                if local_index is None:
                    continue

                callback = self._make_clip_selector_callback(
                    local_index,
                    physical_x,
                    physical_y,
                )
                self._add_button_value_listener(button, callback)
                self._clip_selector_listeners.append((button, callback))
        finally:
            self._clip_selector_installing = False

    def _install_drum_pad_listeners(self):
        if self._matrix is None:
            return

        self._remove_drum_pad_listeners()

        for button, (physical_x, physical_y) in self._iter_matrix_buttons():
            logical_x, logical_y = self._logical_coordinate(physical_x, physical_y)
            drum_index = self._drum_index_for_coordinate(logical_x, logical_y)

            if drum_index is None:
                continue

            callback = self._make_drum_pad_callback(button, drum_index)
            self._add_button_value_listener(button, callback)
            self._drum_pad_listeners.append((button, callback))

        self._update_native_drum_routing()

    def _install_step_pad_listeners(self):
        if self._matrix is None:
            return

        self._remove_step_pad_listeners()

        for button, (physical_x, physical_y) in self._iter_matrix_buttons():
            logical_x, logical_y = self._logical_coordinate(physical_x, physical_y)
            step_index = self._step_index_for_coordinate(logical_x, logical_y)

            if step_index is None:
                continue

            callback = self._make_step_pad_callback(step_index)
            self._add_button_value_listener(button, callback)
            self._step_pad_listeners.append((button, callback))

    def _install_bar_pad_listeners(self):
        if self._matrix is None:
            return

        self._remove_bar_pad_listeners()

        for button, (physical_x, physical_y) in self._iter_matrix_buttons():
            logical_x, logical_y = self._logical_coordinate(physical_x, physical_y)
            bar_index = self._bar_index_for_coordinate(logical_x, logical_y)

            if bar_index is None:
                continue

            callback = self._make_bar_pad_callback(bar_index)
            self._add_button_value_listener(button, callback)
            self._bar_pad_listeners.append((button, callback))

    def _install_command_pad_listeners(self):
        if self._matrix is None:
            return

        self._remove_command_pad_listeners()

        for button, (physical_x, physical_y) in self._iter_matrix_buttons():
            logical_x, logical_y = self._logical_coordinate(physical_x, physical_y)
            command_index = self._command_index_for_coordinate(logical_x, logical_y)

            if command_index is None:
                continue

            callback = self._make_command_pad_callback(command_index)
            self._add_button_value_listener(button, callback)
            self._command_pad_listeners.append((button, callback))

    def _remove_clip_selector_listeners(self):
        for button, callback in self._clip_selector_listeners:
            try:
                if button.value_has_listener(callback):
                    button.remove_value_listener(callback)
            except (AttributeError, RuntimeError, TypeError):
                try:
                    button.remove_value_listener(callback)
                except (AttributeError, RuntimeError, TypeError):
                    pass

        self._clip_selector_listeners = []

    def _update_clip_slot_listeners(self):
        if self._matrix is None or not self.is_enabled():
            return

        self._remove_clip_slot_listeners()
        self._remove_clip_content_listeners()

        for track_index, scene_index in self._visible_clip_addresses():
            clip_slot = self._clip_slot_at_address(track_index, scene_index)

            if not liveobj_valid(clip_slot):
                continue

            self._add_object_listener(
                clip_slot,
                "has_clip",
                self._on_clip_selector_state_changed,
                self._clip_slot_listeners,
            )
            self._add_object_listener(
                clip_slot,
                "color",
                self._on_clip_selector_state_changed,
                self._clip_slot_listeners,
            )
            self._observed_clip_slots.append(clip_slot)

            if getattr(clip_slot, "has_clip", False):
                clip = clip_slot.clip

                if liveobj_valid(clip):
                    for event_name in ("color", "playing_status", "is_recording"):
                        self._add_object_listener(
                            clip,
                            event_name,
                            self._on_clip_selector_state_changed,
                            self._clip_content_listeners,
                        )

    def _remove_clip_slot_listeners(self):
        self._remove_object_listeners(self._clip_slot_listeners)
        self._clip_slot_listeners = []
        self._observed_clip_slots = []
        self._remove_clip_content_listeners()

    def _remove_clip_content_listeners(self):
        self._remove_object_listeners(self._clip_content_listeners)
        self._clip_content_listeners = []

    def _update_track_state_listeners(self):
        tracks = [
            track
            for track_index in range(
                self._clip_window_track_offset,
                self._clip_window_track_offset + CLIP_SELECTOR_TRACKS,
            )
            for track in (self._track_at_index(track_index),)
            if liveobj_valid(track)
        ]

        if tracks == self._observed_tracks:
            return

        self._remove_track_state_listeners()
        self._observed_tracks = tracks

        for track in self._observed_tracks:
            for event_name in ("playing_slot_index", "fired_slot_index", "clip_slots"):
                self._add_object_listener(
                    track,
                    event_name,
                    self._on_clip_selector_state_changed,
                    self._track_state_listeners,
                )

    def _remove_track_state_listeners(self):
        self._remove_object_listeners(self._track_state_listeners)
        self._track_state_listeners = []
        self._observed_tracks = []

    def _add_object_listener(self, obj, event_name, callback, listener_store):
        add_name = "add_{}_listener".format(event_name)
        has_name = "{}_has_listener".format(event_name)

        if obj is None or not hasattr(obj, add_name):
            return

        try:
            has_listener = getattr(obj, has_name, None)

            if has_listener is None or not has_listener(callback):
                getattr(obj, add_name)(callback)
                listener_store.append((obj, event_name, callback))
        except (AttributeError, RuntimeError, TypeError):
            pass

    def _remove_object_listeners(self, listeners):
        for obj, event_name, callback in listeners:
            remove_name = "remove_{}_listener".format(event_name)
            has_name = "{}_has_listener".format(event_name)

            try:
                if hasattr(obj, remove_name):
                    has_listener = getattr(obj, has_name, None)

                    if has_listener is None or has_listener(callback):
                        getattr(obj, remove_name)(callback)
            except (AttributeError, RuntimeError, TypeError):
                pass

    def _on_clip_selector_state_changed(self, *_):
        self._update_clip_slot_listeners()
        self._update_track_state_listeners()
        self._update_layout()

    def _remove_drum_pad_listeners(self):
        self._release_native_drum_routing()

        for button, callback in self._drum_pad_listeners:
            try:
                if button.value_has_listener(callback):
                    button.remove_value_listener(callback)
            except (AttributeError, RuntimeError, TypeError):
                try:
                    button.remove_value_listener(callback)
                except (AttributeError, RuntimeError, TypeError):
                    pass

        self._drum_pad_listeners = []
        self._held_drum_notes = {}

    def _remove_step_pad_listeners(self):
        for button, callback in self._step_pad_listeners:
            try:
                if button.value_has_listener(callback):
                    button.remove_value_listener(callback)
            except (AttributeError, RuntimeError, TypeError):
                try:
                    button.remove_value_listener(callback)
                except (AttributeError, RuntimeError, TypeError):
                    pass

        self._step_pad_listeners = []

    def _remove_bar_pad_listeners(self):
        for button, callback in self._bar_pad_listeners:
            try:
                if button.value_has_listener(callback):
                    button.remove_value_listener(callback)
            except (AttributeError, RuntimeError, TypeError):
                try:
                    button.remove_value_listener(callback)
                except (AttributeError, RuntimeError, TypeError):
                    pass

        self._bar_pad_listeners = []

    def _remove_command_pad_listeners(self):
        for button, callback in self._command_pad_listeners:
            try:
                if button.value_has_listener(callback):
                    button.remove_value_listener(callback)
            except (AttributeError, RuntimeError, TypeError):
                try:
                    button.remove_value_listener(callback)
                except (AttributeError, RuntimeError, TypeError):
                    pass

        self._command_pad_listeners = []

    def _add_button_value_listener(self, button, callback):
        try:
            if not button.value_has_listener(callback):
                button.add_value_listener(callback)
        except (AttributeError, RuntimeError, TypeError):
            button.add_value_listener(callback)

    def _make_drum_pad_callback(self, button, drum_index):
        def callback(value):
            self._on_drum_pad_value(button, drum_index, value)

        return callback

    def _make_step_pad_callback(self, step_index):
        def callback(value):
            self._on_step_pad_value(step_index, value)

        return callback

    def _make_bar_pad_callback(self, bar_index):
        def callback(value):
            self._on_bar_pad_value(bar_index, value)

        return callback

    def _make_command_pad_callback(self, command_index):
        def callback(value):
            self._on_command_pad_value(command_index, value)

        return callback

    def _make_clip_selector_callback(self, local_index, physical_x, physical_y):
        def callback(value):
            self._on_clip_selector_value(local_index, physical_x, physical_y, value)

        return callback

    def _on_drum_pad_value(self, button, drum_index, value):
        drum_name = "D{:02d}".format(drum_index + 1)
        note = self._effective_note_for_drum_index(drum_index)

        if value > 0:
            if self._erase_pitch_modifier:
                self._select_drum(drum_index)
                self._erase_pitch_from_selected_bar(note)
                return

            self._held_drum_notes[button] = note
            button.set_light(DRUM_SELECTED_COLOR)
            self._select_drum(drum_index)
            self._log_pad(
                "[LPX-DRUM-NATIVE] pad={} drum_index={} original_id={} translated_note={}".format(
                    drum_name,
                    drum_index,
                    self._original_identifier_for_button(button),
                    note,
                )
            )
            self._log_pad(
                "[LPX-DRUM-PAD] press drum={} note={} velocity={}".format(
                    drum_name,
                    note,
                    DRUM_PAD_VELOCITY,
                )
            )
            return

        if button in self._held_drum_notes:
            del self._held_drum_notes[button]

        button.set_light(self._color_for_drum_index(drum_index))
        self._log_pad("[LPX-DRUM-NATIVE] pad note={} release".format(note))
        self._log_pad("[LPX-DRUM-PAD] release drum={} note={}".format(drum_name, note))

    def _on_step_pad_value(self, step_index, value):
        if value > 0:
            self._toggle_step(step_index, value)

    def _on_bar_pad_value(self, bar_index, value):
        if value <= 0:
            return

        if self._erase_pitch_modifier:
            self._erase_selected_bar(bar_index)
            return

        self._selected_bar_index = max(0, min(BAR_COUNT - 1, int(bar_index)))
        self._clear_playhead()
        self._log_pad(
            "[LPX-DRUM-BAR] selected=BAR{} index={}".format(
                self._selected_bar_index + 1,
                self._selected_bar_index,
            )
        )
        self._update_layout()
        self._update_playhead()

    def _on_command_pad_value(self, command_index, value):
        if command_index == 0:
            self._on_clear_clip_command_value(value)
        elif command_index == 1:
            self._on_erase_pitch_command_value(value)
        elif value > 0 and command_index == 2:
            self._copy_selected_bar_to_next_bar()
        elif value > 0 and command_index == 5:
            self._toggle_step_velocity_mode()
        elif value > 0 and command_index == 6:
            self._change_drum_octave(-1)
        elif value > 0 and command_index == 7:
            self._change_drum_octave(1)

    def _on_clear_clip_command_value(self, value):
        if value > 0:
            self._clear_clip_pressed = True
            self._clear_clip_long_pressed = False
            self._kill_clear_clip_hold_task()

            self._clear_clip_hold_task = self._tasks.add(
                task.sequence(
                    task.wait(SCENE_HOLD_SECONDS),
                    task.run(self._clear_clip_if_still_held),
                )
            )
            return

        self._clear_clip_pressed = False
        self._kill_clear_clip_hold_task()

        if self._clear_clip_long_pressed:
            self._clear_clip_long_pressed = False

    def _on_erase_pitch_command_value(self, value):
        modifier_enabled = value > 0

        if self._erase_pitch_modifier == modifier_enabled:
            return

        self._erase_pitch_modifier = modifier_enabled
        self._held_drum_notes = {}
        self._update_native_drum_routing()
        self._update_layout()

    def _clear_clip_if_still_held(self):
        self._clear_clip_hold_task = None

        if not self._clear_clip_pressed:
            return

        self._clear_clip_long_pressed = True
        self._clear_selected_clip_notes()

    def _kill_clear_clip_hold_task(self):
        if self._clear_clip_hold_task is not None:
            self._clear_clip_hold_task.kill()
            self._clear_clip_hold_task = None

    def _clear_command_state(self):
        self._clear_clip_pressed = False
        self._clear_clip_long_pressed = False
        self._erase_pitch_modifier = False
        self._kill_clear_clip_hold_task()

    def _toggle_step_velocity_mode(self):
        self._step_velocity_sensitive = not self._step_velocity_sensitive

        if self._step_velocity_sensitive:
            self._log_pad("[LPX-DRUM-VELOCITY] mode=sensitive")
        else:
            self._log_pad("[LPX-DRUM-VELOCITY] mode=fixed velocity=127")

        self._update_layout()

    def _on_clip_selector_value(self, local_index, physical_x, physical_y, value):
        local_track, local_scene = self._clip_selector_local_address(local_index)
        track_index = self._clip_window_track_offset + local_track
        scene_index = self._clip_window_scene_offset + local_scene

        if value <= 0:
            return

        pressed_key = (track_index, scene_index)
        selected_before = (
            self._selected_track_index,
            self._selected_scene_index,
        )
        track = self._track_at_index(track_index)
        clip_slot = self._clip_slot_at_address(track_index, scene_index)
        has_clip = bool(liveobj_valid(clip_slot) and getattr(clip_slot, "has_clip", False))
        is_midi = self._track_supports_midi(track)
        self._selected_track_index = track_index
        self._selected_scene_index = scene_index
        self._clear_playhead()
        self._highlight_clip_slot(track, clip_slot)
        self._update_native_drum_routing()
        self._log_pad(
            "[LPX-DRUM-CLIP] map physical=({},{}) old=({},{}) final=({},{}) track={} scene={}".format(
                physical_x,
                physical_y,
                *self._clip_selector_previous_coordinates_for_physical_coordinate(
                    physical_x,
                    physical_y,
                ),
                local_track,
                local_scene,
                track_index,
                scene_index,
            )
        )
        self._log_pad(
            "[LPX-DRUM-CLIP] select local=({},{}) track={} scene={} track_name={} has_clip={} midi={}".format(
                local_track,
                local_scene,
                track_index,
                scene_index,
                getattr(track, "name", None),
                has_clip,
                is_midi,
            )
        )
        self._log_clip_selector_color(track_index, scene_index, clip_slot)
        self._exclude_clip_slot_from_scene_stop(clip_slot, scene_index)

        if self._clip_selector_installing:
            pass
        elif pressed_key != selected_before:
            pass
        else:
            self._toggle_clip_slot_playback(track, clip_slot, scene_index)

        self._update_layout()
        self._update_playhead()

    def _select_drum(self, drum_index):
        self._selected_drum_index = drum_index
        self._selected_note = self._effective_note_for_drum_index(drum_index)
        self._log_pad(
            "[LPX-DRUM-SELECT] drum=D{:02d} note={}".format(
                drum_index + 1,
                self._selected_note,
            )
        )
        self._update_layout()

    def _toggle_step(self, step_index, velocity_value):
        clip = self._pattern_clip(create=True)

        if clip is None:
            return

        step_time = self._step_time(clip, step_index)
        step_name = "S{:02d}".format(step_index + 1)
        old_length = self._clip_length_bars(clip)

        if self._step_has_note(clip, self._selected_note, step_time):
            self._remove_step_note(clip, self._selected_note, step_time)
            action = "remove"
        else:
            velocity = self._step_note_velocity(velocity_value)
            self._ensure_clip_can_accept_note_at(clip, step_time)
            self._add_step_note(clip, self._selected_note, step_time, velocity)
            action = "add"
            self._log_pad(
                "[LPX-DRUM-STEP] add step={} pitch={} velocity={}".format(
                    step_name,
                    self._selected_note,
                    velocity,
                )
            )

        self._log_pad(
            "[LPX-DRUM-STEP] toggle step={} note={} action={} time={}".format(
                step_name,
                self._selected_note,
                action,
                step_time,
            )
        )
        self._normalize_clip_loop_length(clip, old_length=old_length)
        self._update_layout()

    def _clear_selected_clip_notes(self):
        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return

        old_length = self._clip_length_bars(clip)
        self._remove_all_notes_in_clip(clip)
        self._logged_step_onsets = set()
        self._clear_playhead()
        self._clear_active_drum_pitches()
        self._normalize_clip_loop_length(clip, old_length=old_length)
        self._log_pad(
            "[LPX-DRUM-EDIT] clear clip track={} scene={}".format(
                self._selected_track_index,
                self._selected_scene_index,
            )
        )
        self._update_layout()

    def _erase_pitch_from_selected_bar(self, pitch):
        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return

        old_length = self._clip_length_bars(clip)
        bar_start = self._bar_start_time(clip, self._selected_bar_index)
        removed = len(self._notes_for_pitch_in_bar(clip, pitch, bar_start))
        self._remove_notes_for_pitch_in_bar(clip, pitch, bar_start)
        self._logged_step_onsets = set()
        self._clear_playhead()
        self._clear_active_drum_pitches()
        self._normalize_clip_loop_length(clip, old_length=old_length)
        self._log_pad(
            "[LPX-DRUM-EDIT] erase_pitch bar={} pitch={} removed={}".format(
                self._selected_bar_index + 1,
                pitch,
                removed,
            )
        )
        self._update_layout()

    def _erase_selected_bar(self, bar_index):
        bar_index = max(0, min(BAR_COUNT - 1, int(bar_index)))
        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return

        old_length = self._clip_length_bars(clip)
        bar_start = self._bar_start_time(clip, bar_index)
        removed = len(self._notes_for_bar(clip, bar_start))
        self._remove_notes_in_bar(clip, bar_start)
        self._logged_step_onsets = set()
        self._clear_playhead()
        self._clear_active_drum_pitches()
        self._normalize_clip_loop_length(clip, old_length=old_length)
        self._log_pad(
            "[LPX-DRUM-EDIT] erase_bar bar={} removed={}".format(
                bar_index + 1,
                removed,
            )
        )
        self._update_layout()

    def _copy_selected_bar_to_next_bar(self):
        if self._selected_bar_index >= BAR_COUNT - 1:
            self._log_pad(
                "[LPX-DRUM-EDIT] copy ignored source_bar=8 reason=no_destination"
            )
            return

        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return

        old_length = self._clip_length_bars(clip)
        source_bar = self._selected_bar_index
        dest_bar = source_bar + 1
        source_start = self._bar_start_time(clip, source_bar)
        dest_start = self._bar_start_time(clip, dest_bar)
        notes = self._notes_for_bar(clip, source_start)

        self._remove_notes_in_bar(clip, dest_start)
        if notes:
            self._ensure_clip_can_accept_note_at(clip, dest_start + BAR_LENGTH - STEP_DURATION)
        self._add_copied_notes_to_bar(clip, notes, source_start, dest_start)
        self._normalize_clip_loop_length(clip, old_length=old_length)
        self._logged_step_onsets = set()
        self._log_pad(
            "[LPX-DRUM-EDIT] copy source_bar={} dest_bar={} notes={}".format(
                source_bar + 1,
                dest_bar + 1,
                len(notes),
            )
        )
        self._update_layout()

    def _change_drum_octave(self, delta):
        new_offset = self._drum_octave_offset + int(delta)

        if not self._octave_offset_is_valid(new_offset):
            return

        self._drum_octave_offset = new_offset
        self._selected_note = self._effective_note_for_drum_index(
            self._selected_drum_index
        )
        self._held_drum_notes = {}
        self._clear_active_drum_pitches()
        self._update_native_drum_routing()
        low_note = self._effective_note_for_drum_index(0)
        high_note = self._effective_note_for_drum_index(DRUM_NOTE_COUNT - 1)
        self._log_pad(
            "[LPX-DRUM-OCTAVE] offset={} range={}..{}".format(
                self._drum_octave_offset,
                low_note,
                high_note,
            )
        )
        self._update_layout()

    def _start_playhead_task(self):
        if (
            self._playhead_task is not None
            or not self.is_enabled()
        ):
            return

        self._playhead_task = self._tasks.add(
            task.loop(
                task.wait(PLAYHEAD_REFRESH),
                task.run(self._update_playhead),
            )
        )

    def _stop_playhead_task(self):
        if self._playhead_task is not None:
            self._playhead_task.kill()
            self._playhead_task = None

        self._clear_playhead()

    def _start_bar_blink_task(self):
        if (
            self._bar_blink_task is not None
            or not self.is_enabled()
        ):
            return

        self._bar_blink_task = self._tasks.add(
            task.loop(
                task.wait(BAR_BLINK_REFRESH),
                task.run(self._update_bar_blink),
            )
        )

    def _stop_bar_blink_task(self):
        if self._bar_blink_task is not None:
            self._bar_blink_task.kill()
            self._bar_blink_task = None

        self._bar_blink_on = False
        self._repaint_bar(self._selected_bar_index)

    def _update_bar_blink(self):
        self._bar_blink_on = not self._bar_blink_on
        self._repaint_bar(self._selected_bar_index)

    def _repaint_bar(self, bar_index):
        if bar_index is None or self._matrix is None or not self.is_enabled():
            return

        button = self._button_for_bar_index(bar_index)

        if button is not None:
            button.set_light(self._color_for_bar_index(bar_index))

    def _button_for_bar_index(self, bar_index):
        for button, (physical_x, physical_y) in self._iter_matrix_buttons():
            logical_x, logical_y = self._logical_coordinate(physical_x, physical_y)

            if self._bar_index_for_coordinate(logical_x, logical_y) == bar_index:
                return button

        return None

    def _update_playhead(self):
        step_index = self._current_playhead_step()
        active_drum_pitches = self._current_active_drum_pitches()

        if step_index == self._playhead_step_index:
            self._update_active_drum_pitches(active_drum_pitches)
            return

        previous_step = self._playhead_step_index
        self._playhead_step_index = step_index

        self._repaint_step(previous_step)
        self._repaint_step(step_index)
        self._update_active_drum_pitches(active_drum_pitches)

        if step_index is not None:
            self._log_pad(
                "[LPX-DRUM-PLAYHEAD] step=S{:02d} position={}".format(
                    step_index + 1,
                    self._current_clip_position(),
                )
            )

    def _clear_playhead(self):
        previous_step = self._playhead_step_index
        self._playhead_step_index = None
        self._last_playback_position = None
        self._last_playback_clip = None
        self._repaint_step(previous_step)

    def _current_playhead_step(self):
        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return None

        if not getattr(self.song, "is_playing", False) or not getattr(clip, "is_playing", False):
            return None

        try:
            playing_position = float(clip.playing_position)
            selected_bar_start = float(clip.loop_start) + self._selected_bar_index * BAR_LENGTH
            selected_bar_end = selected_bar_start + BAR_LENGTH
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None

        if playing_position < selected_bar_start or playing_position >= selected_bar_end:
            return None

        relative = playing_position - selected_bar_start
        step_index = int(relative / STEP_DURATION)
        return max(0, min(STEP_COUNT - 1, step_index))

    def _current_clip_position(self):
        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return None

        try:
            return float(clip.playing_position)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None

    def _repaint_step(self, step_index):
        if step_index is None or self._matrix is None or not self.is_enabled():
            return

        button = self._button_for_step_index(step_index)

        if button is not None:
            button.set_light(self._color_for_step_index(step_index))

    def _button_for_step_index(self, step_index):
        for button, (physical_x, physical_y) in self._iter_matrix_buttons():
            logical_x, logical_y = self._logical_coordinate(physical_x, physical_y)

            if self._step_index_for_coordinate(logical_x, logical_y) == step_index:
                return button

        return None

    def _apply_playhead_light(self):
        if self._playhead_step_index is not None:
            self._repaint_step(self._playhead_step_index)

    def _current_active_drum_pitches(self):
        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            self._last_playback_position = None
            self._last_playback_clip = None
            return set()

        if not getattr(self.song, "is_playing", False) or not getattr(clip, "is_playing", False):
            self._last_playback_position = None
            self._last_playback_clip = None
            return set()

        try:
            loop_start = float(clip.loop_start)
            loop_end = float(clip.loop_end)
            playing_position = self._position_in_loop(
                float(clip.playing_position),
                loop_start,
                loop_end,
            )
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self._last_playback_position = None
            self._last_playback_clip = None
            return set()

        previous_position = self._last_playback_position

        if clip != self._last_playback_clip:
            previous_position = None

        self._last_playback_clip = clip
        self._last_playback_position = playing_position

        if previous_position is None:
            return set()

        crossed_pitches = set()

        for note in self._drum_notes_for_loop(clip, loop_start, loop_end):
            try:
                pitch = int(note.pitch)
                note_start = float(note.start_time)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue

            if self._onset_was_crossed(
                note_start,
                previous_position,
                self._position_in_loop(note_start, loop_start, loop_end),
                loop_start,
                loop_end,
            ):
                crossed_pitches.add(pitch)
                self._log_active_drum_onset(pitch, note_start)

        return crossed_pitches

    def _drum_notes_for_loop(self, clip, loop_start, loop_end):
        low_note = self._effective_note_for_drum_index(0)

        try:
            return clip.get_notes_extended(
                low_note,
                DRUM_NOTE_COUNT,
                loop_start,
                max(STEP_DURATION, loop_end - loop_start),
            )
        except (AttributeError, RuntimeError, TypeError):
            return ()

    def _position_in_loop(self, position, loop_start, loop_end):
        loop_length = loop_end - loop_start

        if loop_length <= 0.0:
            return position

        return loop_start + ((position - loop_start) % loop_length)

    def _onset_was_crossed(self, note_start, previous_position, position, loop_start, loop_end):
        if loop_end <= loop_start:
            return False

        if previous_position <= position:
            return previous_position < note_start <= position

        return previous_position < note_start < loop_end or loop_start <= note_start <= position

    def _update_active_drum_pitches(self, active_pitches):
        minimum_ticks = max(1, int(DRUM_FLASH_MIN_SECONDS / PLAYHEAD_REFRESH) + 1)

        for pitch in active_pitches:
            self._drum_flash_ticks[pitch] = minimum_ticks

        for pitch in list(self._drum_flash_ticks.keys()):
            if pitch in active_pitches:
                continue

            self._drum_flash_ticks[pitch] -= 1

            if self._drum_flash_ticks[pitch] <= 0:
                del self._drum_flash_ticks[pitch]

        displayed_pitches = set(active_pitches)
        displayed_pitches.update(self._drum_flash_ticks.keys())

        changed_pitches = self._displayed_active_drum_pitches ^ displayed_pitches

        if not changed_pitches:
            return

        self._displayed_active_drum_pitches = displayed_pitches

        for pitch in sorted(changed_pitches):
            self._repaint_drum_pitch(pitch)

            if pitch in displayed_pitches:
                self._log_active_drum("note_on", pitch)
            else:
                self._log_active_drum("note_off", pitch)

    def _clear_active_drum_pitches(self):
        previous_pitches = set(self._displayed_active_drum_pitches)
        self._displayed_active_drum_pitches = set()
        self._drum_flash_ticks = {}

        for pitch in previous_pitches:
            self._repaint_drum_pitch(pitch)
            self._log_active_drum("note_off", pitch)

    def _repaint_drum_pitch(self, pitch):
        drum_index = self._drum_index_for_effective_note(pitch)

        if drum_index < 0 or drum_index >= DRUM_NOTE_COUNT:
            return

        button = self._button_for_drum_index(drum_index)

        if button is not None:
            button.set_light(self._color_for_drum_index(drum_index))

    def _button_for_drum_index(self, drum_index):
        for button, (physical_x, physical_y) in self._iter_matrix_buttons():
            logical_x, logical_y = self._logical_coordinate(physical_x, physical_y)

            if self._drum_index_for_coordinate(logical_x, logical_y) == drum_index:
                return button

        return None

    def _log_active_drum(self, action, pitch):
        drum_index = self._drum_index_for_effective_note(pitch)

        if drum_index < 0 or drum_index >= DRUM_NOTE_COUNT:
            return

        self._log_pad(
            "[LPX-DRUM-ACTIVE] {} drum=D{:02d} note={}".format(
                action,
                drum_index + 1,
                pitch,
            )
        )

    def _log_active_drum_onset(self, pitch, note_start):
        self._log_pad(
            "[LPX-DRUM-ACTIVE] onset pitch={} time={}".format(
                pitch,
                note_start,
            )
        )

    def _pattern_clip(self, log_errors=True, create=False):
        track = self._selected_track()

        if not liveobj_valid(track):
            if log_errors:
                self._log_pad("[LPX-DRUM-STEP] no_selected_track")
            return None

        if not self._track_supports_midi(track):
            if log_errors:
                self._log_pad(
                    "[LPX-DRUM-CLIP] unsupported track={} reason=not_midi".format(
                        getattr(track, "name", None)
                    )
                )
            return None

        clip_slot = self._selected_clip_slot()

        if not liveobj_valid(clip_slot):
            if log_errors:
                self._log_pad(
                    "[LPX-DRUM-STEP] no_clip_slot track={} scene={}".format(
                        self._selected_track_index,
                        self._selected_scene_index,
                    )
                )
            return None

        if not getattr(clip_slot, "has_clip", False):
            if create and self._create_midi_clip(
                clip_slot,
                self._selected_track_index,
                self._selected_scene_index,
            ):
                self._update_clip_slot_listeners()
                self._update_track_state_listeners()
            else:
                if log_errors:
                    self._log_pad(
                        "[LPX-DRUM-STEP] no_clip track={} scene={}".format(
                            self._selected_track_index,
                            self._selected_scene_index,
                        )
                    )
                return None

        if not getattr(clip_slot, "has_clip", False):
            if log_errors:
                self._log_pad(
                    "[LPX-DRUM-STEP] no_clip track={} scene={}".format(
                        self._selected_track_index,
                        self._selected_scene_index,
                    )
                )
            return None

        clip = clip_slot.clip

        if not getattr(clip, "is_midi_clip", False):
            if log_errors:
                self._log_pad(
                    "[LPX-DRUM-STEP] clip_not_midi track={} scene={}".format(
                        self._selected_track_index,
                        self._selected_scene_index,
                    )
                )
            return None

        return clip

    def _create_midi_clip(self, clip_slot, track_index, scene_index):
        try:
            clip_slot.create_clip(BAR_LENGTH)
            self._log_pad(
                "[LPX-DRUM-CLIP] create track={} scene={} length={}".format(
                    track_index,
                    scene_index,
                    BAR_LENGTH,
                )
            )
            return True
        except (AttributeError, RuntimeError, TypeError):
            return False

    def _selected_track(self):
        return self._track_at_index(self._selected_track_index)

    def _update_native_drum_routing(self):
        if self._matrix is None or not self.is_enabled():
            self._release_native_drum_routing()
            return

        if self._erase_pitch_modifier:
            self._release_native_drum_routing()
            return

        track = self._selected_track()

        if not self._track_supports_midi(track):
            self._release_native_drum_routing()
            self._log_native_selected_track(track, controlled=False)
            return

        if track != self._native_controlled_track:
            self._release_controlled_track()
            self._set_controlled_track(track)

        self._enable_native_drum_buttons()

    def _set_controlled_track(self, track):
        if not liveobj_valid(track) or self._surface is None:
            return

        try:
            self._surface.set_controlled_track(track)
            self._native_controlled_track = track
            self._log_native_selected_track(track, controlled=True)
        except (AttributeError, RuntimeError, TypeError):
            self._native_controlled_track = None

    def _release_controlled_track(self):
        track = self._native_controlled_track

        if self._surface is not None:
            try:
                self._surface.release_controlled_track()
            except (AttributeError, RuntimeError, TypeError):
                pass

        if liveobj_valid(track):
            self._log_pad(
                "[LPX-DRUM-NATIVE] release track={} name={}".format(
                    self._track_index(track),
                    getattr(track, "name", None),
                )
            )

        self._native_controlled_track = None

    def _enable_native_drum_buttons(self):
        current_buttons = {}

        for button, (physical_x, physical_y) in self._iter_matrix_buttons():
            logical_x, logical_y = self._logical_coordinate(physical_x, physical_y)
            drum_index = self._drum_index_for_coordinate(logical_x, logical_y)

            if drum_index is None:
                continue

            current_buttons[button] = self._effective_note_for_drum_index(drum_index)

        for button in list(self._native_drum_buttons.keys()):
            if button not in current_buttons:
                self._restore_native_drum_button(button)

        for button, note in current_buttons.items():
            self._enable_native_drum_button(button, note)

    def _enable_native_drum_button(self, button, note):
        state = self._native_drum_buttons.get(button)

        if state is None:
            state = self._capture_native_drum_button_state(button)
            self._native_drum_buttons[button] = state

        try:
            self._set_button_identifier(button, int(note))
            self._set_button_channel(button, DRUM_NATIVE_CHANNEL)
            button.enabled = True
            button.script_forwarding = ScriptForwarding.non_consuming
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _capture_native_drum_button_state(self, button):
        return {
            "identifier": getattr(button, "identifier", None),
            "original_identifier": getattr(button, "original_identifier", None),
            "channel": getattr(button, "channel", None),
            "original_channel": getattr(button, "original_channel", None),
            "enabled": getattr(button, "enabled", None),
            "script_forwarding": getattr(button, "script_forwarding", None),
        }

    def _restore_native_drum_button(self, button):
        state = self._native_drum_buttons.pop(button, None)

        if state is None:
            return

        try:
            self._set_button_identifier(
                button,
                self._state_value(state, "identifier", "original_identifier"),
            )
            self._set_button_channel(
                button,
                self._state_value(state, "channel", "original_channel"),
            )
            if state["script_forwarding"] is not None:
                button.script_forwarding = state["script_forwarding"]
            if state["enabled"] is not None:
                button.enabled = state["enabled"]
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _set_button_identifier(self, button, identifier):
        if identifier is None:
            return

        set_identifier = getattr(button, "set_identifier", None)

        if callable(set_identifier):
            set_identifier(int(identifier))
            return

        button.identifier = int(identifier)

    def _set_button_channel(self, button, channel):
        if channel is None:
            return

        set_channel = getattr(button, "set_channel", None)

        if callable(set_channel):
            set_channel(int(channel))
            return

        button.channel = int(channel)

    def _state_value(self, state, name, fallback_name):
        value = state.get(name)

        if value is not None:
            return value

        return state.get(fallback_name)

    def _original_identifier_for_button(self, button):
        state = self._native_drum_buttons.get(button, {})
        value = self._state_value(state, "original_identifier", "identifier")

        if value is not None:
            return value

        return getattr(button, "original_identifier", getattr(button, "identifier", None))

    def _release_native_drum_routing(self):
        for button in list(self._native_drum_buttons.keys()):
            self._restore_native_drum_button(button)

        self._release_controlled_track()

    def _log_native_selected_track(self, track, controlled):
        if not liveobj_valid(track):
            self._log_pad("[LPX-DRUM-NATIVE] selected track=None")
            return

        track_index = self._track_index(track)
        self._log_pad(
            "[LPX-DRUM-NATIVE] selected track={} name={}".format(
                track_index,
                getattr(track, "name", None),
            )
        )

        if controlled:
            self._log_pad(
                "[LPX-DRUM-NATIVE] controlled track={} name={}".format(
                    track_index,
                    getattr(track, "name", None),
                )
            )

    def _track_index(self, track):
        try:
            return list(self.song.tracks).index(track)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None

    def _selected_clip_slot(self):
        return self._clip_slot_at_address(
            self._selected_track_index,
            self._selected_scene_index,
        )

    def _track_at_index(self, track_index):
        tracks = getattr(self.song, "tracks", ())

        if track_index < 0 or track_index >= len(tracks):
            return None

        return tracks[track_index]

    def _clip_slot_at_address(self, track_index, scene_index):
        track = self._track_at_index(track_index)

        if not liveobj_valid(track):
            return None

        clip_slots = getattr(track, "clip_slots", ())

        if scene_index < 0 or scene_index >= len(clip_slots):
            return None

        return clip_slots[scene_index]

    def _visible_clip_addresses(self):
        for local_scene in range(CLIP_SELECTOR_SCENES):
            for local_track in range(CLIP_SELECTOR_TRACKS):
                yield (
                    self._clip_window_track_offset + local_track,
                    self._clip_window_scene_offset + local_scene,
                )

    def _clip_selector_local_address(self, local_index):
        local_index = max(
            0,
            min(CLIP_SELECTOR_TRACKS * CLIP_SELECTOR_SCENES - 1, int(local_index)),
        )
        return local_index % CLIP_SELECTOR_TRACKS, local_index // CLIP_SELECTOR_TRACKS

    def _track_supports_midi(self, track):
        return bool(liveobj_valid(track) and getattr(track, "has_midi_input", False))

    def _highlight_clip_slot(self, track, clip_slot):
        if not liveobj_valid(clip_slot):
            return

        try:
            if liveobj_valid(track):
                self.song.view.selected_track = track
            self.song.view.highlighted_clip_slot = clip_slot
        except (AttributeError, RuntimeError, TypeError):
            pass

    def _toggle_clip_slot_playback(self, track, clip_slot, scene_index):
        if (
            not liveobj_valid(track)
            or not liveobj_valid(clip_slot)
            or not getattr(clip_slot, "has_clip", False)
        ):
            return

        clip = clip_slot.clip

        if not liveobj_valid(clip):
            return

        try:
            if clip.is_playing:
                clip.stop()
            else:
                clip_slot.fire()
        except (AttributeError, RuntimeError, TypeError):
            pass

    def _exclude_clip_slot_from_scene_stop(self, clip_slot, scene_index):
        local_scene_index = scene_index - self._clip_window_scene_offset
        scene_component = self._scene_component_for_local_scene(local_scene_index)
        exclude_clip_slot_from_pending_scene_stop(
            clip_slot,
            scene_component=scene_component,
        )

    def _scene_component_for_local_scene(self, local_scene_index):
        if self._surface is None:
            return None

        try:
            return self._surface._session._scenes[int(local_scene_index)]
        except (AttributeError, RuntimeError, TypeError, IndexError, ValueError):
            return None

    def _target_track(self):
        if self._drum_bridge is None:
            return None

        return getattr(self._drum_bridge, "target_track", None)

    def _step_time(self, clip, step_index):
        return (
            float(clip.loop_start)
            + self._selected_bar_index * BAR_LENGTH
            + step_index * STEP_DURATION
        )

    def _step_has_note(self, clip, pitch, step_time):
        step_end = step_time + STEP_DURATION

        for note in self._notes_for_step(clip, pitch, step_time):
            try:
                note_start = float(note.start_time)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue

            if step_time <= note_start < step_end:
                self._log_step_onset(pitch, note_start, step_time)
                return True

        return False

    def _notes_for_step(self, clip, pitch, step_time):
        try:
            return clip.get_notes_extended(pitch, 1, step_time, STEP_DURATION)
        except (AttributeError, RuntimeError, TypeError):
            return ()

    def _step_note_velocity(self, velocity_value):
        if not self._step_velocity_sensitive:
            return STEP_VELOCITY

        try:
            return max(1, min(127, int(velocity_value)))
        except (TypeError, ValueError):
            return STEP_VELOCITY

    def _add_step_note(self, clip, pitch, step_time, velocity):
        note = Live.Clip.MidiNoteSpecification(
            pitch=int(pitch),
            start_time=float(step_time),
            duration=STEP_DURATION,
            velocity=int(velocity),
        )
        clip.add_new_notes((note,))

    def _remove_step_note(self, clip, pitch, step_time):
        clip.remove_notes_extended(pitch, 1, step_time, STEP_DURATION)
        self._logged_step_onsets = set()

    def _remove_all_notes_in_clip(self, clip):
        try:
            span = max(
                BAR_LENGTH,
                float(getattr(clip, "length", 0.0)),
                float(getattr(clip, "end_marker", 0.0)),
                float(getattr(clip, "loop_end", 0.0)),
            )
            clip.remove_notes_extended(0, 128, 0.0, span)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _bar_start_time(self, clip, bar_index):
        return float(clip.loop_start) + max(0, int(bar_index)) * BAR_LENGTH

    def _notes_for_pitch_in_bar(self, clip, pitch, bar_start):
        try:
            return tuple(clip.get_notes_extended(int(pitch), 1, bar_start, BAR_LENGTH))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return ()

    def _remove_notes_for_pitch_in_bar(self, clip, pitch, bar_start):
        try:
            clip.remove_notes_extended(int(pitch), 1, bar_start, BAR_LENGTH)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _notes_for_bar(self, clip, bar_start):
        notes = []
        bar_end = bar_start + BAR_LENGTH

        try:
            candidates = clip.get_notes_extended(0, 128, bar_start, BAR_LENGTH)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return notes

        for note in candidates:
            try:
                note_start = float(note.start_time)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue

            if bar_start <= note_start < bar_end:
                notes.append(note)

        return notes

    def _remove_notes_in_bar(self, clip, bar_start):
        try:
            clip.remove_notes_extended(0, 128, bar_start, BAR_LENGTH)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _add_copied_notes_to_bar(self, clip, notes, source_start, dest_start):
        if not notes:
            return

        copied_notes = []

        for note in notes:
            copied_note = self._copy_note_to_start(note, source_start, dest_start)

            if copied_note is not None:
                copied_notes.append(copied_note)

        if copied_notes:
            try:
                clip.add_new_notes(tuple(copied_notes))
            except (AttributeError, RuntimeError, TypeError):
                pass

    def _copy_note_to_start(self, note, source_start, dest_start):
        try:
            kwargs = dict(
                pitch=int(note.pitch),
                start_time=float(dest_start) + (float(note.start_time) - float(source_start)),
                duration=float(note.duration),
                velocity=int(note.velocity),
            )
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None

        for name in (
            "mute",
            "probability",
            "velocity_deviation",
            "release_velocity",
        ):
            if hasattr(note, name):
                kwargs[name] = getattr(note, name)

        while True:
            try:
                return Live.Clip.MidiNoteSpecification(**kwargs)
            except TypeError:
                optional_names = [
                    name
                    for name in (
                        "mute",
                        "probability",
                        "velocity_deviation",
                        "release_velocity",
                    )
                    if name in kwargs
                ]

                if not optional_names:
                    return None

                del kwargs[optional_names[-1]]

    def _log_step_onset(self, pitch, note_start, step_time):
        try:
            clip = self._pattern_clip(log_errors=False)
            selected_bar_start = float(clip.loop_start) + self._selected_bar_index * BAR_LENGTH
            step_index = int((step_time - selected_bar_start) / STEP_DURATION)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            step_index = None

        key = (pitch, note_start, step_index)

        if key in self._logged_step_onsets:
            return

        self._logged_step_onsets.add(key)
        self._log_pad(
            "[LPX-DRUM-NOTE] step pitch={} onset={} step={}".format(
                pitch,
                note_start,
                step_index,
            )
        )

    def _ensure_clip_can_accept_note_at(self, clip, step_time):
        try:
            required_end = step_time + STEP_DURATION

            if required_end > float(clip.loop_end):
                clip.loop_end = required_end
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _normalize_clip_loop_length(self, clip, old_length=None):
        if old_length is None:
            old_length = self._clip_length_bars(clip)

        new_length = self._effective_clip_length_bars(clip)

        if old_length == new_length:
            return

        try:
            clip.loop_end = float(clip.loop_start) + new_length * BAR_LENGTH
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return

        if new_length > old_length:
            self._log_pad(
                "[LPX-DRUM-BAR] expanded old={} new={}".format(
                    old_length,
                    new_length,
                )
            )
        else:
            self._log_pad(
                "[LPX-DRUM-BAR] shrunk old={} new={}".format(
                    old_length,
                    new_length,
                )
            )

    def _clip_length_bars(self, clip):
        try:
            loop_length = max(0.0, float(clip.loop_end) - float(clip.loop_start))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return 1

        return max(1, min(BAR_COUNT, int((loop_length + BAR_LENGTH - STEP_EPSILON) / BAR_LENGTH)))

    def _effective_clip_length_bars(self, clip):
        highest_bar = -1

        for note in self._all_notes_in_bar_range(clip):
            try:
                note_start = float(note.start_time)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue

            bar_index = self._bar_index_for_note_start(clip, note_start)

            if bar_index is not None:
                highest_bar = max(highest_bar, bar_index)

        return max(1, highest_bar + 1)

    def _all_notes_in_bar_range(self, clip):
        try:
            return clip.get_notes_extended(
                0,
                128,
                float(clip.loop_start),
                BAR_COUNT * BAR_LENGTH,
            )
        except (AttributeError, RuntimeError, TypeError):
            return ()

    def _bar_index_for_note_start(self, clip, note_start):
        try:
            relative = note_start - float(clip.loop_start)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None

        if relative < -STEP_EPSILON or relative >= BAR_COUNT * BAR_LENGTH:
            return None

        return max(0, min(BAR_COUNT - 1, int(max(0.0, relative) / BAR_LENGTH)))

    def _send_note_on(self, note):
        return self._drum_bridge.send_note_on(
            note,
            DRUM_PAD_VELOCITY,
            source="live_pad",
        )

    def _send_note_off(self, note):
        return self._drum_bridge.send_note_off(note, source="live_pad")

    def _bridge_available(self):
        return (
            self._drum_bridge is not None
            and getattr(self._drum_bridge, "has_target", False)
        )

    def _matrix_dimension(self, matrix, name):
        if matrix is None:
            return None

        dimension = getattr(matrix, name, None)
        if callable(dimension):
            return dimension()

        return dimension

    def _logical_coordinate(self, x, y):
        return y, x

    def _color_for_physical_coordinate(self, x, y):
        clip_selector_index = self._clip_selector_index_for_coordinate(x, y)

        if clip_selector_index is not None:
            return self._color_for_clip_selector_index(clip_selector_index)

        logical_x, logical_y = self._logical_coordinate(x, y)
        return self._color_for_coordinate(logical_x, logical_y)

    def _color_for_coordinate(self, x, y):
        if y == 7:
            command_index = self._command_index_for_coordinate(x, y)
            return self._color_for_command_index(command_index)

        if y == 6:
            bar_index = self._bar_index_for_coordinate(x, y)
            return self._color_for_bar_index(bar_index)

        if y >= 4:
            step_index = self._step_index_for_coordinate(x, y)
            return self._color_for_step_index(step_index)

        if x >= 4:
            drum_index = self._drum_index_for_coordinate(x, y)
            return self._color_for_drum_index(drum_index)

        return OFF_COLOR

    def _clip_selector_index_for_coordinate(self, x, y):
        coordinates = self._clip_selector_coordinates_for_physical_coordinate(x, y)

        if coordinates is None:
            return None

        cx, cy = coordinates
        return cy * CLIP_SELECTOR_TRACKS + cx

    def _clip_selector_coordinates_for_physical_coordinate(self, x, y):
        coordinates = self._clip_selector_previous_coordinates_for_physical_coordinate(x, y)

        if coordinates is None:
            return None

        cx, cy = coordinates
        return CLIP_SELECTOR_TRACKS - 1 - cx, CLIP_SELECTOR_SCENES - 1 - cy

    def _clip_selector_previous_coordinates_for_physical_coordinate(self, x, y):
        if x < 0 or x >= CLIP_SELECTOR_TRACKS or y < 0 or y >= CLIP_SELECTOR_SCENES:
            return None

        rotated_x = CLIP_SELECTOR_TRACKS - 1 - y
        rotated_y = x
        return rotated_x, CLIP_SELECTOR_SCENES - 1 - rotated_y

    def _color_for_clip_selector_index(self, local_index):
        if local_index is None:
            return CLIP_SELECTOR_EMPTY_COLOR

        local_track, local_scene = self._clip_selector_local_address(local_index)
        track_index = self._clip_window_track_offset + local_track
        scene_index = self._clip_window_scene_offset + local_scene
        clip_slot = self._clip_slot_at_address(track_index, scene_index)

        if not liveobj_valid(clip_slot):
            return CLIP_SELECTOR_EMPTY_COLOR

        is_selected = (
            track_index == self._selected_track_index
            and scene_index == self._selected_scene_index
        )
        has_clip = bool(getattr(clip_slot, "has_clip", False))
        clip = clip_slot.clip if has_clip else None
        is_playing = bool(liveobj_valid(clip) and getattr(clip, "is_playing", False))
        is_triggered = bool(liveobj_valid(clip) and getattr(clip, "is_triggered", False))
        is_stop_triggered = self._clip_selector_stop_is_triggered(
            track_index,
            scene_index,
        )

        if is_stop_triggered:
            return "Session.StopClipTriggered"

        if is_triggered:
            return CLIP_SELECTOR_TRIGGERED_COLOR

        if is_selected and is_playing:
            return CLIP_SELECTOR_SELECTED_PLAYING_COLOR

        if is_playing:
            return CLIP_SELECTOR_PLAYING_COLOR

        if is_selected and not has_clip:
            return CLIP_SELECTOR_SELECTED_EMPTY_COLOR

        base_color = self._clip_selector_base_color(clip_slot, clip)

        if is_selected:
            return Blink(base_color, Color(Rgb.WHITE.midi_value))

        return base_color

    def _clip_selector_stop_is_triggered(self, track_index, scene_index):
        track = self._track_at_index(track_index)

        if not liveobj_valid(track):
            return False

        try:
            return (
                track.fired_slot_index == -2
                and track.playing_slot_index == scene_index
            )
        except (AttributeError, RuntimeError, TypeError):
            return False

    def _clip_selector_base_color(self, clip_slot, clip):
        if not liveobj_valid(clip):
            return CLIP_SELECTOR_EMPTY_COLOR

        clip_color = getattr(clip, "color", None)

        if clip_color is None:
            clip_color = getattr(clip_slot, "color", None)

        return self._clip_color_to_led(clip_color)

    def _clip_color_to_led(self, clip_color):
        if clip_color is None:
            return CLIP_SELECTOR_EMPTY_COLOR

        try:
            return Color(CLIP_COLOR_TABLE[clip_color])
        except (KeyError, IndexError, TypeError):
            try:
                return Color(find_nearest_color(RGB_COLOR_TABLE, clip_color))
            except (AttributeError, RuntimeError, TypeError, ValueError):
                return CLIP_SELECTOR_EMPTY_COLOR

    def _log_clip_selector_color(self, track_index, scene_index, clip_slot):
        if not liveobj_valid(clip_slot) or not getattr(clip_slot, "has_clip", False):
            return

        clip = clip_slot.clip
        clip_color = getattr(clip, "color", None) if liveobj_valid(clip) else None
        led_color = self._clip_selector_base_color(clip_slot, clip)
        self._log_pad(
            "[LPX-DRUM-CLIP] color track={} scene={} clip_color={} led_value={}".format(
                track_index,
                scene_index,
                clip_color,
                self._color_log_value(led_color),
            )
        )

    def _color_log_value(self, color):
        return getattr(color, "midi_value", repr(color))

    def _drum_index_for_coordinate(self, x, y):
        if x < 4 or y > 3:
            return None

        return (3 - y) * 4 + (x - 4)

    def _color_for_drum_index(self, drum_index):
        if drum_index is None:
            return DRUM_COLOR

        base_color = self._base_color_for_drum_index(drum_index)

        if drum_index == self._selected_drum_index:
            return Blink(DRUM_SELECTED_BLINK_COLOR, base_color)

        return base_color

    def _base_color_for_drum_index(self, drum_index):
        pitch = self._effective_note_for_drum_index(drum_index)

        if pitch in self._displayed_active_drum_pitches:
            return DRUM_PLAYBACK_COLOR

        if self._drum_pitch_has_notes(pitch):
            return DRUM_PLAYBACK_COLOR

        return DRUM_COLOR

    def _drum_pitch_has_notes(self, pitch):
        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return False

        try:
            return bool(
                clip.get_notes_extended(
                    int(pitch),
                    1,
                    float(clip.loop_start),
                    BAR_COUNT * BAR_LENGTH,
                )
            )
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False

    def _command_index_for_coordinate(self, x, y):
        if y != 7:
            return None

        return max(0, min(7, int(x)))

    def _color_for_command_index(self, command_index):
        if command_index == 0:
            return COMMAND_CLEAR_COLOR

        if command_index == 1:
            return COMMAND_ERASE_COLOR

        if command_index == 2:
            return COMMAND_COPY_COLOR

        if command_index == 5:
            return (
                COMMAND_VELOCITY_SENSITIVE_COLOR
                if self._step_velocity_sensitive
                else COMMAND_VELOCITY_FIXED_COLOR
            )

        if command_index in (6, 7):
            return self._color_for_octave_command_index(command_index)

        return OFF_COLOR

    def _color_for_octave_command_index(self, command_index):
        if command_index == 6:
            return (
                COMMAND_OCTAVE_ACTIVE_COLOR
                if self._drum_octave_offset < 0
                else COMMAND_OCTAVE_DEFAULT_COLOR
            )

        return (
            COMMAND_OCTAVE_ACTIVE_COLOR
            if self._drum_octave_offset > 0
            else COMMAND_OCTAVE_DEFAULT_COLOR
        )

    def _effective_note_for_drum_index(self, drum_index):
        return DRUM_BASE_NOTE + int(drum_index) + self._drum_octave_offset * 12

    def _drum_index_for_effective_note(self, pitch):
        return int(pitch) - self._effective_note_for_drum_index(0)

    def _octave_offset_is_valid(self, offset):
        return (
            DRUM_BASE_NOTE + offset * 12 >= 0
            and DRUM_BASE_NOTE + (DRUM_NOTE_COUNT - 1) + offset * 12 <= 127
        )

    def _step_index_for_coordinate(self, x, y):
        if y < 4 or y > 5:
            return None

        return x + (y - 4) * 8

    def _bar_index_for_coordinate(self, x, y):
        if y != 6:
            return None

        return max(0, min(BAR_COUNT - 1, int(x)))

    def _color_for_bar_index(self, bar_index):
        if bar_index is None:
            return BAR_BEYOND_COLOR

        if bar_index == self._selected_bar_index and self._bar_blink_on:
            return BAR_SELECTED_COLOR

        return self._base_color_for_bar_index(bar_index)

    def _base_color_for_bar_index(self, bar_index):
        effective_length = self._effective_clip_length_bars_for_current_clip()

        if bar_index >= effective_length:
            return BAR_BEYOND_COLOR

        if self._bar_has_notes(bar_index):
            return BAR_FILLED_COLOR

        return BAR_EMPTY_COLOR

    def _effective_clip_length_bars_for_current_clip(self):
        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return 1

        return self._effective_clip_length_bars(clip)

    def _bar_has_notes(self, bar_index):
        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return False

        bar_start = float(clip.loop_start) + bar_index * BAR_LENGTH

        try:
            return bool(clip.get_notes_extended(0, 128, bar_start, BAR_LENGTH))
        except (AttributeError, RuntimeError, TypeError):
            return False

    def _step_is_on(self, step_index):
        if step_index is None:
            return False

        clip = self._pattern_clip(log_errors=False)

        if clip is None:
            return False

        return self._step_has_note(
            clip,
            self._selected_note,
            self._step_time(clip, step_index),
        )

    def _color_for_step_index(self, step_index):
        step_on = self._step_is_on(step_index)

        if step_index == self._playhead_step_index:
            return STEP_ON_COLOR if step_on else STEP_PLAYHEAD_COLOR

        return STEP_ON_COLOR if step_on else STEP_COLOR

    def _log_pad(self, message):
        if self._drum_pad_logger is None:
            return

        self._drum_pad_logger(message)

    def _log_bridge_manager_attached(self):
        self._log_pad(
            "[LPX-DRUM-PAD] bridge_manager_attached={}".format(
                self._drum_bridge is not None
            )
        )

    def disconnect(self):
        self._clear_command_state()
        self._stop_playhead_task()
        self._stop_bar_blink_task()
        self._clear_active_drum_pitches()
        self._remove_clip_selector_listeners()
        self._remove_clip_slot_listeners()
        self._remove_track_state_listeners()
        self._remove_drum_pad_listeners()
        self._remove_step_pad_listeners()
        self._remove_bar_pad_listeners()
        self._remove_command_pad_listeners()
        super(StaticDrumModeLayoutComponent, self).disconnect()
