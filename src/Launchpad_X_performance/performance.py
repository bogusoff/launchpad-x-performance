from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.control_surface import Layer

from .clip_delete import install_clip_delete
from .clip_launch import install_clip_launch
from .drum_bridge import LPXDrumBridgeManager
from .drum_mode_layout import DrumModeLayoutManager, StaticDrumModeLayoutComponent
from .fixed_length import PerformanceFixedLengthComponent, PerformanceFixedLengthRecording, PerformanceFixedLengthSetting
from .fixed_length_manager import PerformanceFixedLengthManager
from .launchpad_x import Launchpad_X
from .mixer_stop import install_mixer_side_stop
from .scene_stop import install_scene_stop
from .sequential_record import SequentialRecordManager
from .session_global import install_session_global_actions

class Launchpad_X_Performance(Launchpad_X):
    def _create_components(self):
        super(Launchpad_X_Performance, self)._create_components()
        self._performance_fixed_length_setting = PerformanceFixedLengthSetting()
        self._performance_fixed_length_recording = PerformanceFixedLengthRecording(
            self.song,
            self._performance_fixed_length_setting,
            task_group=self._tasks,
        )
        clip_matrix = self._elements.clip_launch_matrix
        fixed_length_matrix = clip_matrix.submatrix[slice(None), slice(5, 7)]
        self._performance_fixed_length = PerformanceFixedLengthComponent(
            fixed_length_setting=self._performance_fixed_length_setting,
            name="Performance_Fixed_Length",
            is_enabled=False,
            layer=Layer(length_buttons=fixed_length_matrix),
        )
        self._performance_fixed_length_manager = PerformanceFixedLengthManager(
            surface=self,
            component=self._performance_fixed_length,
        )
        self._performance_sequential_record = SequentialRecordManager(
            surface=self,
            fixed_length_setting=self._performance_fixed_length_setting,
            task_group=self._tasks,
        )
        self._performance_drum_bridge = LPXDrumBridgeManager(surface=self)
        self._performance_drum_mode_layout = StaticDrumModeLayoutComponent(
            name="Performance_Drum_Mode_Static_Layout",
            drum_bridge_manager=self._performance_drum_bridge,
            is_enabled=False,
            layer=Layer(matrix=clip_matrix),
        )
        self._performance_drum_mode_layout_manager = DrumModeLayoutManager(
            surface=self,
            component=self._performance_drum_mode_layout,
        )

    def disconnect(self):
        try:
            self._performance_sequential_record.disconnect()
        except (AttributeError, RuntimeError, TypeError):
            pass

        try:
            self._performance_drum_mode_layout_manager.disconnect()
        except (AttributeError, RuntimeError, TypeError):
            pass

        super(Launchpad_X_Performance, self).disconnect()

install_clip_launch()
install_clip_delete()
install_scene_stop()
install_mixer_side_stop()
install_session_global_actions()
