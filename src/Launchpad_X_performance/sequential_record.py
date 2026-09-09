from __future__ import absolute_import, print_function, unicode_literals

import Live
from ableton.v2.base import liveobj_valid, task

from .clip_launch_pending import _next_boundary, _quantization_length
from .fixed_length import track_can_record


SEQUENTIAL_RECORD_REFRESH = 0.01
_SWALLOW_RELEASE_ATTR = "_performance_sequential_record_swallow_release"


def _log(surface, message):
    try:
        surface.log_message(message)
    except (AttributeError, RuntimeError, TypeError):
        try:
            surface._c_instance.log_message(message)
        except (AttributeError, RuntimeError, TypeError):
            pass


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


def _clip_slot_component_for_slot(surface, clip_slot):
    try:
        scenes = surface._session._scenes
    except (AttributeError, RuntimeError, TypeError):
        return None

    for scene_component in scenes:
        for clip_component in getattr(scene_component, "_clip_slots", []):
            if getattr(clip_component, "_clip_slot", None) == clip_slot:
                return clip_component

    return None


def _clip_cycle_length(clip):
    try:
        return max(0.0, float(clip.loop_end) - float(clip.loop_start))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return 0.0


class SequentialRecordManager(object):
    def __init__(self, surface, fixed_length_setting, task_group):
        self._surface = surface
        self._fixed_length_setting = fixed_length_setting
        self._tasks = task_group
        self._state = None
        self._has_clip_listeners = {}
        self._recording_listeners = {}

    def disconnect(self):
        self._clear_state("disconnect")
        self._remove_all_listeners()

    def handle_clip_launch(self, clip_component, fire_state):
        if not fire_state:
            if getattr(clip_component, _SWALLOW_RELEASE_ATTR, False):
                setattr(clip_component, _SWALLOW_RELEASE_ATTR, False)
                return True

            return False

        if not self._solo_mode_active():
            return False

        setattr(clip_component, _SWALLOW_RELEASE_ATTR, True)

        if self._state is not None:
            self._abort("busy")
            return True

        if self._start_sequence(clip_component):
            return True

        return True

    def _solo_mode_active(self):
        try:
            return (
                self._surface._main_modes.selected_mode == "session"
                and self._surface._session_modes.selected_mode == "mixer"
                and self._surface._mixer_modes.selected_mode == "solo"
            )
        except (AttributeError, RuntimeError, TypeError):
            return False

    def _start_sequence(self, clip_component):
        source_slot = getattr(clip_component, "_clip_slot", None)

        if not liveobj_valid(source_slot):
            self._abort("invalid_source")
            return False

        track = getattr(source_slot, "canonical_parent", None)

        if not liveobj_valid(track):
            self._abort("invalid_track")
            return False

        track_index = _track_index(self._surface.song, track)
        source_scene_index = _clip_slot_index(track, source_slot)
        destination_scene_index = source_scene_index + 1

        if track_index < 0 or source_scene_index < 0:
            self._abort("invalid_indices")
            return False

        try:
            destination_slot = track.clip_slots[destination_scene_index]
        except (AttributeError, RuntimeError, TypeError, IndexError):
            self._abort("no_destination")
            return False

        if not liveobj_valid(destination_slot):
            self._abort("invalid_destination")
            return False

        if destination_slot.has_clip:
            self._abort("destination_occupied")
            return False

        if not track_can_record(track):
            self._abort("track_cannot_record")
            return False

        record_length = self._fixed_length_setting.get_selected_length(
            self._surface.song
        )
        fixed_length_bars = self._fixed_length_setting.selected_bars
        source_had_clip = bool(source_slot.has_clip)

        self._state = {
            "state": "START_PENDING",
            "track": track,
            "track_index": track_index,
            "source_slot": source_slot,
            "source_component": clip_component,
            "source_scene_index": source_scene_index,
            "destination_slot": destination_slot,
            "destination_component": _clip_slot_component_for_slot(
                self._surface,
                destination_slot,
            ),
            "destination_scene_index": destination_scene_index,
            "record_length": record_length,
            "fixed_length_bars": fixed_length_bars,
            "source_had_clip": source_had_clip,
            "task": None,
        }
        self._log(
            "start track_index={} source_scene_index={} destination_scene_index={} fixed_length_bars={}".format(
                track_index,
                source_scene_index,
                destination_scene_index,
                fixed_length_bars,
            )
        )

        if source_had_clip:
            self._start_existing_source()
        else:
            self._start_empty_source_recording()

        return True

    def _start_empty_source_recording(self):
        state = self._state

        if state is None:
            return

        self._log_state("source_empty")
        state["state"] = "FIRST_ACTIVE"
        self._set_source_light("Recording.CaptureTriggered")
        self._install_recording_sequence_listeners(
            state["source_slot"],
            self._on_source_recording_finished,
        )
        self._fire_recording(
            state["source_slot"],
            state["record_length"],
            Live.Song.Quantization.q_bar,
        )

    def _start_existing_source(self):
        state = self._state

        if state is None:
            return

        source_slot = state["source_slot"]
        source_clip = source_slot.clip if source_slot.has_clip else None

        if not liveobj_valid(source_clip):
            self._abort("invalid_source_clip")
            return

        source_length = _clip_cycle_length(source_clip)

        if source_length <= 0.0:
            self._abort("invalid_source_length")
            return

        state["source_length"] = source_length
        state["state"] = "START_PENDING"
        self._log_state("source_existing")
        self._set_source_light("Session.ClipTriggeredPlay")
        try:
            source_slot.fire()
        except (AttributeError, RuntimeError, TypeError):
            self._abort("source_launch_failed")
            return

        self._schedule_source_cycle_wait(source_length)

    def _schedule_source_cycle_wait(self, source_length):
        state = self._state

        if state is None:
            return

        song = self._surface.song
        quantization_length = _quantization_length(song)

        if quantization_length is None or not song.is_playing:
            source_start = song.current_song_time
        else:
            source_start = _next_boundary(song, quantization_length)

        state["source_cycle_end"] = source_start + source_length
        state["state"] = "FIRST_ACTIVE"
        self._log_state("first_active")

        def tick():
            if state is not self._state:
                self._kill_task(state)
                return

            if not liveobj_valid(state.get("source_slot")):
                self._abort("source_lost")
                return

            if song.current_song_time >= state["source_cycle_end"]:
                self._kill_task(state)
                self._start_destination_recording()

        cycle_task = task.loop(
            task.wait(SEQUENTIAL_RECORD_REFRESH),
            task.run(tick),
        )
        state["task"] = cycle_task
        cycle_task.pause()
        self._tasks.add(cycle_task)
        cycle_task.resume()

    def _on_source_recording_finished(self, clip):
        state = self._state

        if state is None:
            return

        self._defer_boundary_fix(clip, state["record_length"])
        self._start_destination_recording()

    def _start_destination_recording(self):
        state = self._state

        if state is None:
            return

        destination_slot = state["destination_slot"]

        if not liveobj_valid(destination_slot) or destination_slot.has_clip:
            self._abort("destination_unavailable")
            return

        self._log_state("destination_record_start")
        state["state"] = "SECOND_RECORDING"
        self._set_destination_light("Recording.CaptureTriggered")
        self._install_recording_sequence_listeners(
            destination_slot,
            self._on_destination_recording_finished,
        )
        self._fire_recording(
            destination_slot,
            state["record_length"],
            Live.Song.Quantization.q_no_q,
        )

    def _on_destination_recording_finished(self, clip):
        state = self._state

        if state is None:
            return

        self._defer_boundary_fix(clip, state["record_length"])
        self._log_state("destination_record_end")
        self._return_to_source()

    def _return_to_source(self):
        state = self._state

        if state is None:
            return

        source_slot = state["source_slot"]

        if not liveobj_valid(source_slot) or not source_slot.has_clip:
            self._abort("source_unavailable")
            return

        state["state"] = "RETURN_PENDING"
        self._log_state("return_source")

        try:
            source_slot.fire(
                launch_quantization=Live.Song.Quantization.q_no_q,
            )
        except (AttributeError, RuntimeError, TypeError):
            try:
                source_slot.fire()
            except (AttributeError, RuntimeError, TypeError):
                self._abort("return_failed")
                return

        self._log_state("complete")
        self._clear_state("complete")

    def _fire_recording(self, clip_slot, record_length, launch_quantization):
        try:
            clip_slot.fire(
                record_length=record_length,
                launch_quantization=launch_quantization,
            )
        except (AttributeError, RuntimeError, TypeError):
            try:
                clip_slot.fire(record_length=record_length)
            except (AttributeError, RuntimeError, TypeError):
                self._abort("record_fire_failed")

    def _install_recording_sequence_listeners(self, clip_slot, callback):
        if not self._has_clip_listener_supported(clip_slot):
            self._abort("has_clip_listener_unavailable")
            return

        self._remove_has_clip_listener(clip_slot)

        def on_has_clip_changed():
            if not getattr(clip_slot, "has_clip", False):
                return

            self._remove_has_clip_listener(clip_slot)
            clip = clip_slot.clip

            if not liveobj_valid(clip):
                self._abort("created_clip_invalid")
                return

            self._install_recording_finished_listener(clip, callback)

        try:
            clip_slot.add_has_clip_listener(on_has_clip_changed)
        except (AttributeError, RuntimeError):
            self._abort("has_clip_listener_failed")
            return

        self._has_clip_listeners[id(clip_slot)] = (clip_slot, on_has_clip_changed)

        if getattr(clip_slot, "has_clip", False):
            on_has_clip_changed()

    def _install_recording_finished_listener(self, clip, callback):
        if not self._is_recording_listener_supported(clip):
            self._abort("recording_listener_unavailable")
            return

        self._remove_recording_finished_listener(clip)

        def on_is_recording_changed():
            if self._safe_get(clip, "is_recording"):
                return

            self._remove_recording_finished_listener(clip)
            callback(clip)

        try:
            clip.add_is_recording_listener(on_is_recording_changed)
        except (AttributeError, RuntimeError):
            self._abort("recording_listener_failed")
            return

        self._recording_listeners[id(clip)] = (clip, on_is_recording_changed)

        if not self._safe_get(clip, "is_recording"):
            on_is_recording_changed()

    def _has_clip_listener_supported(self, clip_slot):
        return all(
            hasattr(clip_slot, name)
            for name in (
                "add_has_clip_listener",
                "has_clip_has_listener",
                "remove_has_clip_listener",
            )
        )

    def _is_recording_listener_supported(self, clip):
        return all(
            hasattr(clip, name)
            for name in (
                "add_is_recording_listener",
                "is_recording_has_listener",
                "remove_is_recording_listener",
            )
        )

    def _remove_has_clip_listener(self, clip_slot):
        listener_entry = self._has_clip_listeners.pop(id(clip_slot), None)

        if listener_entry is None:
            return

        old_clip_slot, listener = listener_entry

        try:
            if old_clip_slot.has_clip_has_listener(listener):
                old_clip_slot.remove_has_clip_listener(listener)
        except (AttributeError, RuntimeError):
            pass

    def _remove_recording_finished_listener(self, clip):
        listener_entry = self._recording_listeners.pop(id(clip), None)

        if listener_entry is None:
            return

        old_clip, listener = listener_entry

        try:
            if old_clip.is_recording_has_listener(listener):
                old_clip.remove_is_recording_listener(listener)
        except (AttributeError, RuntimeError):
            pass

    def _remove_all_listeners(self):
        for clip_slot, _ in list(self._has_clip_listeners.values()):
            self._remove_has_clip_listener(clip_slot)

        for clip, _ in list(self._recording_listeners.values()):
            self._remove_recording_finished_listener(clip)

    def _defer_boundary_fix(self, clip, record_length):
        try:
            self._tasks.add(
                task.sequence(
                    task.delay(0),
                    task.run(lambda: self._fix_clip_boundaries(clip, record_length)),
                )
            )
        except RuntimeError:
            pass

    def _fix_clip_boundaries(self, clip, record_length):
        self._safe_set_clip_property(clip, "loop_end", record_length)
        self._safe_set_clip_property(clip, "end_marker", record_length)

    def _safe_set_clip_property(self, clip, name, value):
        try:
            setattr(clip, name, value)
        except (AttributeError, RuntimeError):
            pass

    def _safe_get(self, obj, name):
        try:
            return getattr(obj, name)
        except (AttributeError, RuntimeError):
            return False

    def _set_source_light(self, color):
        self._set_component_light(self._state.get("source_component"), color)

    def _set_destination_light(self, color):
        self._set_component_light(self._state.get("destination_component"), color)

    def _set_component_light(self, clip_component, color):
        if clip_component is None:
            return

        try:
            button = clip_component.launch_button.control_element
        except (AttributeError, RuntimeError, TypeError):
            return

        if button is not None:
            button.set_light(color)

    def _restore_lights(self, state):
        for key in ("source_component", "destination_component"):
            clip_component = state.get(key)

            if clip_component is None:
                continue

            try:
                clip_component._update_launch_button_color()
            except (AttributeError, RuntimeError, TypeError):
                pass

    def _kill_task(self, state):
        sequence_task = state.get("task")

        if sequence_task is not None:
            sequence_task.kill()
            state["task"] = None

    def _clear_state(self, reason):
        state = self._state

        if state is not None:
            self._kill_task(state)
            self._restore_lights(state)

        self._state = None

    def _abort(self, reason):
        self._log("abort reason={}".format(reason))
        self._clear_state(reason)

    def _log_state(self, event):
        state = self._state

        if state is None:
            self._log(event)
            return

        self._log(
            "{} track_index={} source_scene_index={} destination_scene_index={} fixed_length_bars={} state={}".format(
                event,
                state.get("track_index"),
                state.get("source_scene_index"),
                state.get("destination_scene_index"),
                state.get("fixed_length_bars"),
                state.get("state"),
            )
        )

    def _log(self, message):
        _log(self._surface, "SEQ_TRACE {}".format(message))
