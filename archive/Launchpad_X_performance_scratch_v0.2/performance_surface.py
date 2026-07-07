from _Framework.ControlSurface import ControlSurface

from .logger import log
from .version import VERSION


class PerformanceSurface(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)

        log(self, "================================")
        log(self, f"Version {VERSION}")
        log(self, "Loaded")
        log(self, "MIDI Logger enabled")

    def receive_midi(self, midi_bytes):
        log(self, f"MIDI received: {midi_bytes}")

    def disconnect(self):
        log(self, "Disconnected")
        ControlSurface.disconnect(self)