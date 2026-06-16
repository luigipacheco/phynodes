# GPL-3.0-or-later
# Switch node: a multiplexer — Switch selects between the False and True inputs.

import bpy
from bpy.types import Node

from ..base import AQBaseNode, to_bool_safe


class AQSwitchNode(AQBaseNode, Node):
    bl_idname = "AQMqttouchSwitchNode"
    bl_label = "Switch"
    bl_icon = "MOD_PHYSICS"

    def init(self, context):
        self.new_input("Switch", "BOOL")
        self.new_input("False", "ANY")
        self.new_input("True", "ANY")
        self.new_output("Result", "ANY")

    def compute_output(self, socket):
        sel = to_bool_safe(self.get_input("Switch", 0.0))
        if sel >= 0.5:
            return self.get_input("True", 0.0)
        return self.get_input("False", 0.0)


classes = (AQSwitchNode,)
