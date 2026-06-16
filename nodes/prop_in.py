# GPL-3.0-or-later
# Property In node: reads a Blender property and feeds it into the graph.
#
# The headline Animaquina integration: any Blender property (object transforms,
# custom props, scene values, geometry attributes via data path) becomes a graph
# input. Uses a guarded eval of a data path, like blender_mqtt_nodes.

import bpy
from bpy.props import StringProperty
from bpy.types import Node

from ..base import AQBaseNode

# Vector-like Blender types are converted to plain lists for the graph.
try:
    from mathutils import Vector, Euler, Quaternion, Color as MColor
    _VECTORLIKE = (Vector, Euler, Quaternion, MColor)
except Exception:  # pragma: no cover
    _VECTORLIKE = ()


def read_data_path(data_path):
    """Evaluate a bpy data path safely. Returns a scalar / str / list or None."""
    if not data_path:
        return None
    try:
        value = eval(data_path, {"__builtins__": {}}, {"bpy": bpy})
    except Exception as exc:
        print("[mqttouch] Property In bad path:", data_path, exc)
        return None
    if isinstance(value, _VECTORLIKE):
        return [float(v) for v in value]
    if isinstance(value, (list, tuple)):
        try:
            return [float(v) for v in value]
        except (TypeError, ValueError):
            return list(value)
    if isinstance(value, (int, float, str, bool)):
        return value
    return None


class AQPropInNode(AQBaseNode, Node):
    bl_idname = "PhyNodesPropInNode"
    bl_label = "Property In"
    bl_icon = "IMPORT"

    data_path: StringProperty(
        name="Data Path",
        description='e.g. bpy.data.objects["Cube"].location[2]',
        default='bpy.data.objects["Cube"].location[2]',
    )

    def init(self, context):
        self.new_output("Value", "ANY")

    def draw_buttons(self, context, layout):
        layout.prop(self, "data_path", text="")
        val = read_data_path(self.data_path)
        layout.label(text="= %s" % ("?" if val is None else str(val)[:24]))

    def compute_output(self, socket):
        val = read_data_path(self.data_path)
        return 0.0 if val is None else val


classes = (AQPropInNode,)
