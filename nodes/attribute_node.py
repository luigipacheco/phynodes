# GPL-3.0-or-later
# Geometry Attribute node (source): read a mesh / geometry-nodes attribute from
# the *evaluated* object and emit it into the graph (scalar, vector, or an array
# of per-element values). Wire it to MQTT PUB to reproduce the old addon's
# "attribute output", or through Math / Array / Property Out for more.

import bpy
from bpy.props import PointerProperty, EnumProperty, BoolProperty, IntProperty
from bpy.types import Node

from ..base import AQBaseNode, to_float_safe

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

    def _update_all_instances(self, context):
        sock = self.inputs.get("Index")
        if sock is not None:
            sock.enabled = not self.all_instances

    all_instances: BoolProperty(
        name="All Elements",
        description="Output the whole attribute as an array (else a single index)",
        default=True,
        update=_update_all_instances,
    )
    # Legacy fallback for nodes saved before the Index socket existed.
    index: IntProperty(name="Index", default=0, min=0)

    def init(self, context):
        # Index is a live input so it can be driven by the graph — e.g. wire an
        # Animaquina run_idx (Property In) here to look up per-point toolpath
        # attributes at the waypoint the robot / sim playback is currently at.
        sock = self.new_input("Index", "INT", default=0)
        sock.enabled = not self.all_instances
        self.new_output("Value", "ANY")

    def draw_buttons(self, context, layout):
        layout.prop(self, "object", text="")
        layout.prop(self, "attribute", text="")
        layout.prop(self, "all_instances")
        if not self.all_instances and self.inputs.get("Index") is None:
            # Node from an old file (no socket): keep the property editable.
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
        # Clamp into range: an idle Animaquina run publishes run_idx = -1,
        # which resolves to the first point rather than an error.
        idx = max(0, min(self._current_index(), n - 1))
        return self._element(attr.data[idx], mode)

    def _current_index(self):
        sock = self.inputs.get("Index")
        if sock is None:
            return int(self.index)  # legacy node without the socket
        return int(to_float_safe(self.get_input("Index", 0)))

    def compute_output(self, socket):
        return self._read()


# ---------------------------------------------------------------------------
# Versioning — the Index input started life as a plain property, so nodes saved
# before it became a socket have nothing to wire into (draw_buttons falls back
# to the number field). init() only runs at creation and sockets persist in the
# .blend, so those nodes never gain it on their own. Add it on load, carrying
# the old value over, so existing graphs can be wired to an Animaquina Index
# without being rebuilt.
# ---------------------------------------------------------------------------

def _add_index_socket(node):
    sock = node.inputs.new("PhyNodesSocketType", "Index")
    sock.data_type = "INT"
    try:
        sock.value_int = int(getattr(node, "index", 0))
    except Exception:
        pass
    sock.enabled = not node.all_instances
    return sock


def version_index_sockets():
    """Give every legacy Geometry Attribute node its Index input socket."""
    from ..tree import TREE_ID

    fixed = 0
    for tree in bpy.data.node_groups:
        if tree.bl_idname != TREE_ID:
            continue
        for node in tree.nodes:
            if node.bl_idname != AQAttributeNode.bl_idname:
                continue
            if node.inputs.get("Index") is not None:
                continue
            try:
                _add_index_socket(node)
                fixed += 1
            except Exception as exc:
                print("[phynodes] could not add Index socket to", node.name, ":", exc)
    if fixed:
        print("[phynodes] added Index input to %d legacy Geometry Attribute node(s)" % fixed)
    return fixed


classes = (AQAttributeNode,)
