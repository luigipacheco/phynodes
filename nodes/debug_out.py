# GPL-3.0-or-later
# Debug node (sink): shows the latest value of its input in the node body.
# Handy for testing the graph without a broker.

import bpy
from bpy.props import StringProperty
from bpy.types import Node

from ..base import AQBaseNode, is_array


class AQDebugNode(AQBaseNode, Node):
    bl_idname = "MQTTNodesDebugNode"
    bl_label = "Debug"
    bl_icon = "INFO"

    is_sink = True

    display: StringProperty(default="-", options={"HIDDEN"})

    def init(self, context):
        self.new_input("Value", "ANY")

    def draw_buttons(self, context, layout):
        layout.label(text=self.display)

    def evaluate_sink(self):
        value = self.get_input("Value", 0.0)
        if is_array(value):
            text = "Array[%d]: %s" % (len(value), str(value)[:32])
        else:
            text = str(value)[:40]
        if text != self.display:
            self.display = text


classes = (AQDebugNode,)
