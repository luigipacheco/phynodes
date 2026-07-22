# GPL-3.0-or-later
# MQTT PUB node (sink): publishes its input value to a topic when it changes.

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Node

from ..base import format_for_mqtt
from .io_base import ConnectorIONode

# Last payload sent per node (keyed by node pointer), to suppress duplicate
# publishes. Runtime-only on purpose: storing it in node properties would
# dirty the .blend and push depsgraph updates on every publish (up to the
# timer rate).
_last_sent = {}


class AQMqttPubNode(ConnectorIONode, Node):
    bl_idname = "PhyNodesMqttPubNode"
    bl_label = "MQTT PUB"
    bl_icon = "EXPORT"

    is_sink = True
    connector_type_id = "MQTT"

    connector_name: StringProperty(
        name="Connector",
        description="Named connection to use (empty = first MQTT connection)",
        default="",
    )
    topic: StringProperty(
        name="Topic",
        description="Topic postfix to publish to (appended to the connector's topic prefix)",
        default="command",
    )
    only_on_change: BoolProperty(
        name="Only on Change",
        description="Publish only when the value differs from the last sent value",
        default=True,
    )

    def init(self, context):
        self.new_input("Value", "ANY")

    def draw_buttons(self, context, layout):
        self.draw_connector_selector(context, layout)
        layout.prop(self, "topic", text="")
        layout.prop(self, "only_on_change")

    def evaluate_sink(self):
        conn = self.get_connector()
        if conn is None:
            return
        # FabNodes safety rule: while system/estop is latched, control nodes
        # fail safe and suppress outbound values.
        if getattr(conn, "estop_active", False):
            return
        value = self.get_input("Value", 0.0)
        payload = format_for_mqtt(value)
        key = self.as_pointer()
        if self.only_on_change and _last_sent.get(key) == payload:
            return
        if conn.write(self.topic, payload):
            _last_sent[key] = payload


classes = (AQMqttPubNode,)
