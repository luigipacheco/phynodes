# GPL-3.0-or-later
# Array Reduce node: collapse an array (flattened, numeric) down to a single
# value -- sum, average, min/max, etc. Counterpart to the Array node.

import bpy
from bpy.props import EnumProperty
from bpy.types import Node

from ..base import AQBaseNode, is_array, to_float_safe, flatten_array

_OPS = [
    ("SUM", "Sum", "Total of all items"),
    ("PRODUCT", "Product", "All items multiplied"),
    ("MEAN", "Average", "Arithmetic mean"),
    ("MIN", "Minimum", "Smallest item"),
    ("MAX", "Maximum", "Largest item"),
    ("RANGE", "Range", "Max minus Min"),
    ("MEDIAN", "Median", "Middle value when sorted"),
    ("COUNT", "Count", "Number of items"),
    ("FIRST", "First", "First item"),
    ("LAST", "Last", "Last item"),
]


def _reduce(op, nums):
    if op == "SUM":
        return sum(nums)
    if op == "PRODUCT":
        p = 1.0
        for n in nums:
            p *= n
        return p
    if op == "MEAN":
        return sum(nums) / len(nums)
    if op == "MIN":
        return min(nums)
    if op == "MAX":
        return max(nums)
    if op == "RANGE":
        return max(nums) - min(nums)
    if op == "MEDIAN":
        s = sorted(nums)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
    if op == "FIRST":
        return nums[0]
    if op == "LAST":
        return nums[-1]
    return 0.0


class AQArrayReduceNode(AQBaseNode, Node):
    bl_idname = "PhyNodesArrayReduceNode"
    bl_label = "Array Reduce"
    bl_icon = "SEQ_LUMA_WAVEFORM"

    operation: EnumProperty(name="Operation", items=_OPS, default="SUM")

    def init(self, context):
        self.new_input("Array", "ANY")
        self.new_output("Result", "FLOAT")

    def draw_label(self):
        for ident, label, _ in _OPS:
            if ident == self.operation:
                return label
        return self.bl_label

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

    def compute_output(self, socket):
        value = self.get_input("Array", [])
        items = flatten_array(value) if is_array(value) else [value]
        nums = [to_float_safe(x) for x in items]
        if self.operation == "COUNT":
            return float(len(nums))
        if not nums:
            return 0.0
        return _reduce(self.operation, nums)


classes = (AQArrayReduceNode,)
