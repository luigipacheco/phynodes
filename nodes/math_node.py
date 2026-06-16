# GPL-3.0-or-later
# Math node: mirrors Blender's built-in Math node (operation dropdown), with the
# scalar + element-wise array behavior from mqttouch's MathNode.

import math
import bpy
from bpy.props import EnumProperty
from bpy.types import Node

from ..base import AQBaseNode, is_array, to_float_safe, flatten_array

_OPS = [
    ("ADD", "Add", ""),
    ("SUBTRACT", "Subtract", ""),
    ("MULTIPLY", "Multiply", ""),
    ("DIVIDE", "Divide", ""),
    ("POWER", "Power", ""),
    ("MODULO", "Modulo", ""),
    ("MINIMUM", "Minimum", ""),
    ("MAXIMUM", "Maximum", ""),
    ("SINE", "Sine", ""),
    ("COSINE", "Cosine", ""),
    ("TANGENT", "Tangent", ""),
    ("ARCTAN2", "Arctan2", ""),
    ("ROUND", "Round", ""),
    ("FLOOR", "Floor", ""),
    ("CEIL", "Ceil", ""),
    ("SQRT", "Square Root", ""),
    ("ABSOLUTE", "Absolute", ""),
    ("SIGN", "Sign", ""),
    ("LOG", "Logarithm", ""),
    ("EXP", "Exponent", ""),
]


def _scalar(op, a, b):
    a = to_float_safe(a)
    b = to_float_safe(b)
    try:
        if op == "ADD":
            return a + b
        if op == "SUBTRACT":
            return a - b
        if op == "MULTIPLY":
            return a * b
        if op == "DIVIDE":
            return a / b if b != 0.0 else 0.0
        if op == "POWER":
            return math.pow(a, b)
        if op == "MODULO":
            return math.fmod(a, b) if b != 0.0 else 0.0
        if op == "MINIMUM":
            return min(a, b)
        if op == "MAXIMUM":
            return max(a, b)
        if op == "SINE":
            return math.sin(a)
        if op == "COSINE":
            return math.cos(a)
        if op == "TANGENT":
            return math.tan(a)
        if op == "ARCTAN2":
            return math.atan2(a, b)
        if op == "ROUND":
            return float(round(a))
        if op == "FLOOR":
            return math.floor(a)
        if op == "CEIL":
            return math.ceil(a)
        if op == "SQRT":
            return math.sqrt(abs(a))
        if op == "ABSOLUTE":
            return abs(a)
        if op == "SIGN":
            return float((a > 0) - (a < 0))
        if op == "LOG":
            return math.log(a) if a > 0.0 else 0.0
        if op == "EXP":
            return math.exp(a)
    except (ValueError, OverflowError):
        return 0.0
    return 0.0


class AQMathNode(AQBaseNode, Node):
    bl_idname = "PhyNodesMathNode"
    bl_label = "Math"
    bl_icon = "PLUS"

    operation: EnumProperty(name="Operation", items=_OPS, default="MULTIPLY")

    def init(self, context):
        self.new_input("A")
        self.new_input("B", default=1.0)
        self.new_output("Result", "FLOAT")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

    def compute_output(self, socket):
        a = self.get_input("A", 0.0)
        b = self.get_input("B", 0.0)
        if is_array(a) or is_array(b):
            return self._compute_array(a, b)
        return _scalar(self.operation, a, b)

    def _compute_array(self, a, b):
        arr_a = list(a) if is_array(a) else [a]
        arr_b = list(b) if is_array(b) else [b]
        n = max(len(arr_a), len(arr_b)) or 0
        out = []
        for i in range(n):
            va = arr_a[i % len(arr_a)] if arr_a else 0.0
            vb = arr_b[i % len(arr_b)] if arr_b else 0.0
            if is_array(va) or is_array(vb):
                # one level of nesting: broadcast against the scalar
                inner = va if is_array(va) else vb
                scalar = vb if is_array(va) else va
                out.append([_scalar(self.operation, x, scalar) for x in flatten_array(inner)])
            else:
                out.append(_scalar(self.operation, va, vb))
        return out


classes = (AQMathNode,)
