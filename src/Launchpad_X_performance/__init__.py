from __future__ import absolute_import, print_function, unicode_literals
from ableton.v2.control_surface.capabilities import CONTROLLER_ID_KEY, NOTES_CC, PORTS_KEY, REMOTE, SCRIPT, SYNC, controller_id, inport, outport
from .performance import Launchpad_X_Performance

def get_capabilities():
    return {
        CONTROLLER_ID_KEY: controller_id(vendor_id=4661, product_ids=[105], model_name="Launchpad X"),
        PORTS_KEY: [
            inport(props=[NOTES_CC, SCRIPT, REMOTE]),
            outport(props=[NOTES_CC, SCRIPT, REMOTE, SYNC]),
        ],
    }

def create_instance(c_instance):
    return Launchpad_X_Performance(c_instance=c_instance)
