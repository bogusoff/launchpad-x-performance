from __future__ import absolute_import, print_function, unicode_literals
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
    def __init__(self, song, fixed_length_setting):
        self._song = song
        self._fixed_length_setting = fixed_length_setting
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
            clip_slot.fire(record_length=self._fixed_length_setting.get_selected_length(self._song))
        else:
            clip_slot.fire()

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
