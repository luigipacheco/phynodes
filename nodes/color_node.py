# GPL-3.0-or-later
# Color node: an RGBA color picker that outputs [r, g, b, a].

import bpy
from bpy.props import FloatVectorProperty
from bpy.types import Node

from ..base import AQBaseNode


class AQColorNode(AQBaseNode, Node):
    bl_idname = "MQTTNodesColorNode"
    bl_label = "Color"
    bl_icon = "COLOR"

    color: FloatVectorProperty(
        name="Color",
        subtype="COLOR",
        size=4,
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
    )

    def init(self, context):
        self.new_output("Color", "COLOR")

    def draw_buttons(self, context, layout):
        layout.template_color_picker(self, "color", value_slider=True)
        layout.prop(self, "color", text="")

    def compute_output(self, socket):
        c = self.color
        return [c[0], c[1], c[2], c[3]]


classes = (AQColorNode,)
