from ableton.v2.base import task
from ableton.v2.control_surface import Layer
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

from .fixed_length_component import PerformanceFixedLengthComponent
from .fixed_length_manager import PerformanceFixedLengthManager


# Long-press timing, in seconds.
#
# Increase these values if Scene Stop or Clip Delete trigger too easily.
# Decrease them for faster live-performance access.
#
# Recommended range: 0.5–2.0 seconds.
SCENE_HOLD_SECONDS = 0.7
CLIP_DELETE_HOLD_SECONDS = 0.7

# LED indication refresh intervals and delete flash duration.
# These normally do not need to be changed.
STOP_INDICATION_REFRESH = 0.05
CLIP_DELETE_FLASH_REFRESH = 0.05
CLIP_DELETE_FLASH_STEPS = 8


_original_do_launch_clip = ClipSlotComponent._do_launch_clip
_original_on_launch_button_pressed = (
    ClipSlotComponent._on_launch_button_pressed
)
_original_on_launch_button_released = (
    ClipSlotComponent._on_launch_button_released
)
_original_do_launch_scene = SceneComponent._do_launch_scene


def _belongs_to_performance_surface(component):
    current = component

    for _ in range(20):
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



def _get_performance_surface(component):
    current = component

    for _ in range(30):
        module_name = getattr(
            getattr(current, "__class__", None),
            "__module__",
            "",
        )

        if (
            module_name.startswith("Launchpad_X_performance")
            and hasattr(current, "_performance_fixed_length")
        ):
            return current

        parent = getattr(current, "canonical_parent", None)

        if parent is None or parent is current:
            break

        current = parent

    return None

def _track_is_armed(track):
    return (
        bool(getattr(track, "can_be_armed", False))
        and bool(getattr(track, "arm", False))
    )


def _start_clip_delete_flash(self, button):
    previous_task = getattr(
        self,
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

        self._performance_clip_delete_flash_task = None
        self._update_launch_button_color()

    button.set_light("Session.StopClipTriggered")

    flash_task = self._tasks.add(
        task.loop(
            task.wait(CLIP_DELETE_FLASH_REFRESH),
            task.run(_refresh_delete_flash),
        )
    )

    task_holder["task"] = flash_task
    self._performance_clip_delete_flash_task = flash_task


def _start_clip_delete_hold(self):
    previous_task = getattr(
        self,
        "_performance_clip_delete_hold_task",
        None,
    )

    if previous_task is not None:
        previous_task.kill()

    clip = self._clip_slot.clip
    clip_slot = self._clip_slot
    button = self.launch_button.control_element

    self._performance_clip_delete_pressed = True
    self._performance_clip_delete_long_pressed = False

    def _delete_clip_if_still_held():
        if not getattr(
            self,
            "_performance_clip_delete_pressed",
            False,
        ):
            return

        same_slot = self._clip_slot == clip_slot
        same_clip = self.has_clip() and self._clip_slot.clip == clip

        if not same_slot or not same_clip:
            return

        track = self._clip_slot.canonical_parent

        if not _track_is_armed(track):
            return

        self._performance_clip_delete_long_pressed = True

        # Удаление выполняется немедленно и не зависит
        # от глобальной квантизации.
        self._do_delete_clip()

        if button is not None:
            _start_clip_delete_flash(self, button)

    delete_task = self._tasks.add(
        task.sequence(
            task.wait(CLIP_DELETE_HOLD_SECONDS),
            task.run(_delete_clip_if_still_held),
        )
    )

    self._performance_clip_delete_hold_task = delete_task


def _performance_on_launch_button_pressed(self):
    if not _belongs_to_performance_surface(self):
        return _original_on_launch_button_pressed(self)

    if not self.has_clip():
        return _original_on_launch_button_pressed(self)

    track = self._clip_slot.canonical_parent

    if not _track_is_armed(track):
        return _original_on_launch_button_pressed(self)

    # На вооружённой дорожке ждём отпускания или long press.
    # Поэтому обычное действие пока не запускаем.
    _start_clip_delete_hold(self)


def _performance_on_launch_button_released(self):
    if not _belongs_to_performance_surface(self):
        return _original_on_launch_button_released(self)

    if not getattr(
        self,
        "_performance_clip_delete_pressed",
        False,
    ):
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

    # После long press клип уже удалён — обычное действие
    # по отпусканию выполнять нельзя.
    if getattr(
        self,
        "_performance_clip_delete_long_pressed",
        False,
    ):
        self._performance_clip_delete_long_pressed = False
        return

    # Короткое нажатие: выполняем штатный press/release.
    _original_on_launch_button_pressed(self)
    _original_on_launch_button_released(self)


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


def _start_scene_clips_stop_indication(scene_component, pending_clips):
    previous_task = getattr(
        scene_component,
        "_performance_scene_clips_stop_task",
        None,
    )

    if previous_task is not None:
        previous_task.kill()

    task_holder = {}
    pending_holder = {
        "items": list(pending_clips),
    }

    def _refresh_scene_clips_stop_indication():
        indicator_task = task_holder.get("task")
        remaining_items = []

        for clip_component, clip, button in pending_holder["items"]:
            same_clip = (
                clip_component.has_clip()
                and clip_component._clip_slot.clip == clip
            )

            same_button = (
                clip_component.launch_button.control_element == button
            )

            if same_clip and same_button and clip.is_playing:
                button.set_light("Session.StopClipTriggered")
                remaining_items.append(
                    (clip_component, clip, button)
                )
            else:
                clip_component._update_launch_button_color()

        pending_holder["items"] = remaining_items

        if remaining_items:
            return

        if indicator_task is not None:
            indicator_task.kill()

        scene_component._performance_scene_clips_stop_task = None

    indicator_task = scene_component._tasks.add(
        task.loop(
            task.wait(STOP_INDICATION_REFRESH),
            task.run(_refresh_scene_clips_stop_indication),
        )
    )

    task_holder["task"] = indicator_task
    scene_component._performance_scene_clips_stop_task = indicator_task


def _toggle_do_launch_clip(self, fire_state):
    if not _belongs_to_performance_surface(self):
        return _original_do_launch_clip(self, fire_state)

    surface = _get_performance_surface(self)

    # Fixed Length применяется только при запуске записи
    # в пустом слоте на явно вооружённой дорожке.
    if (
        fire_state
        and surface is not None
        and not self.has_clip()
    ):
        track = self._clip_slot.canonical_parent
        fixed_length = surface._performance_fixed_length

        if (
            _track_is_armed(track)
            and fixed_length.fixed_length_enabled
        ):
            record_length = fixed_length.record_length_beats

            if record_length is not None:
                self._clip_slot.fire(
                    record_length=record_length
                )
                return

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
    if not _belongs_to_performance_surface(self):
        return _original_do_launch_scene(self, value)

    if not self._scene:
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
            if not getattr(
                self,
                "_performance_scene_pressed",
                False,
            ):
                return

            self._performance_scene_long_pressed = True
            pending_clips = []

            for clip_component in self._clip_slots:
                clip_slot = getattr(
                    clip_component,
                    "_clip_slot",
                    None,
                )

                # За пределами текущего Session Ring компонент может
                # временно не иметь назначенного ClipSlot.
                if clip_slot is None or not clip_slot.has_clip:
                    continue

                clip = clip_slot.clip

                if not clip.is_playing:
                    continue

                button = clip_component.launch_button.control_element

                if button is not None:
                    pending_clips.append(
                        (clip_component, clip, button)
                    )

            # Останавливаем только дорожки, на которых сейчас играет
            # клип именно из удерживаемой сцены. Track Stop использует
            # штатную Global Quantization Ableton Live.
            stopped_tracks = set()

            for clip_component, clip, button in pending_clips:
                track = clip_component._clip_slot.canonical_parent

                if track not in stopped_tracks:
                    track.stop_all_clips()
                    stopped_tracks.add(track)

                button.set_light("Session.StopClipTriggered")

            if pending_clips:
                _start_scene_clips_stop_indication(
                    self,
                    pending_clips,
                )

        hold_task = self._tasks.add(
            task.sequence(
                task.wait(SCENE_HOLD_SECONDS),
                task.run(_stop_scene_if_still_held),
            )
        )

        self._performance_scene_hold_task = hold_task

    else:
        if not getattr(
            self,
            "_performance_scene_pressed",
            False,
        ):
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

        # После long press остановка уже поставлена в очередь.
        # Короткий запуск сцены по отпусканию выполнять нельзя.
        if getattr(
            self,
            "_performance_scene_long_pressed",
            False,
        ):
            self._performance_scene_long_pressed = False
            return

        # Короткое нажатие сохраняет штатный запуск сцены.
        _original_do_launch_scene(self, True)
        _original_do_launch_scene(self, False)


ClipSlotComponent._do_launch_clip = _toggle_do_launch_clip
ClipSlotComponent._on_launch_button_pressed = (
    _performance_on_launch_button_pressed
)
ClipSlotComponent._on_launch_button_released = (
    _performance_on_launch_button_released
)
SceneComponent._do_launch_scene = _scene_restart_or_stop


from .launchpad_x import Launchpad_X


_original_create_components = Launchpad_X._create_components


def _performance_create_components(self):
    _original_create_components(self)

    clip_matrix = self._elements.clip_launch_matrix

    # Нижние два физических ряда исходной Session-матрицы.
    fixed_length_matrix = clip_matrix.submatrix[
        slice(None),
        slice(6, 8),
    ]

    self._performance_fixed_length = PerformanceFixedLengthComponent(
        name="Performance_Fixed_Length",
        is_enabled=False,
        layer=Layer(
            length_buttons=fixed_length_matrix,
        ),
    )

    self._performance_fixed_length_manager = PerformanceFixedLengthManager(
        surface=self,
        component=self._performance_fixed_length,
    )


Launchpad_X._create_components = _performance_create_components

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
