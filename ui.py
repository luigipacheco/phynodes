# GPL-3.0-or-later
# Node-editor UI: the Add-node menu for the MQTTouch tree, an N-panel for the
# shared broker connection, and connect/disconnect operators.

import bpy
from bpy.types import Menu, Panel, Operator

from .tree import TREE_ID
from .nodes import NODE_CLASSES
from .connection import manager


# ---------------------------------------------------------------------------
# Add menu
# ---------------------------------------------------------------------------

class NODE_MT_aq_mqttouch_add(Menu):
    bl_idname = "NODE_MT_aq_mqttouch_add"
    bl_label = "MQTTouch"

    def draw(self, context):
        layout = self.layout
        for cls in NODE_CLASSES:
            op = layout.operator("node.add_node", text=cls.bl_label)
            op.type = cls.bl_idname
            op.use_transform = True


def _draw_add_menu(self, context):
    space = context.space_data
    if space and getattr(space, "tree_type", "") == TREE_ID:
        self.layout.menu(NODE_MT_aq_mqttouch_add.bl_idname)


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class AQ_OT_mqttouch_connect(Operator):
    bl_idname = "aq_mqttouch.connect"
    bl_label = "Connect"
    bl_description = "Connect the shared MQTT client to the broker"

    def execute(self, context):
        s = context.scene.aq_mqttouch
        if not manager.available:
            self.report({"ERROR"}, "paho-mqtt is not installed in Blender's Python")
            return {"CANCELLED"}
        ok = manager.run(s.broker_host, s.topic_prefix, s.broker_port)
        if not ok:
            self.report({"ERROR"}, manager.last_error or "Could not start client")
            return {"CANCELLED"}
        self.report({"INFO"}, "Connecting to %s" % s.broker_host)
        return {"FINISHED"}


class AQ_OT_mqttouch_disconnect(Operator):
    bl_idname = "aq_mqttouch.disconnect"
    bl_label = "Disconnect"
    bl_description = "Disconnect the shared MQTT client"

    def execute(self, context):
        manager.stop()
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# N-panel
# ---------------------------------------------------------------------------

class NODE_PT_aq_mqttouch(Panel):
    bl_idname = "NODE_PT_aq_mqttouch"
    bl_label = "MQTTouch Broker"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "MQTTouch"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space and getattr(space, "tree_type", "") == TREE_ID

    def draw(self, context):
        layout = self.layout
        s = context.scene.aq_mqttouch

        if not manager.available:
            box = layout.box()
            box.label(text="paho-mqtt not installed", icon="ERROR")
            box.label(text="pip install paho-mqtt")

        col = layout.column(align=True)
        col.prop(s, "broker_host")
        col.prop(s, "broker_port")
        col.prop(s, "topic_prefix")

        layout.prop(s, "enabled")

        row = layout.row(align=True)
        if manager.connected:
            row.label(text="Connected", icon="LINKED")
            row.operator(AQ_OT_mqttouch_disconnect.bl_idname, text="", icon="X")
        else:
            row.operator(AQ_OT_mqttouch_connect.bl_idname, icon="PLAY")

        if manager.last_error:
            layout.label(text=manager.last_error[:48], icon="ERROR")


classes = (
    NODE_MT_aq_mqttouch_add,
    AQ_OT_mqttouch_connect,
    AQ_OT_mqttouch_disconnect,
    NODE_PT_aq_mqttouch,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.NODE_MT_add.append(_draw_add_menu)


def unregister():
    bpy.types.NODE_MT_add.remove(_draw_add_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
