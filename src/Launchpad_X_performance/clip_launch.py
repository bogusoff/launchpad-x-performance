from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.control_surface.components.clip_slot import ClipSlotComponent

from .clip_launch_pending import handle_queued_launch, swallow_pending_launch_release
from .clip_stop import handle_clip_stop
from .scene_stop import (
    handle_pending_scene_clip_override,
    pending_scene_lookup_for_clip_component,
)
from .session_global import handle_session_global_clip_override


_original_do_launch_clip = ClipSlotComponent._do_launch_clip
_installed = False


def _get_performance_surface(component):
    """
    Ищет главный Launchpad_X_Performance по canonical_parent.

    Глобальный ClipSlotComponent patch не должен менять другие
    Control Surface.
    """
    current = component

    for _ in range(30):
        if (
            current.__class__.__module__.startswith(
                "Launchpad_X_performance"
            )
            and hasattr(
                current,
                "_performance_fixed_length_recording",
            )
        ):
            return current

        parent = getattr(current, "canonical_parent", None)

        if parent is None or parent is current:
            break

        current = parent

    return None


def performance_do_launch_clip(self, fire_state):
    """
    Единая точка маршрутизации действий пэда Session.

    Порядок:
    1. Fixed Length-запись пустого слота по логике Novation.
    2. Собственный queued launch остановленного клипа.
    3. Квантованный Stop уже играющего клипа.
    4. Всё остальное — штатный ClipSlotComponent.
    """
    surface = _get_performance_surface(self)

    if surface is None:
        return _original_do_launch_clip(self, fire_state)

    pending_scene_lookup = pending_scene_lookup_for_clip_component(self)
    pending_scene = pending_scene_lookup["found"]
    pending_state = pending_scene_lookup["state"]

    if fire_state and pending_scene:
        handled = handle_pending_scene_clip_override(
            self,
            pending_state,
            pending_lookup=pending_scene_lookup,
        )

        if handled:
            return

    if not fire_state:
        handled = handle_pending_scene_clip_override(self, None, fire_state=False)

        if handled:
            return

    if surface._performance_sequential_record.handle_clip_launch(
        self,
        fire_state,
    ):
        return

    if fire_state:
        slot = self._clip_slot
        recording = surface._performance_fixed_length_recording

        if recording.should_start_recording_in_slot(slot):
            recording.start_recording_in_slot(slot)
            return

    if swallow_pending_launch_release(
        self,
        fire_state,
    ):
        return

    if handle_session_global_clip_override(
        self,
        fire_state,
    ):
        return

    if handle_queued_launch(
        self,
        fire_state,
    ):
        return

    if handle_clip_stop(
        self,
        fire_state,
    ):
        return

    return _original_do_launch_clip(self, fire_state)


def install_clip_launch():
    global _installed

    if _installed:
        return

    ClipSlotComponent._do_launch_clip = performance_do_launch_clip
    _installed = True
