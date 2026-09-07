from __future__ import absolute_import, print_function, unicode_literals

import Live
from ableton.v2.base import liveobj_valid, task
from ableton.v2.control_surface.components.scene import SceneComponent

from .clip_stop import (
    _next_boundary,
    _quantization_length,
    _safe_immediate_track_stop,
    queue_clip_stop,
)


SCENE_HOLD_SECONDS = 0.7


_original_do_launch_scene = SceneComponent._do_launch_scene
_installed = False
_PENDING_SCENE_ACTION_ATTR = "_performance_scene_pending_action"
_SWALLOW_SCENE_RELEASE_ATTR = "_performance_scene_swallow_release"
_SCENE_ACTION_REFRESH = 0.01
_SCENE_ACTION_STOP = "stop"
_SCENE_ACTION_START = "start"
_SWALLOW_SCENE_CLIP_RELEASE_ATTR = "_performance_scene_clip_override_release"
_PENDING_SCENE_REGISTRY_ATTR = "_performance_pending_scenes"


def _belongs_to_performance_surface(component):
    current = component

    for _ in range(30):
        module_name = getattr(
            getattr(current, "__class__", None),
            "__module__",
            "",
        )

        if module_name.startswith("Launchpad_X_performance"):
            return True

        parent = getattr(current, "canonical_parent", None)

        if parent is None or parent is current:
            break

        current = parent

    return False


def queue_scene_stop(scene_component):
    queued_clips = 0

    for clip_component in scene_component._clip_slots:
        clip_slot = getattr(clip_component, "_clip_slot", None)

        if not liveobj_valid(clip_slot) or not clip_component.has_clip():
            continue

        clip = clip_slot.clip

        if not clip.is_playing:
            continue

        if queue_clip_stop(clip_component):
            queued_clips += 1

    return queued_clips


def _scene_has_playing_clips(scene_component):
    for clip_component in scene_component._clip_slots:
        clip_slot = getattr(clip_component, "_clip_slot", None)

        if not liveobj_valid(clip_slot) or not clip_component.has_clip():
            continue

        clip = clip_slot.clip

        if liveobj_valid(clip) and clip.is_playing:
            return True

    return False


def _scene_clip_actions_for_stop(scene_component):
    clip_actions = {}

    for clip_component in scene_component._clip_slots:
        clip_slot = getattr(clip_component, "_clip_slot", None)
        clip_slot_key = _clip_slot_key(scene_component.song, clip_slot)

        if clip_slot_key is None:
            continue

        action = None

        if liveobj_valid(clip_slot) and clip_component.has_clip():
            clip = clip_slot.clip

            if liveobj_valid(clip) and (clip.is_playing or clip.is_triggered):
                action = _SCENE_ACTION_STOP

        clip_actions[clip_slot_key] = action

    return clip_actions


def _scene_clip_actions_for_start(scene_component):
    clip_actions = {}

    for clip_component in scene_component._clip_slots:
        clip_slot = getattr(clip_component, "_clip_slot", None)
        clip_slot_key = _clip_slot_key(scene_component.song, clip_slot)

        if clip_slot_key is None:
            continue

        action = None

        if liveobj_valid(clip_slot) and clip_component.has_clip():
            action = _SCENE_ACTION_START

        clip_actions[clip_slot_key] = action

    return clip_actions


def _track_index(song, track):
    try:
        for index, song_track in enumerate(song.tracks):
            if song_track == track:
                return index
    except (AttributeError, RuntimeError, TypeError):
        pass

    return -1


def _clip_slot_index(track, clip_slot):
    try:
        for index, track_clip_slot in enumerate(track.clip_slots):
            if track_clip_slot == clip_slot:
                return index
    except (AttributeError, RuntimeError, TypeError):
        pass

    return -1


def _clip_slot_key(song, clip_slot):
    if not liveobj_valid(clip_slot):
        return None

    track = getattr(clip_slot, "canonical_parent", None)

    if not liveobj_valid(track):
        return None

    track_index = _track_index(song, track)
    scene_index = _clip_slot_index(track, clip_slot)

    if track_index < 0 or scene_index < 0:
        return None

    return (track_index, scene_index)


def _kill_scene_action_task(state):
    action_task = state.get("task")

    if action_task is not None:
        action_task.kill()
        state["task"] = None


def _get_pending_scene_action(scene_component):
    scene_index = _scene_index_for_component(scene_component)

    if scene_index >= 0:
        registry = _pending_scene_registry_for_component(scene_component, create=False)

        if registry is not None:
            return registry.get(scene_index)

    return getattr(scene_component, _PENDING_SCENE_ACTION_ATTR, None)


def _performance_surface_for_component(component):
    current = component

    for _ in range(30):
        module_name = getattr(
            getattr(current, "__class__", None),
            "__module__",
            "",
        )

        if module_name.startswith("Launchpad_X_performance") and hasattr(
            current,
            "_performance_fixed_length_recording",
        ):
            return current

        parent = getattr(current, "canonical_parent", None)

        if parent is None or parent is current:
            break

        current = parent

    return None


def _scene_index_for_component(scene_component):
    surface = _performance_surface_for_component(scene_component)

    if surface is None:
        return -1

    try:
        for index, candidate in enumerate(surface._session._scenes):
            if candidate is scene_component:
                return index
    except (AttributeError, RuntimeError, TypeError):
        pass

    return -1


def _pending_scene_registry_for_component(component, create=True):
    surface = _performance_surface_for_component(component)

    if surface is None:
        return None

    registry = getattr(surface, _PENDING_SCENE_REGISTRY_ATTR, None)

    if registry is None and create:
        registry = {}
        setattr(surface, _PENDING_SCENE_REGISTRY_ATTR, registry)

    return registry


def _set_pending_scene_action(scene_component, state):
    scene_index = state.get("scene_index", _scene_index_for_component(scene_component))
    registry = _pending_scene_registry_for_component(scene_component)

    if registry is not None and scene_index >= 0:
        registry[scene_index] = state

    setattr(scene_component, _PENDING_SCENE_ACTION_ATTR, state)


def _remove_pending_scene_action(scene_component, state=None, scene_index=None):
    if scene_index is None:
        scene_index = _scene_index_for_component(scene_component)

    registry = _pending_scene_registry_for_component(scene_component, create=False)

    if registry is not None and scene_index >= 0:
        current_state = registry.get(scene_index)

        if state is None or current_state is state:
            try:
                del registry[scene_index]
            except KeyError:
                pass

    current_component_state = getattr(scene_component, _PENDING_SCENE_ACTION_ATTR, None)

    if state is None or current_component_state is state:
        setattr(scene_component, _PENDING_SCENE_ACTION_ATTR, None)


def pending_scene_lookup_for_clip_component(clip_component):
    scene_component = getattr(clip_component, "canonical_parent", None)
    clip_slot = getattr(clip_component, "_clip_slot", None)
    clip_slot_key = None
    state = None
    scene_index = -1
    registry = _pending_scene_registry_for_component(clip_component, create=False)

    if scene_component is not None:
        song = getattr(scene_component, "song", None)
    else:
        surface = _performance_surface_for_component(clip_component)
        song = getattr(surface, "song", None)

    if song is not None:
        clip_slot_key = _clip_slot_key(song, clip_slot)

        if clip_slot_key is not None:
            scene_index = clip_slot_key[1]

    if registry is not None and scene_index >= 0:
        state = registry.get(scene_index)

    return {
        "found": state is not None,
        "scene_component": scene_component,
        "scene_index": scene_index,
        "state": state,
        "key": clip_slot_key,
    }


def has_pending_scene_action_for_clip_component(clip_component):
    return bool(pending_scene_lookup_for_clip_component(clip_component)["found"])


def _clear_pending_scene_action(scene_component, update_light=True, reason="clear"):
    state = _get_pending_scene_action(scene_component)

    if state is not None:
        _kill_scene_action_task(state)
        _remove_pending_scene_action(scene_component, state)

    if update_light:
        scene_component._update_launch_button()
        _restore_scene_clip_lights(scene_component, state)


def _set_scene_action_light(scene_component, action):
    if action == _SCENE_ACTION_STOP:
        scene_component.launch_button.color = "Session.StopClipTriggered"
    else:
        scene_component.launch_button.color = "Session.SceneTriggered"


def _set_scene_clip_action_light(clip_component, action):
    try:
        button = clip_component.launch_button.control_element
    except (AttributeError, RuntimeError, TypeError):
        return

    if button is None:
        return

    if action == _SCENE_ACTION_STOP:
        button.set_light("Session.StopClipTriggered")
    else:
        button.set_light(clip_component._triggered_to_play_color)


def _update_scene_clip_lights(scene_component, state=None):
    if state is None:
        state = _get_pending_scene_action(scene_component)

    touched = set()

    if state is not None:
        touched.update(state.get("clip_actions", {}).keys())

    for clip_component in scene_component._clip_slots:
        clip_slot = getattr(clip_component, "_clip_slot", None)
        clip_slot_key = _clip_slot_key(scene_component.song, clip_slot)
        action = None

        if state is not None:
            action = state.get("clip_actions", {}).get(clip_slot_key)

        if action in (_SCENE_ACTION_START, _SCENE_ACTION_STOP):
            _set_scene_clip_action_light(clip_component, action)
        elif clip_slot_key in touched:
            clip_component._update_launch_button_color()


def _restore_scene_clip_lights(scene_component, state):
    if state is None:
        return

    touched = set(state.get("clip_actions", {}).keys())

    for clip_component in scene_component._clip_slots:
        clip_slot_key = _clip_slot_key(
            scene_component.song,
            getattr(clip_component, "_clip_slot", None),
        )

        if clip_slot_key in touched:
            clip_component._update_launch_button_color()


def _toggle_pending_scene_action(scene_component):
    state = _get_pending_scene_action(scene_component)

    if state is None:
        return False

    state["action"] = _opposite_scene_action(state.get("action"))

    if state["action"] == _SCENE_ACTION_STOP:
        state["clip_actions"] = _scene_clip_actions_for_stop(scene_component)
    else:
        state["clip_actions"] = _scene_clip_actions_for_start(scene_component)

    _set_scene_action_light(scene_component, state["action"])
    _update_scene_clip_lights(scene_component, state)
    return True


def _opposite_scene_action(action):
    return _SCENE_ACTION_START if action == _SCENE_ACTION_STOP else _SCENE_ACTION_STOP


def _log(scene_component, message):
    current = scene_component

    for _ in range(30):
        if hasattr(current, "log_message"):
            try:
                current.log_message(message)
                return
            except (AttributeError, RuntimeError, TypeError):
                pass

        parent = getattr(current, "canonical_parent", None)

        if parent is None or parent is current:
            break

        current = parent


def _toggle_clip_slot_in_pending_scene_action(clip_slot, scene_component, state=None):
    if state is None:
        state = _get_pending_scene_action(scene_component)

    if state is None:
        return False

    clip_slot_key = _clip_slot_key(scene_component.song, clip_slot)

    if clip_slot_key is None:
        return False

    has_clip = liveobj_valid(clip_slot) and clip_slot.has_clip
    clip = clip_slot.clip if has_clip else None
    is_playing = liveobj_valid(clip) and (clip.is_playing or clip.is_triggered)
    clip_actions = state.setdefault("clip_actions", {})
    before_action = clip_actions.get(clip_slot_key)

    if is_playing:
        after_action = None if before_action == _SCENE_ACTION_STOP else _SCENE_ACTION_STOP
    elif has_clip:
        after_action = None if before_action == _SCENE_ACTION_START else _SCENE_ACTION_START
    else:
        after_action = None

    clip_actions[clip_slot_key] = after_action
    return True


def exclude_clip_slot_from_pending_scene_stop(clip_slot, scene_component=None):
    if not liveobj_valid(clip_slot):
        return

    if scene_component is None:
        scene_component = _scene_component_for_clip_slot(clip_slot)

    if scene_component is None:
        return

    state = _get_pending_scene_action(scene_component)

    clip_slot_key = _clip_slot_key(scene_component.song, clip_slot)

    if (
        state is None
        or clip_slot_key is None
        or state.setdefault("clip_actions", {}).get(clip_slot_key) != _SCENE_ACTION_STOP
    ):
        return

    state.setdefault("clip_actions", {})[clip_slot_key] = None
    _update_scene_clip_lights(scene_component, state)


def exclude_clip_component_from_pending_scene_stop(clip_component):
    clip_slot = getattr(clip_component, "_clip_slot", None)

    if not liveobj_valid(clip_slot):
        return

    scene_component = getattr(clip_component, "canonical_parent", None)
    exclude_clip_slot_from_pending_scene_stop(
        clip_slot,
        scene_component=scene_component,
    )


def handle_pending_scene_clip_override(
    clip_component,
    pending_state=None,
    fire_state=True,
    pending_lookup=None,
):
    if not fire_state:
        if getattr(clip_component, _SWALLOW_SCENE_CLIP_RELEASE_ATTR, False):
            setattr(clip_component, _SWALLOW_SCENE_CLIP_RELEASE_ATTR, False)
            return True

        return False

    clip_slot = getattr(clip_component, "_clip_slot", None)

    if not liveobj_valid(clip_slot):
        return False

    state = pending_state
    lookup = pending_lookup or pending_scene_lookup_for_clip_component(clip_component)
    scene_component = state.get("scene_component") if state is not None else None

    if scene_component is None:
        scene_component = lookup["scene_component"]

    if scene_component is None:
        return False

    if state is None:
        return False

    if lookup.get("key") is None:
        return False

    if not _toggle_clip_slot_in_pending_scene_action(
        clip_slot,
        scene_component,
        state=state,
    ):
        return False

    _update_scene_clip_lights(scene_component, state)

    setattr(clip_component, _SWALLOW_SCENE_CLIP_RELEASE_ATTR, True)
    return True


def _scene_component_for_clip_slot(clip_slot):
    current = getattr(clip_slot, "canonical_parent", None)

    for _ in range(30):
        parent = getattr(current, "canonical_parent", None)

        if parent is None:
            return None

        clip_slots = getattr(parent, "_clip_slots", None)

        if clip_slots is not None:
            for clip_component in clip_slots:
                if getattr(clip_component, "_clip_slot", None) == clip_slot:
                    return parent

        current = parent

    return None


def _pending_scene_action_is_current(scene_component, state):
    if (
        _get_pending_scene_action(scene_component) is not state
        or not liveobj_valid(getattr(scene_component, "_scene", None))
    ):
        return False

    return scene_component.song.clip_trigger_quantization == state.get("quantization")


def _execute_scene_stop(scene_component, clip_actions=None):
    for clip_component in scene_component._clip_slots:
        clip_slot = getattr(clip_component, "_clip_slot", None)
        clip_slot_key = _clip_slot_key(scene_component.song, clip_slot)

        if clip_actions is not None and clip_actions.get(clip_slot_key) != _SCENE_ACTION_STOP:
            continue

        if not liveobj_valid(clip_slot) or not clip_component.has_clip():
            continue

        clip = clip_slot.clip

        if not liveobj_valid(clip):
            continue

        if clip_actions is None and not clip.is_playing:
            continue

        if liveobj_valid(clip):
            _safe_immediate_track_stop(clip_slot.canonical_parent)


def _execute_scene_start(scene_component, clip_actions=None):
    for clip_component in scene_component._clip_slots:
        clip_slot = getattr(clip_component, "_clip_slot", None)
        clip_slot_key = _clip_slot_key(scene_component.song, clip_slot)

        if clip_actions is not None and clip_actions.get(clip_slot_key) != _SCENE_ACTION_START:
            continue

        if not liveobj_valid(clip_slot) or not clip_component.has_clip():
            continue

        try:
            clip_slot.fire(launch_quantization=Live.Song.Quantization.q_no_q)
        except (AttributeError, RuntimeError, TypeError):
            try:
                clip_slot.fire()
            except (AttributeError, RuntimeError, TypeError):
                pass


def _execute_scene_clip_actions(scene_component, clip_actions):
    _execute_scene_stop(scene_component, clip_actions=clip_actions)
    _execute_scene_start(scene_component, clip_actions=clip_actions)


def _execute_scene_action(scene_component, action, state=None):
    clip_actions = None

    if state is not None:
        clip_actions = state.get("clip_actions")

    if clip_actions is not None:
        _execute_scene_clip_actions(scene_component, clip_actions)
        return

    if action == _SCENE_ACTION_STOP:
        _execute_scene_stop(scene_component, clip_actions=clip_actions)
    else:
        _execute_scene_start(scene_component, clip_actions=clip_actions)


def _queue_scene_action(scene_component, action):
    _clear_pending_scene_action(
        scene_component,
        update_light=False,
        reason="new_scene_action",
    )

    song = scene_component.song
    quantization_length = _quantization_length(song)
    scene_index = _scene_index_for_component(scene_component)
    clip_actions = (
        _scene_clip_actions_for_stop(scene_component)
        if action == _SCENE_ACTION_STOP
        else _scene_clip_actions_for_start(scene_component)
    )

    _log(
        scene_component,
        "SCENE_ACTION transport_playing={} action={}".format(
            int(bool(song.is_playing)),
            action,
        ),
    )

    if quantization_length is None or not song.is_playing:
        state = {
            "action": action,
            "group_action": action,
            "scene_component": scene_component,
            "scene_index": scene_index,
            "clip_actions": clip_actions,
        }
        _log(scene_component, "SCENE_ACTION immediate_execution")
        _execute_scene_action(scene_component, action, state)
        scene_component._update_launch_button()
        _restore_scene_clip_lights(scene_component, state)
        return True

    state = {
        "action": action,
        "group_action": action,
        "scene_component": scene_component,
        "scene_index": scene_index,
        "boundary": _next_boundary(song, quantization_length),
        "clip_actions": clip_actions,
        "quantization": song.clip_trigger_quantization,
        "task": None,
    }

    _log(
        scene_component,
        "SCENE_ACTION queued boundary={}".format(state["boundary"]),
    )
    _set_scene_action_light(scene_component, action)
    _update_scene_clip_lights(scene_component, state)

    def _tick_scene_action():
        if not _pending_scene_action_is_current(scene_component, state):
            if state is _get_pending_scene_action(scene_component):
                _remove_pending_scene_action(scene_component, state)
                scene_component._update_launch_button()
                _restore_scene_clip_lights(scene_component, state)

            _kill_scene_action_task(state)
            return

        _set_scene_action_light(scene_component, state["action"])
        _update_scene_clip_lights(scene_component, state)

        if song.current_song_time >= state["boundary"]:
            action_to_execute = state["action"]
            _remove_pending_scene_action(scene_component, state)
            _kill_scene_action_task(state)
            _execute_scene_action(scene_component, action_to_execute, state)
            scene_component._update_launch_button()
            _restore_scene_clip_lights(scene_component, state)

    action_task = task.loop(
        task.wait(_SCENE_ACTION_REFRESH),
        task.run(_tick_scene_action),
    )
    state["task"] = action_task
    _set_pending_scene_action(scene_component, state)
    action_task.pause()
    scene_component._tasks.add(action_task)
    action_task.resume()
    return True


def _scene_restart_or_stop(self, value):
    if not _belongs_to_performance_surface(self):
        return _original_do_launch_scene(self, value)

    if not liveobj_valid(self._scene):
        return

    if value:
        if _toggle_pending_scene_action(self):
            setattr(self, _SWALLOW_SCENE_RELEASE_ATTR, True)
            return

        previous_task = getattr(
            self,
            "_performance_scene_hold_task",
            None,
        )

        if previous_task is not None:
            previous_task.kill()

        self._performance_scene_pressed = True
        self._performance_scene_long_pressed = False

        def _stop_scene_if_still_held():
            if not getattr(self, "_performance_scene_pressed", False):
                return

            self._performance_scene_long_pressed = True
            queue_scene_stop(self)

        hold_task = self._tasks.add(
            task.sequence(
                task.wait(SCENE_HOLD_SECONDS),
                task.run(_stop_scene_if_still_held),
            )
        )

        self._performance_scene_hold_task = hold_task
        return

    if getattr(self, _SWALLOW_SCENE_RELEASE_ATTR, False):
        setattr(self, _SWALLOW_SCENE_RELEASE_ATTR, False)
        self._performance_scene_pressed = False
        hold_task = getattr(self, "_performance_scene_hold_task", None)

        if hold_task is not None:
            hold_task.kill()

        self._performance_scene_hold_task = None
        return

    if not getattr(self, "_performance_scene_pressed", False):
        return

    self._performance_scene_pressed = False

    hold_task = getattr(
        self,
        "_performance_scene_hold_task",
        None,
    )

    if hold_task is not None:
        hold_task.kill()

    self._performance_scene_hold_task = None

    if getattr(self, "_performance_scene_long_pressed", False):
        self._performance_scene_long_pressed = False
        return

    if _scene_has_playing_clips(self):
        _queue_scene_action(self, _SCENE_ACTION_STOP)
        return

    _queue_scene_action(self, _SCENE_ACTION_START)


def install_scene_stop():
    global _installed

    if _installed:
        return

    SceneComponent._do_launch_scene = _scene_restart_or_stop
    _installed = True
