# GPL-3.0-or-later
# Geometry Attribute node (source): read a mesh / geometry-nodes attribute from
# the *evaluated* object and emit it into the graph (scalar, vector, or an array
# of per-element values). Wire it to MQTT PUB to reproduce the old addon's
# "attribute output", or through Math / Array / Property Out for more.

import bpy
from bpy.props import PointerProperty, EnumProperty, BoolProperty, IntProperty
from bpy.types import Node

from ..base import AQBaseNode

# Keep a reference to the items list returned to EnumProperty (Blender will
# crash if the strings are garbage-collected while the enum is live).
_attr_items_cache = [("", "(none)", "")]


def _eval_object(obj, context=None):
    """Return the depsgraph-evaluated object (so geo-nodes attributes appear)."""
    if obj is None:
        return None
    ctx = context or bpy.context
    try:
        depsgraph = ctx.evaluated_depsgraph_get()
        return obj.evaluated_get(depsgraph)
    except Exception:
        return obj


def _attributes_of(obj, context=None):
    obj_eval = _eval_object(obj, context)
    data = getattr(obj_eval, "data", None)
    return getattr(data, "attributes", None)


def _attr_items(self, context):
    items = []
    attrs = _attributes_of(self.object, context)
    if attrs:
        for a in attrs:
            domain = getattr(a, "domain", "")
            dtype = getattr(a, "data_type", "")
            items.append((a.name, a.name, "%s · %s" % (dtype, domain)))
    if not items:
        items = [("", "(no attributes)", "")]
    _attr_items_cache[:] = items
    return _attr_items_cache


class AQAttributeNode(AQBaseNode, Node):
    bl_idname = "PhyNodesAttributeNode"
    bl_label = "Geometry Attribute"
    bl_icon = "MESH_DATA"

    bl_width_default = 200

    object: PointerProperty(name="Object", type=bpy.types.Object)
    attribute: EnumProperty(name="Attribute", items=_attr_items)
    all_instances: BoolProperty(
        name="All Elements",
        description="Output the whole attribute as an array (else a single index)",
        default=True,
    )
    index: IntProperty(name="Index", default=0, min=0)

    def init(self, context):
        self.new_output("Value", "ANY")

    def draw_buttons(self, context, layout):
        layout.prop(self, "object", text="")
        layout.prop(self, "attribute", text="")
        layout.prop(self, "all_instances")
        if not self.all_instances:
            layout.prop(self, "index")

    # -- reading ---------------------------------------------------------
    @staticmethod
    def _element(data_item, mode):
        if mode == "vector":
            return [float(x) for x in data_item.vector]
        if mode == "color":
            return [float(x) for x in data_item.color]
        return float(data_item.value)

    def _read(self):
        attrs = _attributes_of(self.object)
        if not attrs or not self.attribute:
            return 0.0
        attr = attrs.get(self.attribute)
        if not attr or len(attr.data) == 0:
            return 0.0
        first = attr.data[0]
        if hasattr(first, "vector"):
            mode = "vector"
        elif hasattr(first, "color"):
            mode = "color"
        elif hasattr(first, "value"):
            mode = "value"
        else:
            return 0.0

        n = len(attr.data)
        if self.all_instances:
            return [self._element(attr.data[i], mode) for i in range(n)]
        idx = max(0, min(self.index, n - 1))
        return self._element(attr.data[idx], mode)

    def compute_output(self, socket):
        return self._read()


classes = (AQAttributeNode,)
