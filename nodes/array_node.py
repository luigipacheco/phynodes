# GPL-3.0-or-later
# Array node: combine many inputs into a single array via a Blender-native
# multi-input socket (like Join Geometry), rather than a fixed count.

import bpy
from bpy.types import Node

from ..base import AQBaseNode


class AQArrayNode(AQBaseNode, Node):
    bl_idname = "PhyNodesArrayNode"
    bl_label = "Array"
    bl_icon = "LINENUMBERS_ON"

    def init(self, context):
        sock = self.new_input("Items", "ANY")
        # link_limit = 0 -> unlimited links = a multi-input socket.
        try:
            sock.link_limit = 0
        except Exception:
            pass
        self.new_output("Array", "ANY")

    def compute_output(self, socket):
        items = self.inputs.get("Items")
        out = []
        if items:
            for link in items.links:
                from_node = link.from_node
                if isinstance(from_node, AQBaseNode):
                    out.append(from_node.eval_output(link.from_socket))
        return out


classes = (AQArrayNode,)
