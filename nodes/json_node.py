# GPL-3.0-or-later
# JSON Parse / Stringify nodes.

import json
import bpy
from bpy.types import Node

from ..base import AQBaseNode


class AQJsonParseNode(AQBaseNode, Node):
    bl_idname = "PhyNodesJsonParseNode"
    bl_label = "JSON Parse"
    bl_icon = "IMPORT"

    def init(self, context):
        self.new_input("JSON", "STRING")
        self.new_output("Value", "ANY")

    def compute_output(self, socket):
        s = self.get_input("JSON", "")
        if not isinstance(s, str):
            return s
        try:
            return json.loads(s)
        except (ValueError, TypeError):
            return s


class AQJsonStringifyNode(AQBaseNode, Node):
    bl_idname = "PhyNodesJsonStringifyNode"
    bl_label = "JSON Stringify"
    bl_icon = "EXPORT"

    def init(self, context):
        self.new_input("Value", "ANY")
        self.new_output("JSON", "STRING")

    def compute_output(self, socket):
        value = self.get_input("Value", 0.0)
        try:
            return json.dumps(value)
        except (TypeError, ValueError):
            return str(value)


classes = (AQJsonParseNode, AQJsonStringifyNode)
