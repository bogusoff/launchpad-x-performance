from __future__ import absolute_import, print_function, unicode_literals
from ableton.v2.control_surface import Layer
from .clip_launch import install_clip_launch
from .fixed_length import PerformanceFixedLengthComponent, PerformanceFixedLengthRecording, PerformanceFixedLengthSetting
from .fixed_length_manager import PerformanceFixedLengthManager
from .launchpad_x import Launchpad_X

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

install_clip_launch()
