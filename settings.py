# GPL-3.0-or-later
# Scene-level MQTT Nodes settings: the single shared broker connection config.

import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty, PointerProperty
from bpy.types import PropertyGroup


class MQTTNodesSettings(PropertyGroup):
    broker_host: StringProperty(
        name="Broker Host",
        description="IP or hostname of the MQTT broker",
        default="test.mosquitto.org",
    )
    broker_port: IntProperty(
        name="Port",
        default=1883,
        min=1,
        max=65535,
    )
    topic_prefix: StringProperty(
        name="Topic Prefix",
        description="Prepended to every node topic (e.g. /mqttnodes/)",
        default="/mqttnodes/",
    )
    enabled: BoolProperty(
        name="Graph Enabled",
        description="Evaluate the MQTT Nodes graph and exchange MQTT messages",
        default=True,
    )


def register():
    bpy.utils.register_class(MQTTNodesSettings)
    bpy.types.Scene.aq_mqttouch = PointerProperty(type=MQTTNodesSettings)


def unregister():
    del bpy.types.Scene.aq_mqttouch
    bpy.utils.unregister_class(MQTTNodesSettings)
