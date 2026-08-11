from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import liveobj_valid, task
from ableton.v2.control_surface.components.scene import SceneComponent

from .clip_stop import queue_clip_stop


SCENE_HOLD_SECONDS = 0.7


_original_do_launch_scene = SceneComponent._do_launch_scene
_installed = False


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


def _scene_restart_or_stop(self, value):
    if not _belongs_to_performance_surface(self):
        return _original_do_launch_scene(self, value)

    if not liveobj_valid(self._scene):
        return

    if value:
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

            for clip_component in self._clip_slots:
                clip_slot = getattr(clip_component, "_clip_slot", None)

                if not liveobj_valid(clip_slot) or not clip_component.has_clip():
                    continue

                clip = clip_slot.clip

                if not clip.is_playing:
                    continue

                queue_clip_stop(clip_component)

        hold_task = self._tasks.add(
            task.sequence(
                task.wait(SCENE_HOLD_SECONDS),
                task.run(_stop_scene_if_still_held),
            )
        )

        self._performance_scene_hold_task = hold_task
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

    _original_do_launch_scene(self, True)
    _original_do_launch_scene(self, False)


def install_scene_stop():
    global _installed

    if _installed:
        return

    SceneComponent._do_launch_scene = _scene_restart_or_stop
    _installed = True
