# GPL-3.0-or-later
# The MQTTouch node tree and its generic value socket.

import bpy
from bpy.props import FloatProperty, StringProperty, EnumProperty
from bpy.types import NodeTree, NodeSocket

TREE_ID = "AQMqttouchTreeType"


class AQMqttouchTree(NodeTree):
    """A MQTTouch data-flow graph: wire nodes and exchange MQTT messages."""
    bl_idname = TREE_ID
    bl_label = "MQTTouch"
    bl_icon = "NODETREE"


# Socket display colors by semantic kind (mirrors mqttouch's port colors).
_SOCKET_COLORS = {
    "SCALAR": (0.80, 0.80, 0.80, 1.0),  # white/grey
    "ARRAY": (0.30, 0.85, 0.35, 1.0),   # green
    "BOOL": (0.90, 0.85, 0.25, 1.0),    # yellow
    "MQTT": (0.25, 0.80, 0.90, 1.0),    # cyan
}


class AQVariantSocket(NodeSocket):
    """A generic socket carrying a scalar, string or array at runtime.

    Anything can connect to anything (mqttouch's Variant model). When an input
    is unlinked, its `default_value` float is used so simple constants need no
    extra node.
    """
    bl_idname = "AQVariantSocketType"
    bl_label = "Value"

    default_value: FloatProperty(name="Value", default=0.0)

    kind: EnumProperty(
        items=[
            ("SCALAR", "Scalar", ""),
            ("ARRAY", "Array", ""),
            ("BOOL", "Bool", ""),
            ("MQTT", "MQTT", ""),
        ],
        default="SCALAR",
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        return _SOCKET_COLORS.get(self.kind, _SOCKET_COLORS["SCALAR"])

    def get_value(self):
        return self.default_value


classes = (
    AQMqttouchTree,
    AQVariantSocket,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
