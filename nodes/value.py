# GPL-3.0-or-later
# Value node: a 0..1 slider remapped to a [Min, Max] output range.
# (Use the Clamp node if you want to constrain a value — that's its job.)

import bpy
from bpy.props import FloatProperty
from bpy.types import Node

from ..base import AQBaseNode


class AQValueNode(AQBaseNode, Node):
    bl_idname = "PhyNodesValueNode"
    bl_label = "Value"
    bl_icon = "DRIVER"

    # The slider is a 0..1 factor; Min/Max remap it to the output range.
    factor: FloatProperty(
        name="Factor", default=0.0, min=0.0, max=1.0, soft_min=0.0, soft_max=1.0,
    )
    min_value: FloatProperty(name="Min", default=0.0)
    max_value: FloatProperty(name="Max", default=1.0)

    def init(self, context):
        self.new_output("Value", "FLOAT")

    def _value(self):
        return self.min_value + self.factor * (self.max_value - self.min_value)

    def draw_buttons(self, context, layout):
        layout.prop(self, "factor", text="", slider=True)
        row = layout.row(align=True)
        row.prop(self, "min_value")
        row.prop(self, "max_value")
        layout.label(text="= %.4g" % self._value())

    def compute_output(self, socket):
        return self._value()


classes = (AQValueNode,)
