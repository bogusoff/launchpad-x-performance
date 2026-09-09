from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import liveobj_valid, task
from ableton.v2.control_surface.components.clip_slot import ClipSlotComponent

from .clip_launch_pending import clear_queued_launch
from .clip_stop import clear_queued_stop


CLIP_DELETE_HOLD_SECONDS = 0.7
CLIP_DELETE_FLASH_REFRESH = 0.05
CLIP_DELETE_FLASH_STEPS = 8


_original_on_launch_button_pressed = ClipSlotComponent._on_launch_button_pressed
_original_on_launch_button_released = ClipSlotComponent._on_launch_button_released
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


def _track_is_explicitly_armed(track):
    return bool(
        getattr(track, "can_be_armed", False)
        and getattr(track, "arm", False)
    )


def _start_clip_delete_flash(component, button):
    previous_task = getattr(
        component,
        "_performance_clip_delete_flash_task",
        None,
    )

    if previous_task is not None:
        previous_task.kill()

    state = {
        "remaining": CLIP_DELETE_FLASH_STEPS,
    }
    task_holder = {}

    def _refresh_delete_flash():
        flash_task = task_holder.get("task")

        if state["remaining"] > 0:
            button.set_light("Session.StopClipTriggered")
            state["remaining"] -= 1
            return

        if flash_task is not None:
            flash_task.kill()

        component._performance_clip_delete_flash_task = None
        component._update_launch_button_color()

    button.set_light("Session.StopClipTriggered")

    flash_task = component._tasks.add(
        task.loop(
            task.wait(CLIP_DELETE_FLASH_REFRESH),
            task.run(_refresh_delete_flash),
        )
    )

    task_holder["task"] = flash_task
    component._performance_clip_delete_flash_task = flash_task


def _start_clip_delete_hold(component):
    previous_task = getattr(
        component,
        "_performance_clip_delete_hold_task",
        None,
    )

    if previous_task is not None:
        previous_task.kill()

    clip = component._clip_slot.clip
    clip_slot = component._clip_slot
    button = component.launch_button.control_element

    component._performance_clip_delete_pressed = True
    component._performance_clip_delete_long_pressed = False

    def _delete_clip_if_still_held():
        if not getattr(component, "_performance_clip_delete_pressed", False):
            return

        same_slot = component._clip_slot == clip_slot
        same_clip = component.has_clip() and component._clip_slot.clip == clip

        if not same_slot or not same_clip:
            return

        track = component._clip_slot.canonical_parent

        if not _track_is_explicitly_armed(track):
            return

        component._performance_clip_delete_long_pressed = True
        clear_queued_launch(component, update_color=False)
        clear_queued_stop(component, update_color=False)

        try:
            if liveobj_valid(clip_slot) and clip_slot.has_clip:
                clip_slot.delete_clip()
        except RuntimeError:
            return

        if button is not None:
            _start_clip_delete_flash(component, button)

    delete_task = component._tasks.add(
        task.sequence(
            task.wait(CLIP_DELETE_HOLD_SECONDS),
            task.run(_delete_clip_if_still_held),
        )
    )

    component._performance_clip_delete_hold_task = delete_task


def _performance_on_launch_button_pressed(self):
    if not _belongs_to_performance_surface(self):
        return _original_on_launch_button_pressed(self)

    if not self.has_clip():
        return _original_on_launch_button_pressed(self)

    track = self._clip_slot.canonical_parent

    if not _track_is_explicitly_armed(track):
        return _original_on_launch_button_pressed(self)

    _start_clip_delete_hold(self)


def _performance_on_launch_button_released(self):
    if not _belongs_to_performance_surface(self):
        return _original_on_launch_button_released(self)

    if not getattr(self, "_performance_clip_delete_pressed", False):
        return _original_on_launch_button_released(self)

    self._performance_clip_delete_pressed = False

    delete_task = getattr(
        self,
        "_performance_clip_delete_hold_task",
        None,
    )

    if delete_task is not None:
        delete_task.kill()

    self._performance_clip_delete_hold_task = None

    if getattr(self, "_performance_clip_delete_long_pressed", False):
        self._performance_clip_delete_long_pressed = False
        return

    _original_on_launch_button_pressed(self)
    _original_on_launch_button_released(self)


def install_clip_delete():
    global _installed

    if _installed:
        return

    ClipSlotComponent._on_launch_button_pressed = (
        _performance_on_launch_button_pressed
    )
    ClipSlotComponent._on_launch_button_released = (
        _performance_on_launch_button_released
    )
    _installed = True
