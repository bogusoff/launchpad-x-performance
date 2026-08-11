from __future__ import absolute_import, print_function, unicode_literals

import math

import Live
from ableton.v2.base import liveobj_valid, task


STOP_SCHEDULER_REFRESH = 0.01
_PENDING_STOP_ATTR = "_performance_pending_stop"


def _clip_slot_index(track, clip_slot):
    for index, track_clip_slot in enumerate(track.clip_slots):
        if track_clip_slot == clip_slot:
            return index

    return -1


def _pending_stop_matches_slot(component, state, track, clip):
    slot_index = _clip_slot_index(track, component._clip_slot)

    return (
        state is not None
        and slot_index >= 0
        and state.get("track") == track
        and state.get("clip_slot") == component._clip_slot
        and state.get("clip") == clip
        and state.get("slot_index") == slot_index
        and track.playing_slot_index == slot_index
        and component.has_clip()
        and component._clip_slot.clip == clip
        and clip.is_playing
    )


def _get_pending_stop(component):
    return getattr(component, _PENDING_STOP_ATTR, None)


def _clear_pending_stop(component, update_color=True):
    state = _get_pending_stop(component)

    if state is not None:
        _kill_pending_task(state)

        setattr(component, _PENDING_STOP_ATTR, None)

    if update_color:
        component._update_launch_button_color()


def clear_queued_stop(component, update_color=True):
    _clear_pending_stop(component, update_color=update_color)


def _kill_pending_task(state):
    pending_task = state.get("task")

    if pending_task is not None:
        pending_task.kill()
        state["task"] = None


def _safe_immediate_track_stop(track):
    try:
        track.stop_all_clips(False)
    except RuntimeError:
        pass


def _bar_length(song):
    return song.signature_numerator * 4.0 / song.signature_denominator


def _quantization_length(song):
    quantization = song.clip_trigger_quantization
    quantization_type = Live.Song.Quantization

    if quantization == quantization_type.q_no_q:
        return None

    bar = _bar_length(song)
    mapping = {
        quantization_type.q_8_bars: bar * 8.0,
        quantization_type.q_4_bars: bar * 4.0,
        quantization_type.q_2_bars: bar * 2.0,
        quantization_type.q_bar: bar,
        quantization_type.q_half: 2.0,
        quantization_type.q_quarter: 1.0,
        quantization_type.q_eight: 0.5,
        quantization_type.q_sixtenth: 0.25,
        quantization_type.q_thirtytwoth: 0.125,
    }

    optional_lengths = (
        ("q_half_triplet", 4.0 / 3.0),
        ("q_quarter_triplet", 2.0 / 3.0),
        ("q_eight_triplet", 1.0 / 3.0),
        ("q_sixtenth_triplet", 1.0 / 6.0),
    )

    for name, length in optional_lengths:
        if hasattr(quantization_type, name):
            mapping[getattr(quantization_type, name)] = length

    return mapping.get(quantization)


def _next_boundary(song, quantization_length):
    current_time = song.current_song_time
    current_step = math.floor(current_time / quantization_length)

    return (current_step + 1.0) * quantization_length


def _pending_stop_is_current(component, state):
    song = component.song
    track = state.get("track")
    clip_slot = state.get("clip_slot")
    clip = state.get("clip")

    if (
        state is not _get_pending_stop(component)
        or not liveobj_valid(track)
        or not liveobj_valid(clip_slot)
        or not liveobj_valid(clip)
    ):
        return False

    return (
        song.clip_trigger_quantization == state.get("quantization")
        and component.has_clip()
        and component._clip_slot == clip_slot
        and component._clip_slot.clip == clip
        and clip.is_playing
        and track.playing_slot_index == state.get("slot_index")
    )


def _start_pending_stop(component, track, clip, button):
    _clear_pending_stop(component, update_color=False)

    song = component.song
    quantization_length = _quantization_length(song)

    if quantization_length is None:
        _safe_immediate_track_stop(track)
        component._update_launch_button_color()
        return

    state = {
        "track": track,
        "clip_slot": component._clip_slot,
        "clip": clip,
        "slot_index": _clip_slot_index(track, component._clip_slot),
        "quantization": song.clip_trigger_quantization,
        "boundary": _next_boundary(song, quantization_length),
        "task": None,
    }

    if button is not None:
        button.set_light("Session.StopClipTriggered")

    def _tick_pending_stop():
        if not _pending_stop_is_current(component, state):
            if state is _get_pending_stop(component):
                setattr(component, _PENDING_STOP_ATTR, None)
                component._update_launch_button_color()

            _kill_pending_task(state)
            return

        if button is not None:
            button.set_light("Session.StopClipTriggered")

        if song.current_song_time >= state["boundary"]:
            setattr(component, _PENDING_STOP_ATTR, None)
            _kill_pending_task(state)
            _safe_immediate_track_stop(track)
            component._update_launch_button_color()

    pending_task = task.loop(
        task.wait(STOP_SCHEDULER_REFRESH),
        task.run(_tick_pending_stop),
    )
    state["task"] = pending_task
    setattr(component, _PENDING_STOP_ATTR, state)
    pending_task.pause()
    component._tasks.add(pending_task)
    pending_task.resume()


def queue_clip_stop(component):
    if not component.has_clip():
        return False

    clip = component._clip_slot.clip

    if not clip.is_playing:
        return False

    track = component._clip_slot.canonical_parent
    button = component.launch_button.control_element

    _start_pending_stop(
        component,
        track,
        clip,
        button,
    )

    return True


def handle_clip_stop(component, fire_state):
    """
    Повторное нажатие по играющему клипу ставит или отменяет
    собственный queued stop.

    Пустые ClipSlot больше вообще не трогаем — поэтому на armed track
    никакая новая запись ниже не запускается.
    """
    if not fire_state:
        return False

    if not component.has_clip():
        return False

    clip = component._clip_slot.clip
    track = component._clip_slot.canonical_parent
    pending_stop = _get_pending_stop(component)
    matches_pending = _pending_stop_matches_slot(
        component,
        pending_stop,
        track,
        clip,
    )

    if not clip.is_playing:
        if _get_pending_stop(component) is not None:
            _clear_pending_stop(component)

        return False

    if matches_pending:
        _clear_pending_stop(component)
        return True

    return queue_clip_stop(component)
