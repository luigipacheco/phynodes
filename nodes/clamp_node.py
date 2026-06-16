# GPL-3.0-or-later
# Clamp node: constrain a value (or array, element-wise) to [Min, Max].

import bpy
from bpy.types import Node

from ..base import AQBaseNode, is_array, to_float_safe


def _clamp(v, lo, hi):
    return max(lo, min(hi, to_float_safe(v)))


class AQClampNode(AQBaseNode, Node):
    bl_idname = "AQMqttouchClampNode"
    bl_label = "Clamp"
    bl_icon = "CON_DISTLIMIT"

    def init(self, context):
        self.new_input("Value", "FLOAT")
        self.new_input("Min", "FLOAT", default=0.0)
        self.new_input("Max", "FLOAT", default=1.0)
        self.new_output("Result", "FLOAT")

    def compute_output(self, socket):
        value = self.get_input("Value", 0.0)
        lo = to_float_safe(self.get_input("Min", 0.0))
        hi = to_float_safe(self.get_input("Max", 1.0))
        if is_array(value):
            return [_clamp(x, lo, hi) for x in value]
        return _clamp(value, lo, hi)


classes = (AQClampNode,)
