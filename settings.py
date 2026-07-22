# GPL-3.0-or-later
# Scene-level PhyNodes settings: the list of configured connections plus the
# evaluator toggles. Live connector objects are runtime-only (connectors/);
# only their configuration is stored here.

import bpy
from bpy.app.handlers import persistent
from bpy.props import (
    StringProperty, BoolProperty, IntProperty, FloatProperty, PointerProperty,
    CollectionProperty, EnumProperty,
)
from bpy.types import PropertyGroup

from .connectors import type_items, TYPES

# Static per release — connector types are registered at import time.
_CONNECTOR_TYPE_ITEMS = type_items()


def _on_type_change(self, context):
    """Switching an entry's transport resets its fields to that transport's
    defaults (an MQTT broker hostname is meaningless as an OSC send host)."""
    cls = TYPES.get(self.conn_type)
    if cls is not None:
        cls.apply_defaults(self)


class PhyNodesConnectorConfig(PropertyGroup):
    """One configured connection (an entry in scene.phynodes.connectors).

    Fields are a flat superset across transports; each connector class draws
    only the ones it uses (see Connector.draw_config)."""

    name: StringProperty(name="Name", default="Connector")
    conn_type: EnumProperty(
        name="Type",
        items=_CONNECTOR_TYPE_ITEMS,
        default="MQTT",
        update=_on_type_change,
    )
    host: StringProperty(
        name="Host",
        description="IP or hostname to connect to (MQTT broker / OSC send target)",
        default="test.mosquitto.org",
    )
    port: IntProperty(
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
    username: StringProperty(
        name="Username",
        description="MQTT username (leave empty for an anonymous broker)",
        default="",
    )
    password: StringProperty(
        name="Password",
        description="MQTT password (stored in the .blend in plain text)",
        default="",
        subtype="PASSWORD",
    )
    listen_port: IntProperty(
        name="Listen Port",
        description="UDP port to receive OSC on (0 = receive off)",
        default=9001,
        min=0,
        max=65535,
    )
    # FabNodes identity (MQTT only). When on, this connection announces itself
    # under fabnodes/1.1 so FabFlow discovers Blender like any ESP32: it
    # publishes a retained manifest derived from the MQTT PUB/SUB nodes that
    # use it, an online/offline $state (LWT), a diag/uptime heartbeat, and
    # honours the system/estop safety latch.
    fabnode_enabled: BoolProperty(
        name="Announce as FabNode",
        description="Publish a fabnodes/1.1 manifest so FabFlow discovers this "
                    "connection as a node; signals are derived from the MQTT "
                    "PUB/SUB nodes that use this connection",
        default=False,
    )
    fabnode_name: StringProperty(
        name="Node Name",
        description="FabNode identity (e.g. blender1). The manifest, $state and "
                    "diag topics live under this name",
        default="blender1",
    )
    fabnode_type: StringProperty(
        name="Node Type",
        description="FabNode type advertised in the manifest (FabFlow can style "
                    "it distinctly)",
        default="fab-blender",
    )


class PhyNodesSettings(PropertyGroup):
    connectors: CollectionProperty(type=PhyNodesConnectorConfig)
    active_connector_index: IntProperty(default=0)

    enabled: BoolProperty(
        name="Graph Enabled",
        description="Evaluate the PhyNodes graph and exchange messages",
        default=True,
    )
    eval_interval: FloatProperty(
        name="Refresh Interval",
        description="Seconds between graph evaluations (SUB read + publish). "
                    "Lower = more responsive, more CPU",
        default=0.05,
        min=0.005,
        max=5.0,
        soft_min=0.01,
        soft_max=1.0,
        subtype="TIME_ABSOLUTE",
        unit="TIME",
    )

    # Legacy pre-0.2 single-broker fields. Kept only so values saved in old
    # .blend files load and can be migrated into connectors[0]; not shown in
    # the UI anymore.
    broker_host: StringProperty(default="test.mosquitto.org", options={"HIDDEN"})
    broker_port: IntProperty(default=1883, min=1, max=65535, options={"HIDDEN"})
    topic_prefix: StringProperty(default="/phynodes/", options={"HIDDEN"})


def _ensure_connector_entries():
    """Give every scene at least one connector entry, seeded from the legacy
    single-broker fields (which carry old .blend files' values, or defaults)."""
    for scene in bpy.data.scenes:
        s = getattr(scene, "phynodes", None)
        if s is None or len(s.connectors):
            continue
        item = s.connectors.add()
        item.name = "Broker"
        item.conn_type = "MQTT"
        item.host = s.broker_host
        item.port = s.broker_port
        item.topic_prefix = s.topic_prefix


@persistent
def _on_load(*_args):
    _ensure_connector_entries()


def _migrate_once():
    # Deferred to a timer: bpy.data is restricted while add-ons register
    # during Blender startup.
    _ensure_connector_entries()
    return None


def register():
    bpy.utils.register_class(PhyNodesConnectorConfig)
    bpy.utils.register_class(PhyNodesSettings)
    bpy.types.Scene.phynodes = PointerProperty(type=PhyNodesSettings)
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    bpy.app.timers.register(_migrate_once, first_interval=0.1)


def unregister():
    if bpy.app.timers.is_registered(_migrate_once):
        bpy.app.timers.unregister(_migrate_once)
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    del bpy.types.Scene.phynodes
    bpy.utils.unregister_class(PhyNodesSettings)
    bpy.utils.unregister_class(PhyNodesConnectorConfig)
