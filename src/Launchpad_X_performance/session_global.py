from __future__ import absolute_import, print_function, unicode_literals

import Live
from ableton.v2.base import liveobj_valid, task

from .clip_launch_pending import _safe_immediate_launch
from .clip_stop import _next_boundary, _quantization_length, _safe_immediate_track_stop


SESSION_GLOBAL_REFRESH = 0.01

_PENDING_GLOBAL_ATTR = "_performance_session_global_action"
_SWALLOW_GLOBAL_RELEASE_ATTR = "_performance_swallow_session_global_release"
_ACTION_START = "start"
_ACTION_STOP = "stop"
_ACTION_RESTART = "restart"

_original_session_cycle_pressed = None
_original_session_cycle_double_clicked = None
_installed = False


def _get_performance_surface(component):
    current = component

    for _ in range(30):
        module_name = getattr(
            getattr(current, "__class__", None),
            "__module__",
            "",
        )

        if module_name.startswith("Launchpad_X_performance") and hasattr(
            current,
            "_session_ring",
        ):
            return current

        parent = getattr(current, "canonical_parent", None)

        if parent is None or parent is current:
            break

        current = parent

    return None


def _visible_clip_components(surface):
    components = []

    try:
        scenes = surface._session._scenes
    except (AttributeError, RuntimeError, TypeError):
        return components

    for scene_component in scenes:
        for clip_component in getattr(scene_component, "_clip_slots", []):
            clip_slot = getattr(clip_component, "_clip_slot", None)

            if liveobj_valid(clip_slot):
                components.append(clip_component)

    return components


def _clip_slots_for_visible_clips(surface):
    clip_slots = set()

    for clip_component in _visible_clip_components(surface):
        if not clip_component.has_clip():
            continue

        clip_slots.add(clip_component._clip_slot)

    return clip_slots


def _clip_slots_for_visible_playing_clips(surface):
    clip_slots = set()

    for clip_component in _visible_clip_components(surface):
        if not clip_component.has_clip():
            continue

        clip = clip_component._clip_slot.clip

        if liveobj_valid(clip) and (clip.is_playing or clip.is_triggered):
            clip_slots.add(clip_component._clip_slot)

    return clip_slots


def _visible_has_playing_clip(surface):
    for clip_component in _visible_clip_components(surface):
        if not clip_component.has_clip():
            continue

        clip = clip_component._clip_slot.clip

        if liveobj_valid(clip) and clip.is_playing:
            return True

    return False


def _kill_global_task(state):
    global_task = state.get("task")

    if global_task is not None:
        global_task.kill()
        state["task"] = None


def _get_pending_global(surface):
    return getattr(surface, _PENDING_GLOBAL_ATTR, None)


def _clear_pending_global(surface, update_lights=True):
    state = _get_pending_global(surface)

    if state is not None:
        _kill_global_task(state)
        setattr(surface, _PENDING_GLOBAL_ATTR, None)

    if update_lights:
        _update_session_button(surface)
        _restore_clip_lights(surface, state)


def _set_session_button_light(surface, action):
    try:
        color_control = surface._session_modes.mode_button_color_control
    except (AttributeError, RuntimeError, TypeError):
        return

    if action == _ACTION_STOP:
        color_control.color = "Session.StopClipTriggered"
    elif action == _ACTION_RESTART:
        color_control.color = "Session.SceneTriggered"
    else:
        color_control.color = "Session.ClipTriggeredPlay"


def _update_session_button(surface):
    try:
        surface._session_modes._update_cycle_mode_button(
            surface._session_modes.selected_mode,
        )
    except (AttributeError, RuntimeError, TypeError):
        pass


def _clip_button_for_component(clip_component):
    try:
        return clip_component.launch_button.control_element
    except (AttributeError, RuntimeError, TypeError):
        return None


def _set_clip_pending_light(clip_component, action):
    button = _clip_button_for_component(clip_component)

    if button is None:
        return

    if action == _ACTION_STOP:
        button.set_light("Session.StopClipTriggered")
    else:
        button.set_light(clip_component._triggered_to_play_color)


def _update_clip_lights(surface, state=None):
    if state is None:
        state = _get_pending_global(surface)

    touched = set()

    if state is not None:
        touched.update(state.get("included_clip_slots", set()))
        touched.update(state.get("excluded_clip_slots", set()))

    for clip_component in _visible_clip_components(surface):
        clip_slot = clip_component._clip_slot

        if state is not None and clip_slot in state.get("included_clip_slots", set()):
            _set_clip_pending_light(clip_component, state["action"])
        elif clip_slot in touched:
            clip_component._update_launch_button_color()


def _restore_clip_lights(surface, state):
    if state is None:
        return

    touched = set(state.get("included_clip_slots", set()))
    touched.update(state.get("excluded_clip_slots", set()))

    for clip_component in _visible_clip_components(surface):
        if clip_component._clip_slot in touched:
            clip_component._update_launch_button_color()


def _pending_global_is_current(surface, state):
    return (
        state is _get_pending_global(surface)
        and surface.song.clip_trigger_quantization == state.get("quantization")
    )


def _execute_global_action(surface, state):
    action = state["action"]
    included = state.get("included_clip_slots", set())
    excluded = state.get("excluded_clip_slots", set())

    for clip_slot in list(included):
        if clip_slot in excluded or not liveobj_valid(clip_slot):
            continue

        if not getattr(clip_slot, "has_clip", False):
            continue

        if action == _ACTION_STOP:
            _safe_immediate_track_stop(clip_slot.canonical_parent)
        else:
            _safe_immediate_launch(clip_slot)


def _toggle_global_action(surface):
    state = _get_pending_global(surface)

    if state is None:
        return False

    if state["action"] == _ACTION_STOP:
        state["action"] = _ACTION_RESTART
        state["included_clip_slots"] = _clip_slots_for_visible_playing_clips(surface)
    else:
        state["action"] = _ACTION_STOP
        state["included_clip_slots"] = _clip_slots_for_visible_playing_clips(surface)

    state["excluded_clip_slots"] = set()
    _set_session_button_light(surface, state["action"])
    _update_clip_lights(surface, state)
    return True


def _queue_global_action(surface, action):
    _clear_pending_global(surface, update_lights=False)

    song = surface.song
    included = (
        _clip_slots_for_visible_playing_clips(surface)
        if action == _ACTION_STOP
        else _clip_slots_for_visible_clips(surface)
    )

    if not included:
        _update_session_button(surface)
        return False

    quantization_length = _quantization_length(song)

    if quantization_length is None or not song.is_playing:
        state = {
            "action": action,
            "included_clip_slots": included,
            "excluded_clip_slots": set(),
        }
        _execute_global_action(surface, state)
        _update_session_button(surface)
        _restore_clip_lights(surface, state)
        return True

    state = {
        "action": action,
        "boundary": _next_boundary(song, quantization_length),
        "included_clip_slots": included,
        "excluded_clip_slots": set(),
        "quantization": song.clip_trigger_quantization,
        "task": None,
    }

    _set_session_button_light(surface, action)
    _update_clip_lights(surface, state)

    def _tick_global_action():
        if not _pending_global_is_current(surface, state):
            if state is _get_pending_global(surface):
                setattr(surface, _PENDING_GLOBAL_ATTR, None)
                _update_session_button(surface)
                _restore_clip_lights(surface, state)

            _kill_global_task(state)
            return

        _set_session_button_light(surface, state["action"])
        _update_clip_lights(surface, state)

        if song.current_song_time >= state["boundary"]:
            setattr(surface, _PENDING_GLOBAL_ATTR, None)
            _kill_global_task(state)
            _execute_global_action(surface, state)
            _update_session_button(surface)
            _restore_clip_lights(surface, state)

    global_task = task.loop(
        task.wait(SESSION_GLOBAL_REFRESH),
        task.run(_tick_global_action),
    )
    state["task"] = global_task
    setattr(surface, _PENDING_GLOBAL_ATTR, state)
    global_task.pause()
    surface._tasks.add(global_task)
    global_task.resume()
    return True


def handle_session_global_clip_override(clip_component, fire_state):
    if not fire_state:
        if getattr(clip_component, _SWALLOW_GLOBAL_RELEASE_ATTR, False):
            setattr(clip_component, _SWALLOW_GLOBAL_RELEASE_ATTR, False)
            return True

        return False

    surface = _get_performance_surface(clip_component)

    if surface is None:
        return False

    state = _get_pending_global(surface)

    if state is None:
        return False

    clip_slot = getattr(clip_component, "_clip_slot", None)

    if not liveobj_valid(clip_slot):
        return False

    if state["action"] == _ACTION_START:
        included = state.setdefault("included_clip_slots", set())
        excluded = state.setdefault("excluded_clip_slots", set())

        if clip_slot in excluded:
            excluded.discard(clip_slot)
            included.add(clip_slot)
        else:
            included.discard(clip_slot)
            excluded.add(clip_slot)

        _update_clip_lights(surface, state)
        setattr(clip_component, _SWALLOW_GLOBAL_RELEASE_ATTR, True)
        return True

    state.setdefault("excluded_clip_slots", set()).add(clip_slot)
    _update_clip_lights(surface, state)
    return False


def _performance_session_cycle_pressed(self, button):
    surface = _get_performance_surface(self)

    if surface is None:
        return _original_session_cycle_pressed(self, button)

    _original_session_cycle_pressed(self, button)


def _performance_session_cycle_double_clicked(self, button):
    surface = _get_performance_surface(self)

    if surface is None:
        return _original_session_cycle_double_clicked(self, button)

    _original_session_cycle_double_clicked(self, button)


def install_session_global_actions():
    global _installed
    global _original_session_cycle_pressed
    global _original_session_cycle_double_clicked

    if _installed:
        return

    from novation.session_modes import SessionModesComponent

    listeners = SessionModesComponent.cycle_mode_button._event_listeners
    _original_session_cycle_pressed = listeners["pressed"]
    _original_session_cycle_double_clicked = listeners["double_clicked"]
    listeners["pressed"] = _performance_session_cycle_pressed
    listeners["double_clicked"] = _performance_session_cycle_double_clicked
    _installed = True
