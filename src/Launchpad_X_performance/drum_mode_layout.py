from __future__ import absolute_import, print_function, unicode_literals

import Live
from ableton.v2.base import liveobj_valid, task
from ableton.v2.control_surface import Component
from ableton.v2.control_surface.elements import Color
from novation.colors import Rgb


CONTROL_COLOR = Color(Rgb.CREAM.midi_value)
DRUM_COLOR = Color(Rgb.BLUE.midi_value)
DRUM_SELECTED_COLOR = Color(Rgb.AQUA.midi_value)
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
OFF_COLOR = Color(0)
DRUM_BASE_NOTE = 36
DRUM_PAD_VELOCITY = 100
DRUM_NOTE_COUNT = 16
STEP_COUNT = 16
STEP_DURATION = 0.25
STEP_EPSILON = 0.01
STEP_VELOCITY = 100
PATTERN_SLOT_INDEX = 0
PLAYHEAD_REFRESH = 0.04
BAR_LENGTH = 4.0
BAR_COUNT = 8
BAR_BLINK_REFRESH = 0.35
DRUM_FLASH_MIN_SECONDS = 0.06


class DrumModeLayoutManager(object):
    def __init__(self, surface, component):
        self._surface = surface
        self._component = component
        self._component.set_drum_pad_logger(self._log_pad)
        self._surface._mixer_modes.add_selected_mode_listener(self._on_mode_changed)
        self._surface._session_modes.add_selected_mode_listener(self._on_mode_changed)
        self._surface._main_modes.add_selected_mode_listener(self._on_mode_changed)
        self._refresh()

    def _on_mode_changed(self, *_):
        self._refresh()

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
        self._component.set_enabled(enabled)

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
        self._drum_pad_listeners = []
        self._step_pad_listeners = []
        self._bar_pad_listeners = []
        self._held_drum_notes = {}
        self._selected_drum_index = 0
        self._selected_note = DRUM_BASE_NOTE
        self._selected_bar_index = 0
        self._playhead_task = None
        self._playhead_step_index = None
        self._bar_blink_task = None
        self._bar_blink_on = False
        self._displayed_active_drum_pitches = set()
        self._drum_flash_ticks = {}

    def set_drum_pad_logger(self, logger):
        self._drum_pad_logger = logger
        self._log_bridge_manager_attached()

    def set_matrix(self, matrix):
        if matrix != self._matrix:
            self._remove_drum_pad_listeners()
            self._remove_step_pad_listeners()
            self._remove_bar_pad_listeners()
            self._matrix = matrix

        if self.is_enabled() and self._matrix is not None:
            self._install_drum_pad_listeners()
            self._install_step_pad_listeners()
            self._install_bar_pad_listeners()
            self._start_playhead_task()
            self._start_bar_blink_task()
            self._update_layout()

    def update(self):
        super(StaticDrumModeLayoutComponent, self).update()
        self._update_layout()

    def on_enabled_changed(self):
        super(StaticDrumModeLayoutComponent, self).on_enabled_changed()
        if self.is_enabled():
            self._install_drum_pad_listeners()
            self._install_step_pad_listeners()
            self._install_bar_pad_listeners()
            self._start_playhead_task()
            self._start_bar_blink_task()
            self._update_layout()
        else:
            self._stop_playhead_task()
            self._stop_bar_blink_task()
            self._clear_active_drum_pitches()
            self._remove_drum_pad_listeners()
            self._remove_step_pad_listeners()
            self._remove_bar_pad_listeners()

    def _update_layout(self):
        if not self.is_enabled() or self._matrix is None:
            return

        for button, (x, y) in self._iter_matrix_buttons():
            logical_x, logical_y = self._logical_coordinate(x, y)
            button.set_light(self._color_for_coordinate(logical_x, logical_y))

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

    def _remove_drum_pad_listeners(self):
        if self._bridge_available():
            for note in self._held_drum_notes.values():
                self._send_note_off(note)

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

    def _on_drum_pad_value(self, button, drum_index, value):
        drum_name = "D{:02d}".format(drum_index + 1)
        note = DRUM_BASE_NOTE + drum_index

        if value > 0:
            self._held_drum_notes[button] = note
            button.set_light(DRUM_SELECTED_COLOR)
            self._select_drum(drum_index)
            self._log_pad(
                "[LPX-DRUM-PAD] press drum={} note={} velocity={}".format(
                    drum_name,
                    note,
                    DRUM_PAD_VELOCITY,
                )
            )

            if not self._bridge_available():
                self._log_pad("[LPX-DRUM-PAD] bridge_unavailable drum={}".format(drum_name))
            else:
                self._send_note_on(note)
            return

        if button in self._held_drum_notes:
            del self._held_drum_notes[button]

        button.set_light(
            DRUM_SELECTED_COLOR
            if drum_index == self._selected_drum_index
            else DRUM_COLOR
        )
        self._log_pad("[LPX-DRUM-PAD] release drum={} note={}".format(drum_name, note))

        if not self._bridge_available():
            self._log_pad("[LPX-DRUM-PAD] bridge_unavailable drum={}".format(drum_name))
        else:
            self._send_note_off(note)

    def _on_step_pad_value(self, step_index, value):
        if value > 0:
            self._toggle_step(step_index)

    def _on_bar_pad_value(self, bar_index, value):
        if value <= 0:
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

    def _select_drum(self, drum_index):
        self._selected_drum_index = drum_index
        self._selected_note = DRUM_BASE_NOTE + drum_index
        self._log_pad(
            "[LPX-DRUM-SELECT] drum=D{:02d} note={}".format(
                drum_index + 1,
                self._selected_note,
            )
        )
        self._update_layout()

    def _toggle_step(self, step_index):
        clip = self._pattern_clip()

        if clip is None:
            return

        step_time = self._step_time(clip, step_index)
        step_name = "S{:02d}".format(step_index + 1)
        old_length = self._clip_length_bars(clip)

        if self._step_has_note(clip, self._selected_note, step_time):
            self._remove_step_note(clip, self._selected_note, step_time)
            action = "remove"
        else:
            self._ensure_clip_can_accept_note_at(clip, step_time)
            self._add_step_note(clip, self._selected_note, step_time)
            action = "add"

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
            return set()

        if not getattr(self.song, "is_playing", False) or not getattr(clip, "is_playing", False):
            return set()

        try:
            playing_position = float(clip.playing_position)
            loop_start = float(clip.loop_start)
            loop_end = float(clip.loop_end)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return set()

        active_pitches = set()

        for note in self._drum_notes_for_loop(clip, loop_start, loop_end):
            try:
                pitch = int(note.pitch)
                note_start = float(note.start_time)
                note_end = note_start + float(note.duration)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue

            if self._note_is_active_at_position(
                note_start,
                note_end,
                playing_position,
                loop_start,
                loop_end,
            ):
                active_pitches.add(pitch)

        return active_pitches

    def _drum_notes_for_loop(self, clip, loop_start, loop_end):
        try:
            return clip.get_notes_extended(
                DRUM_BASE_NOTE,
                DRUM_NOTE_COUNT,
                loop_start,
                max(STEP_DURATION, loop_end - loop_start),
            )
        except (AttributeError, RuntimeError, TypeError):
            return ()

    def _note_is_active_at_position(self, note_start, note_end, position, loop_start, loop_end):
        if loop_end <= loop_start:
            return False

        if note_end <= loop_end:
            return note_start <= position < note_end

        wrapped_end = loop_start + (note_end - loop_end)
        return position >= note_start or position < wrapped_end

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
        drum_index = pitch - DRUM_BASE_NOTE

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
        self._log_pad(
            "[LPX-DRUM-ACTIVE] {} drum=D{:02d} note={}".format(
                action,
                pitch - DRUM_BASE_NOTE + 1,
                pitch,
            )
        )

    def _pattern_clip(self, log_errors=True):
        track = self._target_track()

        if not liveobj_valid(track):
            if log_errors:
                self._log_pad("[LPX-DRUM-STEP] no_target_track")
            return None

        clip_slots = getattr(track, "clip_slots", ())

        if len(clip_slots) <= PATTERN_SLOT_INDEX:
            if log_errors:
                self._log_pad("[LPX-DRUM-STEP] no_clip slot=0")
            return None

        clip_slot = clip_slots[PATTERN_SLOT_INDEX]

        if not liveobj_valid(clip_slot) or not getattr(clip_slot, "has_clip", False):
            if log_errors:
                self._log_pad("[LPX-DRUM-STEP] no_clip slot=0")
            return None

        clip = clip_slot.clip

        if not getattr(clip, "is_midi_clip", False):
            if log_errors:
                self._log_pad("[LPX-DRUM-STEP] clip_not_midi slot=0")
            return None

        return clip

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
        for note in self._notes_for_step(clip, pitch, step_time):
            if abs(float(note.start_time) - step_time) <= STEP_EPSILON:
                return True

        return False

    def _notes_for_step(self, clip, pitch, step_time):
        start_time = max(0.0, step_time - STEP_EPSILON)
        time_span = STEP_EPSILON * 2.0

        try:
            return clip.get_notes_extended(pitch, 1, start_time, time_span)
        except (AttributeError, RuntimeError, TypeError):
            return ()

    def _add_step_note(self, clip, pitch, step_time):
        note = Live.Clip.MidiNoteSpecification(
            pitch=int(pitch),
            start_time=float(step_time),
            duration=STEP_DURATION,
            velocity=STEP_VELOCITY,
        )
        clip.add_new_notes((note,))

    def _remove_step_note(self, clip, pitch, step_time):
        start_time = max(0.0, step_time - STEP_EPSILON)
        clip.remove_notes_extended(pitch, 1, start_time, STEP_EPSILON * 2.0)

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

    def _color_for_coordinate(self, x, y):
        if y == 7:
            return OFF_COLOR

        if y == 6:
            bar_index = self._bar_index_for_coordinate(x, y)
            return self._color_for_bar_index(bar_index)

        if y >= 4:
            step_index = self._step_index_for_coordinate(x, y)
            return self._color_for_step_index(step_index)

        if x >= 4:
            drum_index = self._drum_index_for_coordinate(x, y)
            return self._color_for_drum_index(drum_index)

        return CONTROL_COLOR

    def _drum_index_for_coordinate(self, x, y):
        if x < 4 or y > 3:
            return None

        return (3 - y) * 4 + (x - 4)

    def _color_for_drum_index(self, drum_index):
        if drum_index is None:
            return DRUM_COLOR

        pitch = DRUM_BASE_NOTE + drum_index

        if pitch in self._displayed_active_drum_pitches:
            return DRUM_PLAYBACK_COLOR

        if drum_index == self._selected_drum_index:
            return DRUM_SELECTED_COLOR

        return DRUM_COLOR

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
        self._stop_playhead_task()
        self._stop_bar_blink_task()
        self._clear_active_drum_pitches()
        self._remove_drum_pad_listeners()
        self._remove_step_pad_listeners()
        self._remove_bar_pad_listeners()
        super(StaticDrumModeLayoutComponent, self).disconnect()
