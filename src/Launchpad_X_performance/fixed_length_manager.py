from __future__ import absolute_import, print_function, unicode_literals

class PerformanceFixedLengthManager(object):
    def __init__(self, surface, component):
        self._surface = surface
        self._component = component
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
            and self._surface._mixer_modes.selected_mode == "arm"
        )
    def _refresh(self):
        enabled = self._overlay_should_be_enabled()
        if enabled:
            self._surface._session_layout_mode()
        self._component.set_enabled(enabled)
