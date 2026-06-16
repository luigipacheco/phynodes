# GPL-3.0-or-later
# Property Out node (sink): writes the graph value into a Blender property.
#
# The other half of the Animaquina integration: drive object transforms, custom
# properties, etc. directly from the graph (sensors / MQTT / math), no driver
# expressions required.

import bpy
from bpy.props import StringProperty
from bpy.types import Node

from ..base import AQBaseNode, is_array, to_float_safe


def write_data_path(data_path, value):
    """Assign `value` to a bpy data path like obj.location[2] = value."""
    if not data_path:
        return False
    # A single namespace acts as both globals and locals so subscript/attribute
    # assignment targets resolve correctly.
    ns = {"__builtins__": {}, "bpy": bpy, "_v": value}
    try:
        exec(data_path + " = _v", ns)
        return True
    except Exception as exc:
        print("[mqttouch] Property Out bad path:", data_path, exc)
        return False


class AQPropOutNode(AQBaseNode, Node):
    bl_idname = "MQTTNodesPropOutNode"
    bl_label = "Property Out"
    bl_icon = "EXPORT"

    is_sink = True

    data_path: StringProperty(
        name="Data Path",
        description='e.g. bpy.data.objects["Cube"].rotation_euler[2]',
        default='bpy.data.objects["Cube"].rotation_euler[2]',
    )

    def init(self, context):
        self.new_input("Value", "ANY")

    def draw_buttons(self, context, layout):
        layout.prop(self, "data_path", text="")

    def evaluate_sink(self):
        value = self.get_input("Value", 0.0)
        # Coerce to a Blender-friendly type: list stays list (for vectors),
        # everything else becomes float (the common case for transforms).
        if is_array(value):
            payload = [to_float_safe(v) for v in value]
        elif isinstance(value, str):
            payload = value
        else:
            payload = to_float_safe(value)
        write_data_path(self.data_path, payload)


classes = (AQPropOutNode,)
