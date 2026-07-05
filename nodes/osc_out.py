# GPL-3.0-or-later
# OSC Out node (sink): sends its input value to an OSC address when it changes.

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Node

from ..base import is_array, flatten_array
from .io_base import ConnectorIONode

# Last value sent per node (keyed by node pointer) — runtime-only, same
# rationale as mqtt_pub._last_sent.
_last_sent = {}


def _osc_args(value):
    """Shape a graph value for python-osc: scalars pass through, arrays become
    a flat argument list (OSC messages have no nesting)."""
    if is_array(value):
        return flatten_array(value)
    return value


class AQOscOutNode(ConnectorIONode, Node):
    bl_idname = "PhyNodesOscOutNode"
    bl_label = "OSC Out"
    bl_icon = "EXPORT"

    is_sink = True
    connector_type_id = "OSC"

    connector_name: StringProperty(
        name="Connector",
        description="Named connection to use (empty = first OSC connection)",
        default="",
    )
    address: StringProperty(
        name="Address",
        description="OSC address to send to (e.g. /led/1)",
        default="/value",
    )
    only_on_change: BoolProperty(
        name="Only on Change",
        description="Send only when the value differs from the last sent value",
        default=True,
    )

    def init(self, context):
        self.new_input("Value", "ANY")

    def draw_buttons(self, context, layout):
        self.draw_connector_selector(context, layout)
        layout.prop(self, "address", text="")
        layout.prop(self, "only_on_change")

    def evaluate_sink(self):
        conn = self.get_connector()
        if conn is None:
            return
        args = _osc_args(self.get_input("Value", 0.0))
        key = self.as_pointer()
        if self.only_on_change and key in _last_sent and _last_sent[key] == args:
            return
        if conn.write(self.address, args):
            _last_sent[key] = args


classes = (AQOscOutNode,)
