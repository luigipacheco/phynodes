# GPL-3.0-or-later
# MQTT SUB node: outputs the latest message received on its topic.
# Uses the single shared connection (settings broker + topic prefix).

import bpy
from bpy.props import StringProperty
from bpy.types import Node

from ..base import AQBaseNode, parse_payload, is_array
from ..connection import manager


class AQMqttSubNode(AQBaseNode, Node):
    bl_idname = "PhyNodesMqttSubNode"
    bl_label = "MQTT SUB"
    bl_icon = "IMPORT"

    topic: StringProperty(
        name="Topic",
        description="Topic postfix to subscribe to (appended to the scene topic prefix)",
        default="sensor",
    )

    def init(self, context):
        self.new_output("Value", "ANY")

    def draw_buttons(self, context, layout):
        layout.prop(self, "topic", text="")
        raw = manager.get_message(self.topic)
        if raw is None:
            layout.label(text="(no message yet)", icon="DOT")
        else:
            value = parse_payload(raw)
            if is_array(value):
                layout.label(text="Array[%d]" % len(value))
            else:
                layout.label(text="= %s" % str(value)[:24])

    def compute_output(self, socket):
        raw = manager.get_message(self.topic)
        if raw is None:
            return 0.0
        return parse_payload(raw)


classes = (AQMqttSubNode,)
