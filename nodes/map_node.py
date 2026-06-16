# GPL-3.0-or-later
# Map node: linear remap of a value from one range to another (mqttouch MapNode).

import bpy
from bpy.types import Node

from ..base import AQBaseNode, is_array, to_float_safe


def _remap(v, fmin, fmax, tmin, tmax):
    v = to_float_safe(v)
    span = fmax - fmin
    if span == 0.0:
        return tmin
    t = (v - fmin) / span
    return tmin + t * (tmax - tmin)


class AQMapNode(AQBaseNode, Node):
    bl_idname = "AQMqttouchMapNode"
    bl_label = "Map Range"
    bl_icon = "ARROW_LEFTRIGHT"

    def init(self, context):
        self.new_input("Value")
        self.new_input("From Min", default=0.0)
        self.new_input("From Max", default=1.0)
        self.new_input("To Min", default=0.0)
        self.new_input("To Max", default=1.0)
        self.new_output("Result", "FLOAT")

    def compute_output(self, socket):
        value = self.get_input("Value", 0.0)
        fmin = to_float_safe(self.get_input("From Min", 0.0))
        fmax = to_float_safe(self.get_input("From Max", 1.0))
        tmin = to_float_safe(self.get_input("To Min", 0.0))
        tmax = to_float_safe(self.get_input("To Max", 1.0))
        if is_array(value):
            return [_remap(x, fmin, fmax, tmin, tmax) for x in value]
        return _remap(value, fmin, fmax, tmin, tmax)


classes = (AQMapNode,)
