# GPL-3.0-or-later
# MQTT PUB node (sink): publishes its input value to a topic when it changes.

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Node

from ..base import AQBaseNode, format_for_mqtt
from ..connection import manager


class AQMqttPubNode(AQBaseNode, Node):
    bl_idname = "MQTTNodesMqttPubNode"
    bl_label = "MQTT PUB"
    bl_icon = "EXPORT"

    is_sink = True

    topic: StringProperty(
        name="Topic",
        description="Topic postfix to publish to (appended to the scene topic prefix)",
        default="command",
    )
    only_on_change: BoolProperty(
        name="Only on Change",
        description="Publish only when the value differs from the last sent value",
        default=True,
    )
    # Last published payload, kept to suppress duplicate publishes. The flag
    # forces a publish the first tick (a StringProperty cannot hold a null
    # sentinel, and any string could legitimately be a payload).
    last_payload: StringProperty(default="", options={"HIDDEN"})
    has_published: BoolProperty(default=False, options={"HIDDEN"})

    def init(self, context):
        self.new_input("Value", "ANY")

    def draw_buttons(self, context, layout):
        layout.prop(self, "topic", text="")
        layout.prop(self, "only_on_change")

    def evaluate_sink(self):
        value = self.get_input("Value", 0.0)
        payload = format_for_mqtt(value)
        if self.only_on_change and self.has_published and payload == self.last_payload:
            return
        if manager.publish(self.topic, payload):
            self.last_payload = payload
            self.has_published = True


classes = (AQMqttPubNode,)
