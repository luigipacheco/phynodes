# GPL-3.0-or-later
# The PhyNodes node tree and its typed value socket.

import bpy
from bpy.props import (
    FloatProperty,
    IntProperty,
    BoolProperty,
    StringProperty,
    EnumProperty,
    FloatVectorProperty,
)
from bpy.types import NodeTree, NodeSocket

TREE_ID = "PhyNodesTreeType"


class PhyNodesTree(NodeTree):
    """A PhyNodes data-flow graph: wire nodes and exchange MQTT messages."""
    bl_idname = TREE_ID
    bl_label = "PhyNodes"
    bl_icon = "NODETREE"


# Per-socket data types, à la geometry nodes. ANY is the generic variant used by
# dynamic outputs (processors, MQTT, Property In) — it shows no default field.
DATA_TYPES = [
    ("ANY", "Any", "Generic value (scalar, string or array)"),
    ("FLOAT", "Float", "Floating-point number"),
    ("INT", "Integer", "Whole number"),
    ("BOOL", "Boolean", "True / False"),
    ("STRING", "String", "Text"),
    ("VECTOR", "Vector", "3 floats"),
    ("COLOR", "Color", "RGBA"),
]

# Socket colors, loosely matching Blender's own socket palette.
_TYPE_COLORS = {
    "ANY": (0.60, 0.60, 0.60, 1.0),
    "FLOAT": (0.63, 0.63, 0.63, 1.0),
    "INT": (0.16, 0.66, 0.40, 1.0),
    "BOOL": (0.86, 0.62, 0.74, 1.0),
    "STRING": (0.44, 0.46, 0.86, 1.0),
    "VECTOR": (0.39, 0.39, 0.93, 1.0),
    "COLOR": (0.86, 0.78, 0.30, 1.0),
}


class AQVariantSocket(NodeSocket):
    """A typed-but-permissive socket (mqttouch's Variant model).

    Any socket can connect to any other — types only drive the default-value
    widget shown when unlinked, the socket color, and optional clamping. Values
    flowing through links are untouched, so a Float socket still happily carries
    an array from upstream.
    """
    bl_idname = "PhyNodesSocketType"
    bl_label = "Value"

    data_type: EnumProperty(name="Type", items=DATA_TYPES, default="FLOAT")

    # One backing default per type; only the one matching data_type is shown.
    value_float: FloatProperty(name="Value", default=0.0)
    value_int: IntProperty(name="Value", default=0)
    value_bool: BoolProperty(name="Value", default=False)
    value_string: StringProperty(name="Value", default="")
    value_vector: FloatVectorProperty(name="Value", size=3, default=(0.0, 0.0, 0.0))
    value_color: FloatVectorProperty(
        name="Color", size=4, subtype="COLOR", min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )

    # Optional preset min/max. Blender can't set a per-instance slider range, so
    # these are enforced by clamping in get_value() (and shown as a number field).
    use_clamp: BoolProperty(name="Clamp", default=False)
    min_value: FloatProperty(name="Min", default=0.0)
    max_value: FloatProperty(name="Max", default=1.0)

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
            return
        self.draw_default(layout, text)

    def draw_default(self, layout, text=""):
        """Draw the type-appropriate default-value widget (no link check)."""
        dt = self.data_type
        if dt == "FLOAT":
            layout.prop(self, "value_float", text=text)
        elif dt == "INT":
            layout.prop(self, "value_int", text=text)
        elif dt == "BOOL":
            layout.prop(self, "value_bool", text=text)
        elif dt == "STRING":
            layout.prop(self, "value_string", text=text)
        elif dt == "VECTOR":
            col = layout.column(align=True)
            if text:
                col.label(text=text)
            col.prop(self, "value_vector", text="")
        elif dt == "COLOR":
            layout.prop(self, "value_color", text=text)
        else:  # ANY
            layout.label(text=text or "(any)")

    def draw_color(self, context, node):
        return _TYPE_COLORS.get(self.data_type, _TYPE_COLORS["ANY"])

    def _clamp(self, v):
        if self.use_clamp:
            return min(max(v, self.min_value), self.max_value)
        return v

    def get_value(self):
        dt = self.data_type
        if dt == "FLOAT":
            return self._clamp(self.value_float)
        if dt == "INT":
            return int(self._clamp(self.value_int))
        if dt == "BOOL":
            return 1.0 if self.value_bool else 0.0
        if dt == "STRING":
            return self.value_string
        if dt == "VECTOR":
            return [self.value_vector[0], self.value_vector[1], self.value_vector[2]]
        if dt == "COLOR":
            c = self.value_color
            return [c[0], c[1], c[2], c[3]]
        return self.value_float  # ANY


classes = (
    PhyNodesTree,
    AQVariantSocket,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
