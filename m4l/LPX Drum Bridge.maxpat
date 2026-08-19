{
    "patcher": {
        "fileversion": 1,
        "appversion": {
            "major": 8,
            "minor": 6,
            "revision": 0,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [100.0, 100.0, 560.0, 360.0],
        "bglocked": 0,
        "openinpresentation": 1,
        "default_fontsize": 12.0,
        "default_fontface": 0,
        "default_fontname": "Arial",
        "gridonopen": 1,
        "gridsize": [15.0, 15.0],
        "objectsnaponopen": 1,
        "boxes": [
            {
                "box": {
                    "id": "obj-note-label",
                    "maxclass": "comment",
                    "text": "Note",
                    "patching_rect": [30.0, 30.0, 80.0, 20.0]
                }
            },
            {
                "box": {
                    "id": "obj-note",
                    "maxclass": "live.numbox",
                    "parameter_enable": 1,
                    "varname": "Note",
                    "patching_rect": [30.0, 55.0, 80.0, 20.0],
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_shortname": "Note",
                            "parameter_longname": "Note",
                            "parameter_mmin": 0.0,
                            "parameter_mmax": 127.0,
                            "parameter_initial": [36.0],
                            "parameter_type": 0
                        }
                    }
                }
            },
            {
                "box": {
                    "id": "obj-velocity-label",
                    "maxclass": "comment",
                    "text": "Velocity",
                    "patching_rect": [130.0, 30.0, 80.0, 20.0]
                }
            },
            {
                "box": {
                    "id": "obj-velocity",
                    "maxclass": "live.numbox",
                    "parameter_enable": 1,
                    "varname": "Velocity",
                    "patching_rect": [130.0, 55.0, 80.0, 20.0],
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_shortname": "Velocity",
                            "parameter_longname": "Velocity",
                            "parameter_mmin": 0.0,
                            "parameter_mmax": 127.0,
                            "parameter_initial": [100.0],
                            "parameter_type": 0
                        }
                    }
                }
            },
            {
                "box": {
                    "id": "obj-gate-label",
                    "maxclass": "comment",
                    "text": "Gate",
                    "patching_rect": [230.0, 30.0, 80.0, 20.0]
                }
            },
            {
                "box": {
                    "id": "obj-gate",
                    "maxclass": "live.numbox",
                    "parameter_enable": 1,
                    "varname": "Gate",
                    "patching_rect": [230.0, 55.0, 80.0, 20.0],
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_shortname": "Gate",
                            "parameter_longname": "Gate",
                            "parameter_mmin": 0.0,
                            "parameter_mmax": 1.0,
                            "parameter_initial": [0.0],
                            "parameter_type": 0
                        }
                    }
                }
            },
            {
                "box": {
                    "id": "obj-trigger-label",
                    "maxclass": "comment",
                    "text": "Trigger",
                    "patching_rect": [330.0, 30.0, 80.0, 20.0]
                }
            },
            {
                "box": {
                    "id": "obj-trigger",
                    "maxclass": "live.numbox",
                    "parameter_enable": 1,
                    "varname": "Trigger",
                    "patching_rect": [330.0, 55.0, 80.0, 20.0],
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_shortname": "Trigger",
                            "parameter_longname": "Trigger",
                            "parameter_mmin": 0.0,
                            "parameter_mmax": 1.0,
                            "parameter_initial": [0.0],
                            "parameter_type": 0
                        }
                    }
                }
            },
            {
                "box": {
                    "id": "obj-trigger-bang",
                    "maxclass": "newobj",
                    "text": "t b",
                    "patching_rect": [330.0, 105.0, 40.0, 20.0]
                }
            },
            {
                "box": {
                    "id": "obj-pack",
                    "maxclass": "newobj",
                    "text": "pack 36 0",
                    "patching_rect": [130.0, 155.0, 90.0, 20.0]
                }
            },
            {
                "box": {
                    "id": "obj-noteout",
                    "maxclass": "newobj",
                    "text": "noteout 10",
                    "patching_rect": [130.0, 210.0, 70.0, 20.0]
                }
            },
            {
                "box": {
                    "id": "obj-midiin",
                    "maxclass": "newobj",
                    "text": "midiin",
                    "patching_rect": [270.0, 155.0, 60.0, 20.0]
                }
            },
            {
                "box": {
                    "id": "obj-midiout",
                    "maxclass": "newobj",
                    "text": "midiout",
                    "patching_rect": [270.0, 210.0, 60.0, 20.0]
                }
            },
            {
                "box": {
                    "id": "obj-info",
                    "maxclass": "comment",
                    "linecount": 4,
                    "text": "LPX Drum Bridge MIDI Effect. Incoming MIDI passes through unchanged. Remote Script writes Note, Velocity, Gate, then toggles Trigger; this patch emits Note/Velocity to noteout 10 on each Trigger change.",
                    "patching_rect": [30.0, 260.0, 480.0, 60.0]
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "source": ["obj-note", 0],
                    "destination": ["obj-pack", 0]
                }
            },
            {
                "patchline": {
                    "source": ["obj-velocity", 0],
                    "destination": ["obj-pack", 1]
                }
            },
            {
                "patchline": {
                    "source": ["obj-trigger", 0],
                    "destination": ["obj-trigger-bang", 0]
                }
            },
            {
                "patchline": {
                    "source": ["obj-trigger-bang", 0],
                    "destination": ["obj-pack", 0]
                }
            },
            {
                "patchline": {
                    "source": ["obj-pack", 0],
                    "destination": ["obj-noteout", 0]
                }
            },
            {
                "patchline": {
                    "source": ["obj-midiin", 0],
                    "destination": ["obj-midiout", 0]
                }
            }
        ]
    }
}
