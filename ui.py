# GPL-3.0-or-later
# Node-editor UI: a categorized Add menu (geometry-nodes style), an N-panel for
# the shared broker connection, and connect/disconnect operators.

import time

import bpy
from bpy.props import StringProperty
from bpy.types import Menu, Panel, Operator

from .tree import TREE_ID
from .connection import manager
from .nodes import (
    value, input_nodes, color_node, time_node, prop_in, attribute_node,
    mqtt_sub, math_node, map_node, clamp_node, compare_node, switch_node,
    array_node, json_node, prop_out, custom_prop, mqtt_pub, debug_out,
)

# Blender's own helper for adding node-type entries to a menu (consistent with
# how the built-in node Add menus are built). Fall back if unavailable.
try:
    from bl_ui import node_add_menu
except Exception:
    node_add_menu = None


# ---------------------------------------------------------------------------
# Add menu — categories appear directly in the node editor's Add menu, like
# geometry nodes (Input / Math / Logic / ...), each a submenu.
# ---------------------------------------------------------------------------

CATEGORIES = [
    ("Input", [
        value.AQValueNode,
        input_nodes.AQBooleanNode,
        input_nodes.AQIntegerNode,
        input_nodes.AQVectorNode,
        input_nodes.AQStringNode,
        color_node.AQColorNode,
        time_node.AQSceneTimeNode,
        time_node.AQTimerNode,
        prop_in.AQPropInNode,
        attribute_node.AQAttributeNode,
    ]),
    ("Math", [math_node.AQMathNode, map_node.AQMapNode, clamp_node.AQClampNode]),
    ("Logic", [compare_node.AQCompareNode, switch_node.AQSwitchNode]),
    ("Array", [array_node.AQArrayNode]),
    ("JSON", [json_node.AQJsonParseNode, json_node.AQJsonStringifyNode]),
    ("MQTT", [mqtt_sub.AQMqttSubNode, mqtt_pub.AQMqttPubNode]),
    ("Output", [
        custom_prop.AQCustomPropertyNode,
        prop_out.AQPropOutNode,
        debug_out.AQDebugNode,
    ]),
]


def _make_category_menu(label, node_classes):
    def draw(self, context):
        layout = self.layout
        for cls in node_classes:
            if node_add_menu is not None:
                node_add_menu.add_node_type(layout, cls.bl_idname)
            else:
                op = layout.operator("node.add_node", text=cls.bl_label)
                op.type = cls.bl_idname
                op.use_transform = True

    slug = label.lower().replace(" ", "_")
    return type(
        "NODE_MT_phynodes_" + slug,
        (Menu,),
        {
            "bl_idname": "NODE_MT_phynodes_" + slug,
            "bl_label": label,
            "draw": draw,
        },
    )


_category_menus = [_make_category_menu(lbl, classes) for lbl, classes in CATEGORIES]


def _draw_add_menu(self, context):
    space = context.space_data
    if not (space and getattr(space, "tree_type", "") == TREE_ID):
        return
    layout = self.layout
    layout.separator()
    for menu in _category_menus:
        layout.menu(menu.bl_idname)


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class PHYNODES_OT_connect(Operator):
    bl_idname = "phynodes.connect"
    bl_label = "Connect"
    bl_description = "Connect the shared MQTT client to the broker"

    def execute(self, context):
        s = context.scene.phynodes
        if not manager.available:
            self.report({"ERROR"}, "paho-mqtt is not installed in Blender's Python")
            return {"CANCELLED"}
        ok = manager.run(s.broker_host, s.topic_prefix, s.broker_port)
        if not ok:
            self.report({"ERROR"}, manager.last_error or "Could not start client")
            return {"CANCELLED"}
        self.report({"INFO"}, "Connecting to %s" % s.broker_host)
        return {"FINISHED"}


class PHYNODES_OT_disconnect(Operator):
    bl_idname = "phynodes.disconnect"
    bl_label = "Disconnect"
    bl_description = "Disconnect the shared MQTT client"

    def execute(self, context):
        manager.stop()
        return {"FINISHED"}


class PHYNODES_OT_reset_timer(Operator):
    bl_idname = "phynodes.reset_timer"
    bl_label = "Reset Timer"
    bl_description = "Reset this Timer node's elapsed time to zero"

    tree_name: StringProperty()
    node_name: StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None:
            return {"CANCELLED"}
        node["start"] = time.time()
        return {"FINISHED"}


class PHYNODES_OT_copy_driver_path(Operator):
    bl_idname = "phynodes.copy_driver_path"
    bl_label = "Copy Driver Path"
    bl_description = "Copy this property's full data path to the clipboard for use in a driver"

    path: StringProperty()

    def execute(self, context):
        if not self.path:
            self.report({"WARNING"}, "No path to copy")
            return {"CANCELLED"}
        context.window_manager.clipboard = self.path
        self.report({"INFO"}, "Copied: " + self.path)
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# N-panel
# ---------------------------------------------------------------------------

class NODE_PT_phynodes(Panel):
    bl_idname = "NODE_PT_phynodes"
    bl_label = "PhyNodes Broker"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "PhyNodes"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space and getattr(space, "tree_type", "") == TREE_ID

    def draw(self, context):
        layout = self.layout
        s = context.scene.phynodes

        if not manager.available:
            box = layout.box()
            box.label(text="paho-mqtt not installed", icon="ERROR")
            box.label(text="pip install paho-mqtt")

        col = layout.column(align=True)
        col.prop(s, "broker_host")
        col.prop(s, "broker_port")
        col.prop(s, "topic_prefix")

        layout.prop(s, "enabled")
        layout.prop(s, "eval_interval")

        row = layout.row(align=True)
        if manager.connected:
            row.label(text="Connected", icon="LINKED")
            row.operator(PHYNODES_OT_disconnect.bl_idname, text="", icon="X")
        else:
            row.operator(PHYNODES_OT_connect.bl_idname, icon="PLAY")

        if manager.last_error:
            layout.label(text=manager.last_error[:48], icon="ERROR")


classes = tuple(_category_menus) + (
    PHYNODES_OT_connect,
    PHYNODES_OT_disconnect,
    PHYNODES_OT_copy_driver_path,
    PHYNODES_OT_reset_timer,
    NODE_PT_phynodes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.NODE_MT_add.append(_draw_add_menu)


def unregister():
    bpy.types.NODE_MT_add.remove(_draw_add_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
