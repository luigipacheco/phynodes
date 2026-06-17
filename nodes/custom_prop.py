# GPL-3.0-or-later
# Custom Property node (sink): generate/maintain a named custom property on the
# Scene (or an Object) so it can be used as a driver variable anywhere.
#
# Unlike "Set Property" (which overwrites an existing data path), this creates a
# bounded, driver-friendly property — e.g. scene["myx"] — with a type and
# min/max written into Blender's id_properties_ui, exactly like a hand-made
# custom property.

import bpy
from bpy.props import (
    StringProperty, EnumProperty, FloatProperty, PointerProperty,
)
from bpy.types import Node

from ..base import AQBaseNode, to_float_safe

_TARGETS = [
    ("SCENE", "Scene", "Create the property on the current scene"),
    ("OBJECT", "Object", "Create the property on a chosen object"),
]
_PTYPES = [
    ("FLOAT", "Float", ""),
    ("INT", "Integer", ""),
    ("BOOL", "Boolean", ""),
]


class AQCustomPropertyNode(AQBaseNode, Node):
    bl_idname = "PhyNodesCustomPropertyNode"
    bl_label = "Custom Property"
    bl_icon = "RNA"

    is_sink = True

    def _refresh(self, context):
        self._ensure_property()

    prop_name: StringProperty(name="Name", default="myx", update=_refresh)
    target_kind: EnumProperty(name="Target", items=_TARGETS, default="SCENE", update=_refresh)
    target_object: PointerProperty(name="Object", type=bpy.types.Object, update=_refresh)
    prop_type: EnumProperty(name="Type", items=_PTYPES, default="FLOAT", update=_refresh)
    min_value: FloatProperty(name="Min", default=0.0, update=_refresh)
    max_value: FloatProperty(name="Max", default=1.0, update=_refresh)
    last_written: StringProperty(default="", options={"HIDDEN"})

    def init(self, context):
        self.new_input("Value", "ANY")

    # -- target / coercion ----------------------------------------------
    def _target_id(self):
        if self.target_kind == "OBJECT":
            return self.target_object
        return bpy.context.scene

    def _coerce(self, value):
        if self.prop_type == "INT":
            return int(round(to_float_safe(value)))
        if self.prop_type == "BOOL":
            return 1 if to_float_safe(value) >= 0.5 else 0
        return to_float_safe(value)

    def _clamp(self, val):
        if self.prop_type == "BOOL":
            return val
        lo, hi = min(self.min_value, self.max_value), max(self.min_value, self.max_value)
        return max(lo, min(hi, val))

    def _ensure_property(self, context=None):
        tgt = self._target_id()
        name = self.prop_name
        if not tgt or not name:
            return
        if name not in tgt.keys():
            tgt[name] = self._coerce(0.0)
        try:
            ui = tgt.id_properties_ui(name)
            if self.prop_type == "BOOL":
                ui.update(min=0, max=1, soft_min=0, soft_max=1, description="PhyNodes")
            else:
                lo = min(self.min_value, self.max_value)
                hi = max(self.min_value, self.max_value)
                ui.update(min=lo, max=hi, soft_min=lo, soft_max=hi, description="PhyNodes")
        except Exception as exc:
            print("[phynodes] id_properties_ui:", exc)

    def driver_path(self):
        tgt = self._target_id()
        name = self.prop_name
        if not tgt or not name:
            return ""
        kind = "objects" if self.target_kind == "OBJECT" else "scenes"
        return 'bpy.data.%s["%s"]["%s"]' % (kind, tgt.name, name)

    # -- UI --------------------------------------------------------------
    def draw_buttons(self, context, layout):
        layout.prop(self, "prop_name")
        layout.prop(self, "prop_type", text="")
        layout.prop(self, "target_kind", text="")
        if self.target_kind == "OBJECT":
            layout.prop(self, "target_object", text="")
        if self.prop_type != "BOOL":
            row = layout.row(align=True)
            row.prop(self, "min_value")
            row.prop(self, "max_value")
        path = self.driver_path()
        if path:
            op = layout.operator("phynodes.copy_driver_path", icon="COPYDOWN")
            op.path = path

    # -- evaluation ------------------------------------------------------
    def evaluate_sink(self):
        tgt = self._target_id()
        name = self.prop_name
        if not tgt or not name:
            return
        val = self._clamp(self._coerce(self.get_input("Value", 0.0)))
        key = repr(val)
        if key == self.last_written and name in tgt.keys():
            return
        if name not in tgt.keys():
            self._ensure_property()
        tgt[name] = val
        self.last_written = key
        # nudge the dependency graph so drivers re-evaluate
        try:
            tgt.update_tag()
        except Exception:
            pass


classes = (AQCustomPropertyNode,)
