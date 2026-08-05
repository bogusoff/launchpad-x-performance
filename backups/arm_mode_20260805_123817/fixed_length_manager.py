from __future__ import absolute_import, print_function, unicode_literals


class PerformanceFixedLengthManager(object):
    """
    Следит за штатными режимами Launchpad X.

    Overlay включён только при:
    Main Mode = Session
    Session Mode = Mixer
    Mixer Mode = Pan

    Штатные Pan-фейдеры при этом отключаются.
    """

    def __init__(self, surface, component):
        self._surface = surface
        self._component = component

        self._surface._mixer_modes.add_selected_mode_listener(
            self._on_mode_changed
        )
        self._surface._session_modes.add_selected_mode_listener(
            self._on_mode_changed
        )
        self._surface._main_modes.add_selected_mode_listener(
            self._on_mode_changed
        )

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
        overlay_enabled = self._overlay_should_be_enabled()

        if overlay_enabled:
            # Режим Pan уже успел захватить фейдеры.
            # Освобождаем их, чтобы нажатия не меняли панораму.
            self._surface._mixer.set_pan_controls(None)
            self._surface._mixer.set_track_color_controls(None)

            # Возвращаем сетку из Faders layout в Session layout.
            self._surface._session_layout_mode()

        self._component.set_enabled(overlay_enabled)
