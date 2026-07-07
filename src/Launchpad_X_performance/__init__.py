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


_original_do_launch_clip = ClipSlotComponent._do_launch_clip


def _toggle_do_launch_clip(self, fire_state):
    if fire_state and self.has_clip():
        clip = self._clip_slot.clip

        if clip.is_playing:
            clip.stop()
            return

    _original_do_launch_clip(self, fire_state)


ClipSlotComponent._do_launch_clip = _toggle_do_launch_clip

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
