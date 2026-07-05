# GPL-3.0-or-later
# MQTT SUB node: outputs the latest message received on its topic, through a
# connector from the scene's connections list (empty name = first MQTT one).

import bpy
from bpy.props import StringProperty
from bpy.types import Node

from ..base import parse_payload, is_array
from .io_base import ConnectorIONode


class AQMqttSubNode(ConnectorIONode, Node):
    bl_idname = "PhyNodesMqttSubNode"
    bl_label = "MQTT SUB"
    bl_icon = "IMPORT"

    connector_type_id = "MQTT"

    connector_name: StringProperty(
        name="Connector",
        description="Named connection to use (empty = first MQTT connection)",
        default="",
    )
    topic: StringProperty(
        name="Topic",
        description="Topic postfix to subscribe to (appended to the connector's topic prefix)",
        default="sensor",
    )

    def init(self, context):
        self.new_output("Value", "ANY")

    def draw_buttons(self, context, layout):
        self.draw_connector_selector(context, layout)
        layout.prop(self, "topic", text="")
        conn = self.get_connector()
        if conn is None:
            layout.label(text="(not connected)", icon="UNLINKED")
            return
        conn.ensure_subscribed(self.topic)
        raw = conn.read(self.topic)
        if raw is None:
            layout.label(text="(no message yet)", icon="DOT")
        else:
            value = parse_payload(raw)
            if is_array(value):
                layout.label(text="Array[%d]" % len(value))
            else:
                layout.label(text="= %s" % str(value)[:24])

    def compute_output(self, socket):
        conn = self.get_connector()
        if conn is None:
            return 0.0
        conn.ensure_subscribed(self.topic)
        raw = conn.read(self.topic)
        if raw is None:
            return 0.0
        return parse_payload(raw)


classes = (AQMqttSubNode,)
