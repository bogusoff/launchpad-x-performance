from ableton.v2.base import task
from ableton.v2.control_surface.capabilities import (
    CONTROLLER_ID_KEY,
    NOTES_CC,
    PORTS_KEY,
    REMOTE,
    SCRIPT,
    SYNC,
    controller_id,
    inport,
    outport,
)
from ableton.v2.control_surface.components.clip_slot import ClipSlotComponent
from ableton.v2.control_surface.components.scene import SceneComponent


LONG_PRESS_TICKS = 10
STOP_INDICATION_REFRESH = 0.05


_original_do_launch_clip = ClipSlotComponent._do_launch_clip
_original_do_launch_scene = SceneComponent._do_launch_scene


def _start_stop_indication(self, track, clip, button):
    previous_task = getattr(
        self,
        "_performance_stop_indication_task",
        None,
    )

    if previous_task is not None:
        previous_task.kill()

    task_holder = {}

    def _refresh_stop_indication():
        indicator_task = task_holder.get("task")

        same_clip = (
            self.has_clip()
            and self._clip_slot.clip == clip
        )

        same_button = (
            self.launch_button.control_element == button
        )

        stop_is_pending = (
            same_clip
            and same_button
            and clip.is_playing
            and track.fired_slot_index == -2
        )

        if stop_is_pending:
            button.set_light("Session.StopClipTriggered")
            return

        if indicator_task is not None:
            indicator_task.kill()

        self._performance_stop_indication_task = None
        self._update_launch_button_color()

    indicator_task = self._tasks.add(
        task.loop(
            task.wait(STOP_INDICATION_REFRESH),
            task.run(_refresh_stop_indication),
        )
    )

    task_holder["task"] = indicator_task
    self._performance_stop_indication_task = indicator_task


def _toggle_do_launch_clip(self, fire_state):
    if fire_state and self.has_clip():
        clip = self._clip_slot.clip

        if clip.is_playing:
            track = self._clip_slot.canonical_parent
            button = self.launch_button.control_element

            track.stop_all_clips()

            if button is not None:
                button.set_light("Session.StopClipTriggered")
                _start_stop_indication(
                    self,
                    track, 
                    clip, 
                    button,
                )

            return

    _original_do_launch_clip(self, fire_state)


def _scene_restart_or_stop(self, value):
    if not self._scene:
        return

    if value:
        self._performance_scene_pressed = True
        self._performance_scene_long_pressed = False

        def _mark_long_press():
            if getattr(self, "_performance_scene_pressed", False):
                self._performance_scene_long_pressed = True

                for clip_slot in self._scene.clip_slots:
                    clip_slot.stop()

        self.canonical_parent.schedule_message(
            LONG_PRESS_TICKS,
            _mark_long_press,
        )

    else:
        if getattr(self, "_performance_scene_pressed", False):
            self._performance_scene_pressed = False

            if not getattr(
                self,
                "_performance_scene_long_pressed",
                False,
            ):
                _original_do_launch_scene(self, True)
                _original_do_launch_scene(self, False)


ClipSlotComponent._do_launch_clip = _toggle_do_launch_clip
SceneComponent._do_launch_scene = _scene_restart_or_stop


from .launchpad_x import Launchpad_X


def get_capabilities():
    return {
        CONTROLLER_ID_KEY: controller_id(
            vendor_id=4661,
            product_ids=[105],
            model_name="Launchpad X",
        ),
        PORTS_KEY: [
            inport(props=[NOTES_CC, SCRIPT, REMOTE]),
            outport(props=[NOTES_CC, SCRIPT, REMOTE, SYNC]),
        ],
    }


def create_instance(c_instance):
    return Launchpad_X(c_instance=c_instance)