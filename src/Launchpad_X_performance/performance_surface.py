from _Framework.ControlSurface import ControlSurface

from .logger import log
from .version import VERSION


class PerformanceSurface(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)

        log(self, "================================")
        log(self, f"Version {VERSION}")
        log(self, "Loaded")
        log(self, "TEST 123456")

    def disconnect(self):
        log(self, "Disconnected")
        ControlSurface.disconnect(self)