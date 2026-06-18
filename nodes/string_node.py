# GPL-3.0-or-later
# String Op node: common text operations on string values. The input/output
# sockets rebuild to match the chosen operation (like Blender's vector-math
# node swapping its sockets per mode).

import bpy
from bpy.props import EnumProperty
from bpy.types import Node

from ..base import AQBaseNode, is_array, to_float_safe

_OPS = [
    ("CONCAT", "Concatenate", "Join A and B"),
    ("UPPER", "Uppercase", "A in UPPER CASE"),
    ("LOWER", "Lowercase", "A in lower case"),
    ("TITLE", "Title Case", "A In Title Case"),
    ("STRIP", "Strip", "Trim leading/trailing whitespace from A"),
    ("REPLACE", "Replace", "Replace Find with Replace inside A"),
    ("SLICE", "Slice", "Substring A[Start:End] (End <= 0 means to the end)"),
    ("LENGTH", "Length", "Character count of A -> Int"),
    ("CONTAINS", "Contains", "A contains B -> Bool"),
    ("SPLIT", "Split", "Split A by Separator -> Array"),
    ("JOIN", "Join", "Join the items of A with Separator -> String"),
]


def _to_str(v):
    """Stringify a graph value: trim trailing .0 on whole floats, join arrays."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return "%g" % v
    if is_array(v):
        return ",".join(_to_str(x) for x in v)
    return str(v)


def _op_update(self, context):
    self._build_sockets()


class AQStringOpNode(AQBaseNode, Node):
    bl_idname = "PhyNodesStringOpNode"
    bl_label = "String Op"
    bl_icon = "SORTALPHA"

    operation: EnumProperty(
        name="Operation", items=_OPS, default="CONCAT", update=_op_update
    )

    def init(self, context):
        self._build_sockets()

    def _build_sockets(self):
        self.inputs.clear()
        self.outputs.clear()
        op = self.operation

        self.new_input("A", "STRING", default="")
        if op == "CONCAT":
            self.new_input("B", "STRING", default="")
            self.new_output("Result", "STRING")
        elif op in {"UPPER", "LOWER", "TITLE", "STRIP"}:
            self.new_output("Result", "STRING")
        elif op == "REPLACE":
            self.new_input("Find", "STRING", default="")
            self.new_input("Replace", "STRING", default="")
            self.new_output("Result", "STRING")
        elif op == "SLICE":
            self.new_input("Start", "INT", default=0)
            self.new_input("End", "INT", default=0)
            self.new_output("Result", "STRING")
        elif op == "LENGTH":
            self.new_output("Length", "INT")
        elif op == "CONTAINS":
            self.new_input("B", "STRING", default="")
            self.new_output("Result", "BOOL")
        elif op == "SPLIT":
            self.new_input("Separator", "STRING", default=",")
            self.new_output("Array", "ANY")
        elif op == "JOIN":
            self.new_input("Separator", "STRING", default=",")
            self.new_output("Result", "STRING")

    def draw_label(self):
        for ident, label, _ in _OPS:
            if ident == self.operation:
                return label
        return self.bl_label

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

    def compute_output(self, socket):
        op = self.operation
        a = self.get_input("A", "")
        if op == "CONCAT":
            return _to_str(a) + _to_str(self.get_input("B", ""))
        if op == "UPPER":
            return _to_str(a).upper()
        if op == "LOWER":
            return _to_str(a).lower()
        if op == "TITLE":
            return _to_str(a).title()
        if op == "STRIP":
            return _to_str(a).strip()
        if op == "REPLACE":
            return _to_str(a).replace(
                _to_str(self.get_input("Find", "")),
                _to_str(self.get_input("Replace", "")),
            )
        if op == "SLICE":
            s = _to_str(a)
            start = int(to_float_safe(self.get_input("Start", 0.0)))
            end = int(to_float_safe(self.get_input("End", 0.0)))
            return s[start:] if end <= 0 else s[start:end]
        if op == "LENGTH":
            return len(_to_str(a))
        if op == "CONTAINS":
            return 1.0 if _to_str(self.get_input("B", "")) in _to_str(a) else 0.0
        if op == "SPLIT":
            sep = _to_str(self.get_input("Separator", ","))
            s = _to_str(a)
            return s.split(sep) if sep else list(s)
        if op == "JOIN":
            sep = _to_str(self.get_input("Separator", ","))
            return sep.join(_to_str(x) for x in a) if is_array(a) else _to_str(a)
        return ""


classes = (AQStringOpNode,)
