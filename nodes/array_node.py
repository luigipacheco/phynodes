# GPL-3.0-or-later
# Array node: combine a configurable number of inputs into a single array.

import bpy
from bpy.props import IntProperty
from bpy.types import Node

from ..base import AQBaseNode


class AQArrayNode(AQBaseNode, Node):
    bl_idname = "PhyNodesArrayNode"
    bl_label = "Array"
    bl_icon = "LINENUMBERS_ON"

    def _update_count(self, context):
        n = self.count
        while len(self.inputs) < n:
            self.new_input("In %d" % len(self.inputs), "ANY")
        while len(self.inputs) > n:
            self.inputs.remove(self.inputs[-1])

    count: IntProperty(
        name="Count",
        description="Number of input slots to combine",
        default=2, min=1, max=16,
        update=_update_count,
    )

    def init(self, context):
        self.new_output("Array", "ANY")
        self._update_count(context)

    def draw_buttons(self, context, layout):
        layout.prop(self, "count")

    def compute_output(self, socket):
        return [self.get_input(s.name, 0.0) for s in self.inputs]


classes = (AQArrayNode,)
