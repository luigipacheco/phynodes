# GPL-3.0-or-later
# Value / Slider node: a constant float source with optional min/max bounds.

import bpy
from bpy.props import FloatProperty, BoolProperty
from bpy.types import Node

from ..base import AQBaseNode


class AQValueNode(AQBaseNode, Node):
    bl_idname = "PhyNodesValueNode"
    bl_label = "Value"
    bl_icon = "DRIVER"

    # The stored value lives in a hidden ID-prop "val" so the visible `value`
    # property can clamp through get/set (Blender can't set a per-instance
    # slider range from Python, so we clamp instead).
    def _get_value(self):
        return self.get("val", 0.0)

    def _set_value(self, v):
        if self.use_minmax:
            lo = min(self.min_value, self.max_value)
            hi = max(self.min_value, self.max_value)
            v = max(lo, min(hi, v))
        self["val"] = v

    def _reclamp(self, context):
        # Re-clamp the stored value when bounds (or the toggle) change.
        self._set_value(self.get("val", 0.0))

    value: FloatProperty(
        name="Value", get=_get_value, set=_set_value,
        soft_min=0.0, soft_max=1.0,
    )
    use_minmax: BoolProperty(name="Clamp", default=True, update=_reclamp)
    min_value: FloatProperty(name="Min", default=0.0, update=_reclamp)
    max_value: FloatProperty(name="Max", default=1.0, update=_reclamp)

    def init(self, context):
        self["val"] = 0.0
        self.new_output("Value", "FLOAT")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value", text="", slider=True)
        row = layout.row(align=True)
        row.prop(self, "use_minmax", text="", icon="CON_DISTLIMIT")
        sub = row.row(align=True)
        sub.enabled = self.use_minmax
        sub.prop(self, "min_value")
        sub.prop(self, "max_value")

    def compute_output(self, socket):
        return self.get("val", 0.0)


classes = (AQValueNode,)
