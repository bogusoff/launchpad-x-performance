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


_original_do_launch_clip = ClipSlotComponent._do_launch_clip
_original_do_launch_scene = SceneComponent._do_launch_scene


def _toggle_do_launch_clip(self, fire_state):
    if fire_state and self.has_clip():
        clip = self._clip_slot.clip

        if clip.is_playing:
            clip.stop()
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

        self.canonical_parent.schedule_message(LONG_PRESS_TICKS, _mark_long_press)

    else:
        if getattr(self, "_performance_scene_pressed", False):
            self._performance_scene_pressed = False

            if not getattr(self, "_performance_scene_long_pressed", False):
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