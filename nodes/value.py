# GPL-3.0-or-later
# Value / Slider node: a constant float source.

import bpy
from bpy.props import FloatProperty
from bpy.types import Node

from ..base import AQBaseNode


class AQValueNode(AQBaseNode, Node):
    bl_idname = "AQMqttouchValueNode"
    bl_label = "Value"
    bl_icon = "DRIVER"

    value: FloatProperty(name="Value", default=0.0)

    def init(self, context):
        self.new_output("Value", "FLOAT")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value", text="", slider=True)

    def compute_output(self, socket):
        return self.value


classes = (AQValueNode,)
