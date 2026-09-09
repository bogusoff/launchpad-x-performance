from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import liveobj_valid, task
import ableton.v2.control_surface.mode as mode_module

from .scene_stop import SCENE_HOLD_SECONDS, queue_scene_stop


MIXER_SIDE_SCENE_INDICES = {
    "volume": 0,
    "pan": 1,
    "send_a": 2,
    "send_b": 3,
    "stop": 4,
    "mute": 5,
    "solo": 6,
    "arm": 7,
}

_HOLD_STATE_ATTR = "_performance_mixer_side_stop_hold"
_original_make_mode_button_control = mode_module.make_mode_button_control
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


def _is_performance_mixer_modes(component):
    return (
        getattr(component, "name", None) == "Mixer_Modes"
        and _get_performance_surface(component) is not None
    )


def _absolute_scene_index(surface, local_scene_index):
    try:
        return int(surface._session_ring.scene_offset) + int(local_scene_index)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return int(local_scene_index)


def _scene_component_for_local_index(surface, local_scene_index):
    try:
        return surface._session._scenes[local_scene_index]
    except (AttributeError, RuntimeError, TypeError, IndexError):
        return None


def _log(surface, message):
    try:
        surface.log_message(message)
    except (AttributeError, RuntimeError, TypeError):
        try:
            surface._c_instance.log_message(message)
        except (AttributeError, RuntimeError, TypeError):
            pass


def _queue_stop_for_scene(surface, local_scene_index):
    scene_component = _scene_component_for_local_index(surface, local_scene_index)

    if scene_component is None or not liveobj_valid(getattr(scene_component, "_scene", None)):
        return 0

    return queue_scene_stop(scene_component)


def _kill_hold_state(state):
    hold_task = state.get("task")

    if hold_task is not None:
        hold_task.kill()
        state["task"] = None


def _clear_hold_state(component):
    state = getattr(component, _HOLD_STATE_ATTR, None)

    if state is not None:
        _kill_hold_state(state)
        setattr(component, _HOLD_STATE_ATTR, None)

    return state


class MixerSideStopBehaviour(object):
    def __init__(self, wrapped_behaviour, mode_name):
        self._wrapped_behaviour = wrapped_behaviour
        self._mode_name = mode_name

    def press_immediate(self, component, mode):
        if not self._should_handle(component):
            return self._wrapped_behaviour.press_immediate(component, mode)

        _clear_hold_state(component)
        surface = _get_performance_surface(component)
        local_scene_index = MIXER_SIDE_SCENE_INDICES[self._mode_name]
        absolute_scene_index = _absolute_scene_index(surface, local_scene_index)

        state = {
            "mode": mode,
            "local_scene_index": local_scene_index,
            "absolute_scene_index": absolute_scene_index,
            "long_pressed": False,
            "task": None,
        }

        def _stop_scene_if_still_held():
            if state is not getattr(component, _HOLD_STATE_ATTR, None):
                _kill_hold_state(state)
                return

            surface = _get_performance_surface(component)

            if surface is None:
                _kill_hold_state(state)
                setattr(component, _HOLD_STATE_ATTR, None)
                return

            queued_clips = _queue_stop_for_scene(
                surface,
                state["local_scene_index"],
            )
            state["long_pressed"] = True
            _log(
                surface,
                "[LPX-MIXER-LONGPRESS] stop button={} mode={} scene={} clips={}".format(
                    state["local_scene_index"],
                    self._mode_name,
                    state["absolute_scene_index"],
                    queued_clips,
                ),
            )

        hold_task = task.sequence(
            task.wait(SCENE_HOLD_SECONDS),
            task.run(_stop_scene_if_still_held),
        )
        state["task"] = hold_task
        setattr(component, _HOLD_STATE_ATTR, state)
        component._tasks.add(hold_task)

    def press_delayed(self, component, mode):
        if not self._should_handle(component):
            return self._wrapped_behaviour.press_delayed(component, mode)

    def release_immediate(self, component, mode):
        return self._release(component, mode, delayed=False)

    def release_delayed(self, component, mode):
        return self._release(component, mode, delayed=True)

    def update_button(self, component, mode, selected_mode):
        return self._wrapped_behaviour.update_button(
            component,
            mode,
            selected_mode,
        )

    def _release(self, component, mode, delayed):
        if not self._should_handle(component):
            if delayed:
                return self._wrapped_behaviour.release_delayed(component, mode)

            return self._wrapped_behaviour.release_immediate(component, mode)

        state = getattr(component, _HOLD_STATE_ATTR, None)

        if state is None or state.get("mode") != mode:
            return

        _clear_hold_state(component)

        if state.get("long_pressed"):
            return

        self._wrapped_behaviour.press_immediate(component, mode)
        self._wrapped_behaviour.release_immediate(component, mode)

    def _should_handle(self, component):
        return (
            self._mode_name in MIXER_SIDE_SCENE_INDICES
            and _is_performance_mixer_modes(component)
        )


def _make_performance_mode_button_control(
    modes_component,
    mode_name,
    behaviour,
    **k
):
    if (
        mode_name in MIXER_SIDE_SCENE_INDICES
        and getattr(modes_component, "name", None) == "Mixer_Modes"
    ):
        behaviour = MixerSideStopBehaviour(behaviour, mode_name)

    return _original_make_mode_button_control(
        modes_component,
        mode_name,
        behaviour,
        **k
    )


def install_mixer_side_stop():
    global _installed

    if _installed:
        return

    mode_module.make_mode_button_control = _make_performance_mode_button_control
    _installed = True
