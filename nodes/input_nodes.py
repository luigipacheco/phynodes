# GPL-3.0-or-later
# Simple typed input nodes mirroring Blender's default input nodes:
# Boolean (toggle), Integer, Vector, String. (Float = Value node; Color too.)

import bpy
from bpy.props import BoolProperty, IntProperty, FloatVectorProperty, StringProperty
from bpy.types import Node

from ..base import AQBaseNode


class AQBooleanNode(AQBaseNode, Node):
    bl_idname = "PhyNodesBooleanNode"
    bl_label = "Boolean"
    bl_icon = "CHECKBOX_HLT"

    value: BoolProperty(name="Value", default=False)

    def init(self, context):
        self.new_output("Value", "BOOL")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value", text="On" if self.value else "Off", toggle=True)

    def compute_output(self, socket):
        return 1.0 if self.value else 0.0


class AQIntegerNode(AQBaseNode, Node):
    bl_idname = "PhyNodesIntegerNode"
    bl_label = "Integer"
    bl_icon = "DRIVER"

    value: IntProperty(name="Value", default=0)

    def init(self, context):
        self.new_output("Value", "INT")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value", text="")

    def compute_output(self, socket):
        return int(self.value)


class AQVectorNode(AQBaseNode, Node):
    bl_idname = "PhyNodesVectorNode"
    bl_label = "Vector"
    bl_icon = "ORIENTATION_GLOBAL"

    value: FloatVectorProperty(name="Value", size=3, default=(0.0, 0.0, 0.0))

    def init(self, context):
        self.new_output("Vector", "VECTOR")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value", text="")

    def compute_output(self, socket):
        v = self.value
        return [v[0], v[1], v[2]]


class AQStringNode(AQBaseNode, Node):
    bl_idname = "PhyNodesStringNode"
    bl_label = "String"
    bl_icon = "SORTALPHA"

    value: StringProperty(name="Value", default="")

    def init(self, context):
        self.new_output("String", "STRING")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value", text="")

    def compute_output(self, socket):
        return self.value


classes = (AQBooleanNode, AQIntegerNode, AQVectorNode, AQStringNode)
