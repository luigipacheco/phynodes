# GPL-3.0-or-later
# Easing node: remap a 0..1 factor through a named easing curve (Penner-style),
# then optionally into a To Min/To Max range. Element-wise on arrays. Pairs well
# with Timer/Scene Time for animation-feeling motion without keyframes.

import math
import bpy
from bpy.props import EnumProperty
from bpy.types import Node

from ..base import AQBaseNode, is_array, to_float_safe

_MODES = [
    ("LINEAR", "Linear", ""),
    ("IN_SINE", "Sine In", ""),
    ("OUT_SINE", "Sine Out", ""),
    ("INOUT_SINE", "Sine In/Out", ""),
    ("IN_QUAD", "Quad In", ""),
    ("OUT_QUAD", "Quad Out", ""),
    ("INOUT_QUAD", "Quad In/Out", ""),
    ("IN_CUBIC", "Cubic In", ""),
    ("OUT_CUBIC", "Cubic Out", ""),
    ("INOUT_CUBIC", "Cubic In/Out", ""),
    ("IN_EXPO", "Expo In", ""),
    ("OUT_EXPO", "Expo Out", ""),
    ("INOUT_EXPO", "Expo In/Out", ""),
    ("IN_CIRC", "Circular In", ""),
    ("OUT_CIRC", "Circular Out", ""),
    ("INOUT_CIRC", "Circular In/Out", ""),
    ("IN_BACK", "Back In", ""),
    ("OUT_BACK", "Back Out", ""),
    ("INOUT_BACK", "Back In/Out", ""),
    ("IN_ELASTIC", "Elastic In", ""),
    ("OUT_ELASTIC", "Elastic Out", ""),
    ("INOUT_ELASTIC", "Elastic In/Out", ""),
    ("IN_BOUNCE", "Bounce In", ""),
    ("OUT_BOUNCE", "Bounce Out", ""),
    ("INOUT_BOUNCE", "Bounce In/Out", ""),
]

_PI = math.pi
_BACK_C1 = 1.70158
_BACK_C2 = _BACK_C1 * 1.525
_BACK_C3 = _BACK_C1 + 1.0


def _bounce_out(t):
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def _ease(mode, t):
    # Clamp the domain so curves stay well-defined past the 0..1 window.
    t = max(0.0, min(1.0, t))
    if mode == "LINEAR":
        return t
    if mode == "IN_SINE":
        return 1 - math.cos((t * _PI) / 2)
    if mode == "OUT_SINE":
        return math.sin((t * _PI) / 2)
    if mode == "INOUT_SINE":
        return -(math.cos(_PI * t) - 1) / 2
    if mode == "IN_QUAD":
        return t * t
    if mode == "OUT_QUAD":
        return 1 - (1 - t) * (1 - t)
    if mode == "INOUT_QUAD":
        return 2 * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 2) / 2
    if mode == "IN_CUBIC":
        return t ** 3
    if mode == "OUT_CUBIC":
        return 1 - math.pow(1 - t, 3)
    if mode == "INOUT_CUBIC":
        return 4 * t ** 3 if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2
    if mode == "IN_EXPO":
        return 0.0 if t == 0 else math.pow(2, 10 * t - 10)
    if mode == "OUT_EXPO":
        return 1.0 if t == 1 else 1 - math.pow(2, -10 * t)
    if mode == "INOUT_EXPO":
        if t == 0:
            return 0.0
        if t == 1:
            return 1.0
        return (math.pow(2, 20 * t - 10) / 2 if t < 0.5
                else (2 - math.pow(2, -20 * t + 10)) / 2)
    if mode == "IN_CIRC":
        return 1 - math.sqrt(1 - math.pow(t, 2))
    if mode == "OUT_CIRC":
        return math.sqrt(1 - math.pow(t - 1, 2))
    if mode == "INOUT_CIRC":
        if t < 0.5:
            return (1 - math.sqrt(1 - math.pow(2 * t, 2))) / 2
        return (math.sqrt(1 - math.pow(-2 * t + 2, 2)) + 1) / 2
    if mode == "IN_BACK":
        return _BACK_C3 * t ** 3 - _BACK_C1 * t * t
    if mode == "OUT_BACK":
        return 1 + _BACK_C3 * math.pow(t - 1, 3) + _BACK_C1 * math.pow(t - 1, 2)
    if mode == "INOUT_BACK":
        if t < 0.5:
            return (math.pow(2 * t, 2) * ((_BACK_C2 + 1) * 2 * t - _BACK_C2)) / 2
        return (math.pow(2 * t - 2, 2) * ((_BACK_C2 + 1) * (t * 2 - 2) + _BACK_C2) + 2) / 2
    if mode == "IN_ELASTIC":
        if t == 0:
            return 0.0
        if t == 1:
            return 1.0
        c4 = (2 * _PI) / 3
        return -math.pow(2, 10 * t - 10) * math.sin((t * 10 - 10.75) * c4)
    if mode == "OUT_ELASTIC":
        if t == 0:
            return 0.0
        if t == 1:
            return 1.0
        c4 = (2 * _PI) / 3
        return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1
    if mode == "INOUT_ELASTIC":
        if t == 0:
            return 0.0
        if t == 1:
            return 1.0
        c5 = (2 * _PI) / 4.5
        if t < 0.5:
            return -(math.pow(2, 20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2
        return (math.pow(2, -20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1
    if mode == "IN_BOUNCE":
        return 1 - _bounce_out(1 - t)
    if mode == "OUT_BOUNCE":
        return _bounce_out(t)
    if mode == "INOUT_BOUNCE":
        if t < 0.5:
            return (1 - _bounce_out(1 - 2 * t)) / 2
        return (1 + _bounce_out(2 * t - 1)) / 2
    return t


class AQEasingNode(AQBaseNode, Node):
    bl_idname = "PhyNodesEasingNode"
    bl_label = "Easing"
    bl_icon = "IPO_EASE_IN_OUT"

    mode: EnumProperty(name="Easing", items=_MODES, default="INOUT_QUAD")

    def init(self, context):
        self.new_input("Fac", "FLOAT", default=0.0, min=0.0, max=1.0)
        self.new_input("To Min", "FLOAT", default=0.0)
        self.new_input("To Max", "FLOAT", default=1.0)
        self.new_output("Result", "FLOAT")

    def draw_label(self):
        for ident, label, _ in _MODES:
            if ident == self.mode:
                return label
        return self.bl_label

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")

    def _one(self, x, lo, hi):
        e = _ease(self.mode, to_float_safe(x))
        return lo + (hi - lo) * e

    def compute_output(self, socket):
        fac = self.get_input("Fac", 0.0)
        lo = to_float_safe(self.get_input("To Min", 0.0))
        hi = to_float_safe(self.get_input("To Max", 1.0))
        if is_array(fac):
            return [self._one(x, lo, hi) for x in fac]
        return self._one(fac, lo, hi)


classes = (AQEasingNode,)
