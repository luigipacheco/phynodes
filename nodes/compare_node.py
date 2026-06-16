# GPL-3.0-or-later
# Compare node: A <op> B -> 1.0 / 0.0 (boolean). Array-aware element-wise.

import bpy
from bpy.props import EnumProperty
from bpy.types import Node

from ..base import AQBaseNode, is_array, to_float_safe

_OPS = [
    ("LT", "A < B", ""),
    ("LE", "A <= B", ""),
    ("GT", "A > B", ""),
    ("GE", "A >= B", ""),
    ("EQ", "A == B", ""),
    ("NE", "A != B", ""),
]


def _cmp(op, a, b):
    a = to_float_safe(a)
    b = to_float_safe(b)
    if op == "LT":
        r = a < b
    elif op == "LE":
        r = a <= b
    elif op == "GT":
        r = a > b
    elif op == "GE":
        r = a >= b
    elif op == "EQ":
        r = a == b
    else:  # NE
        r = a != b
    return 1.0 if r else 0.0


class AQCompareNode(AQBaseNode, Node):
    bl_idname = "AQMqttouchCompareNode"
    bl_label = "Compare"
    bl_icon = "ARROW_LEFTRIGHT"

    operation: EnumProperty(name="Operation", items=_OPS, default="GT")

    def init(self, context):
        self.new_input("A", "FLOAT")
        self.new_input("B", "FLOAT")
        self.new_output("Result", "BOOL")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

    def compute_output(self, socket):
        a = self.get_input("A", 0.0)
        b = self.get_input("B", 0.0)
        if is_array(a) or is_array(b):
            arr_a = list(a) if is_array(a) else [a]
            arr_b = list(b) if is_array(b) else [b]
            n = max(len(arr_a), len(arr_b)) or 0
            return [
                _cmp(self.operation,
                     arr_a[i % len(arr_a)] if arr_a else 0.0,
                     arr_b[i % len(arr_b)] if arr_b else 0.0)
                for i in range(n)
            ]
        return _cmp(self.operation, a, b)


classes = (AQCompareNode,)
