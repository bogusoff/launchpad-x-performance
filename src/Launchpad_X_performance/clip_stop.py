from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import task


STOP_INDICATION_REFRESH = 0.05


def _start_stop_indication(component, track, clip, button):
    previous_task = getattr(
        component,
        "_performance_stop_indication_task",
        None,
    )

    if previous_task is not None:
        previous_task.kill()

    task_holder = {}

    def _refresh_stop_indication():
        indicator_task = task_holder.get("task")

        same_clip = (
            component.has_clip()
            and component._clip_slot.clip == clip
        )

        same_button = (
            component.launch_button.control_element == button
        )

        # Live reports a fired Track Stop as -2.
        stop_is_pending = (
            same_clip
            and same_button
            and clip.is_playing
            and track.fired_slot_index == -2
        )

        if stop_is_pending:
            button.set_light("Session.StopClipTriggered")
            return

        # Some Live paths may not expose -2 for the whole pending interval.
        # Keep the triggered color while the same clip is still playing,
        # then restore the stock color as soon as it actually stops.
        if same_clip and same_button and clip.is_playing:
            button.set_light("Session.StopClipTriggered")
            return

        if indicator_task is not None:
            indicator_task.kill()

        component._performance_stop_indication_task = None
        component._update_launch_button_color()

    indicator_task = component._tasks.add(
        task.loop(
            task.wait(STOP_INDICATION_REFRESH),
            task.run(_refresh_stop_indication),
        )
    )

    task_holder["task"] = indicator_task
    component._performance_stop_indication_task = indicator_task


def handle_clip_stop(component, fire_state):
    """
    Повторное нажатие по играющему клипу -> Clip.stop().

    Live Object Model описывает Clip.stop() как тот же эффект,
    что нажатие Stop Button дорожки, если этот клип действительно играет.

    Пустые ClipSlot больше вообще не трогаем — поэтому на armed track
    никакая новая запись ниже не запускается.
    """
    if not fire_state or not component.has_clip():
        return False

    clip = component._clip_slot.clip

    if not clip.is_playing:
        return False

    track = component._clip_slot.canonical_parent
    button = component.launch_button.control_element

    clip.stop()

    if button is not None:
        button.set_light("Session.StopClipTriggered")
        _start_stop_indication(
            component,
            track,
            clip,
            button,
        )

    return True
