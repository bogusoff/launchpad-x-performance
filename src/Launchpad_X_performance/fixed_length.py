from __future__ import absolute_import, print_function, unicode_literals
from functools import partial
import Live
from ableton.v2.base import task
from ableton.v2.control_surface import Component
from ableton.v2.control_surface.control import ButtonControl, control_list

NUM_LENGTH_OPTIONS = 16
OFF_COLOR = "Recording.CaptureTriggered"
ON_COLOR = "FixedLength.On"

def track_can_record(track):
    return bool(getattr(track, "can_be_armed", False) and (getattr(track, "arm", False) or getattr(track, "implicit_arm", False)))

class PerformanceFixedLengthSetting(object):
    def __init__(self):
        self._selected_index = 0
        self._enabled = False
    @property
    def selected_index(self):
        return self._selected_index
    @selected_index.setter
    def selected_index(self, value):
        self._selected_index = max(0, min(NUM_LENGTH_OPTIONS - 1, int(value)))
    @property
    def selected_bars(self):
        return self._selected_index + 1
    @property
    def enabled(self):
        return self._enabled
    @enabled.setter
    def enabled(self, value):
        self._enabled = bool(value)
    def get_selected_length(self, song):
        numerator = float(song.signature_numerator)
        denominator = float(song.signature_denominator)
        return self.selected_bars * numerator * 4.0 / denominator

class PerformanceFixedLengthRecording(object):
    def __init__(self, song, fixed_length_setting, task_group=None):
        self._song = song
        self._fixed_length_setting = fixed_length_setting
        self._task_group = task_group
        self._has_clip_listeners = {}
        self._recording_listeners = {}
    def should_start_recording_in_slot(self, clip_slot):
        if clip_slot is None:
            return False
        return bool(
            track_can_record(clip_slot.canonical_parent)
            and not clip_slot.is_recording
            and not clip_slot.has_clip
            and self._fixed_length_setting.enabled
        )
    def start_recording_in_slot(self, clip_slot):
        if self.should_start_recording_in_slot(clip_slot):
            record_length = self._fixed_length_setting.get_selected_length(self._song)
            self._install_has_clip_listener(clip_slot, record_length)
            clip_slot.fire(
                record_length=record_length,
                launch_quantization=Live.Song.Quantization.q_bar,
            )
        else:
            clip_slot.fire()

    def _install_has_clip_listener(self, clip_slot, record_length):
        if not self._has_clip_listener_supported(clip_slot):
            return

        listener_key = id(clip_slot)
        self._remove_has_clip_listener(clip_slot)

        def on_has_clip_changed():
            if not getattr(clip_slot, "has_clip", False):
                return
            self._remove_has_clip_listener(clip_slot)
            self._install_recording_finished_listener(clip_slot.clip, record_length)

        try:
            clip_slot.add_has_clip_listener(on_has_clip_changed)
        except (AttributeError, RuntimeError):
            return
        self._has_clip_listeners[listener_key] = (clip_slot, on_has_clip_changed)

    def _install_recording_finished_listener(self, clip, record_length):
        if not self._is_recording_listener_supported(clip):
            return

        listener_key = id(clip)
        self._remove_recording_finished_listener(clip)

        def on_is_recording_changed():
            if self._safe_get(clip, "is_recording"):
                return
            self._remove_recording_finished_listener(clip)
            self._defer_clip_boundary_fix(clip, record_length)

        try:
            clip.add_is_recording_listener(on_is_recording_changed)
        except (AttributeError, RuntimeError):
            return
        self._recording_listeners[listener_key] = (clip, on_is_recording_changed)
        if not self._safe_get(clip, "is_recording"):
            on_is_recording_changed()

    def _has_clip_listener_supported(self, clip_slot):
        return all(
            hasattr(clip_slot, name)
            for name in (
                "add_has_clip_listener",
                "has_clip_has_listener",
                "remove_has_clip_listener",
            )
        )

    def _is_recording_listener_supported(self, clip):
        return all(
            hasattr(clip, name)
            for name in (
                "add_is_recording_listener",
                "is_recording_has_listener",
                "remove_is_recording_listener",
            )
        )

    def _remove_has_clip_listener(self, clip_slot):
        listener_key = id(clip_slot)
        listener_entry = self._has_clip_listeners.pop(listener_key, None)
        if listener_entry is not None:
            old_clip_slot, listener = listener_entry
            try:
                if old_clip_slot.has_clip_has_listener(listener):
                    old_clip_slot.remove_has_clip_listener(listener)
            except RuntimeError:
                pass
            except AttributeError:
                pass

    def _remove_recording_finished_listener(self, clip):
        listener_key = id(clip)
        listener_entry = self._recording_listeners.pop(listener_key, None)
        if listener_entry is not None:
            old_clip, listener = listener_entry
            try:
                if old_clip.is_recording_has_listener(listener):
                    old_clip.remove_is_recording_listener(listener)
            except RuntimeError:
                pass
            except AttributeError:
                pass

    def _defer_clip_boundary_fix(self, clip, record_length):
        if self._task_group is None:
            return
        try:
            self._task_group.add(
                task.sequence(
                    task.delay(0),
                    task.run(partial(self._fix_clip_boundaries, clip, record_length)),
                )
            )
        except RuntimeError:
            pass

    def _fix_clip_boundaries(self, clip, record_length):
        target_end = record_length
        self._safe_set_clip_property(clip, "loop_end", target_end)
        self._safe_set_clip_property(clip, "end_marker", target_end)

    def _safe_set_clip_property(self, clip, name, value):
        try:
            setattr(clip, name, value)
        except (AttributeError, RuntimeError):
            pass

    def _safe_get(self, obj, name):
        try:
            return getattr(obj, name)
        except RuntimeError:
            return "<RuntimeError>"
        except AttributeError:
            return "<unavailable>"

class PerformanceFixedLengthComponent(Component):
    length_buttons = control_list(ButtonControl, control_count=NUM_LENGTH_OPTIONS)
    def __init__(self, fixed_length_setting, *a, **k):
        super(PerformanceFixedLengthComponent, self).__init__(*a, **k)
        self._fixed_length_setting = fixed_length_setting
    @length_buttons.pressed
    def length_buttons(self, button):
        if self._fixed_length_setting.enabled and self._fixed_length_setting.selected_index == button.index:
            self._fixed_length_setting.enabled = False
        else:
            self._fixed_length_setting.selected_index = button.index
            self._fixed_length_setting.enabled = True
        self._update_button_colors()
    @length_buttons.released
    def length_buttons(self, _):
        self._update_button_colors()
    def on_enabled_changed(self):
        super(PerformanceFixedLengthComponent, self).on_enabled_changed()
        if self.is_enabled():
            self._update_button_colors()
    def update(self):
        super(PerformanceFixedLengthComponent, self).update()
        if self.is_enabled():
            self._update_button_colors()
    def _update_button_colors(self):
        for button in self.length_buttons:
            selected = self._fixed_length_setting.enabled and button.index <= self._fixed_length_setting.selected_index
            button.color = ON_COLOR if selected else OFF_COLOR
