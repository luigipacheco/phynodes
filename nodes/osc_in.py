# GPL-3.0-or-later
# OSC In node: outputs the latest value received on its OSC address. Values
# arrive already typed (OSC type tags) — one argument is a scalar, several
# come out as an array.

import bpy
from bpy.props import StringProperty
from bpy.types import Node

from ..base import is_array
from .io_base import ConnectorIONode


class AQOscInNode(ConnectorIONode, Node):
    bl_idname = "PhyNodesOscInNode"
    bl_label = "OSC In"
    bl_icon = "IMPORT"

    connector_type_id = "OSC"

    connector_name: StringProperty(
        name="Connector",
        description="Named connection to use (empty = first OSC connection)",
        default="",
    )
    address: StringProperty(
        name="Address",
        description="OSC address to listen on (e.g. /fader/1)",
        default="/value",
    )

    def init(self, context):
        self.new_output("Value", "ANY")

    def draw_buttons(self, context, layout):
        self.draw_connector_selector(context, layout)
        layout.prop(self, "address", text="")
        conn = self.get_connector()
        if conn is None:
            layout.label(text="(not connected)", icon="UNLINKED")
            return
        value = conn.read(self.address)
        if value is None:
            layout.label(text="(no message yet)", icon="DOT")
        elif is_array(value):
            layout.label(text="Array[%d]" % len(value))
        else:
            layout.label(text="= %s" % str(value)[:24])

    def compute_output(self, socket):
        conn = self.get_connector()
        if conn is None:
            return 0.0
        value = conn.read(self.address)
        return 0.0 if value is None else value


classes = (AQOscInNode,)
