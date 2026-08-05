from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.control_surface import Component
from ableton.v2.control_surface.control import ButtonControl, control_list


NUM_LENGTH_OPTIONS = 16

OFF_COLOR = "Recording.CaptureTriggered"
ON_COLOR = "FixedLength.On"


class PerformanceFixedLengthComponent(Component):
    """
    Выбор фиксированной длины записи от 1 до 16 тактов.

    Физический порядок:
    - нижний ряд: 1–8;
    - ряд над ним: 9–16.
    """

    length_buttons = control_list(
        ButtonControl,
        control_count=NUM_LENGTH_OPTIONS,
    )

    def __init__(self, *a, **k):
        super(PerformanceFixedLengthComponent, self).__init__(*a, **k)
        self._fixed_length_enabled = False
        self._selected_bars = 0

    @property
    def fixed_length_enabled(self):
        return self._fixed_length_enabled

    @property
    def selected_bars(self):
        return self._selected_bars

    @property
    def record_length_beats(self):
        if (
            not self._fixed_length_enabled
            or self._selected_bars <= 0
        ):
            return None

        numerator = float(self.song.signature_numerator)
        denominator = float(self.song.signature_denominator)

        beats_per_bar = numerator * 4.0 / denominator

        return self._selected_bars * beats_per_bar

    def _bars_for_button_index(self, index):
        # submatrix перечисляет сначала ряд 6, затем ряд 7.
        # Нам нужен обратный музыкальный порядок:
        # ряд 7 = 1–8, ряд 6 = 9–16.
        if index < 8:
            return index + 9

        return index - 7

    @length_buttons.pressed
    def length_buttons(self, button):
        selected_bars = self._bars_for_button_index(button.index)

        if (
            self._fixed_length_enabled
            and self._selected_bars == selected_bars
        ):
            self._fixed_length_enabled = False
            self._selected_bars = 0
        else:
            self._fixed_length_enabled = True
            self._selected_bars = selected_bars

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
            button_bars = self._bars_for_button_index(button.index)
            selected = (
                self._fixed_length_enabled
                and button_bars <= self._selected_bars
            )

            button.color = ON_COLOR if selected else OFF_COLOR
