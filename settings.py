# GPL-3.0-or-later
# Scene-level PhyNodes settings: the single shared broker connection config.

import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty, PointerProperty
from bpy.types import PropertyGroup


class PhyNodesSettings(PropertyGroup):
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
        description="Prepended to every node topic (e.g. /phynodes/)",
        default="/phynodes/",
    )
    enabled: BoolProperty(
        name="Graph Enabled",
        description="Evaluate the PhyNodes graph and exchange MQTT messages",
        default=True,
    )


def register():
    bpy.utils.register_class(PhyNodesSettings)
    bpy.types.Scene.phynodes = PointerProperty(type=PhyNodesSettings)


def unregister():
    del bpy.types.Scene.phynodes
    bpy.utils.unregister_class(PhyNodesSettings)
