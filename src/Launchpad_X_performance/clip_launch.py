from __future__ import absolute_import, print_function, unicode_literals
from ableton.v2.control_surface.components.clip_slot import ClipSlotComponent

_original_do_launch_clip = ClipSlotComponent._do_launch_clip
_installed = False

def _get_performance_surface(component):
    current = component
    for _ in range(30):
        module_name = getattr(getattr(current, "__class__", None), "__module__", "")
        if module_name.startswith("Launchpad_X_performance") and hasattr(current, "_performance_fixed_length_recording"):
            return current
        parent = getattr(current, "canonical_parent", None)
        if parent is None or parent is current:
            break
        current = parent
    return None

def performance_do_launch_clip(self, fire_state):
    surface = _get_performance_surface(self)
    if surface is None:
        return _original_do_launch_clip(self, fire_state)
    if fire_state:
        slot = self._clip_slot
        recording = surface._performance_fixed_length_recording
        if recording.should_start_recording_in_slot(slot):
            recording.start_recording_in_slot(slot)
            return
    return _original_do_launch_clip(self, fire_state)

def install_clip_launch():
    global _installed
    if _installed:
        return
    ClipSlotComponent._do_launch_clip = performance_do_launch_clip
    _installed = True
