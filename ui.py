# GPL-3.0-or-later
# Node-editor UI: a categorized Add menu (geometry-nodes style), an N-panel
# listing the scene's connections, and connector operators.

import time

import bpy
from bpy.props import StringProperty
from bpy.types import Menu, Panel, Operator, UIList

from .tree import TREE_ID
from . import connectors
from .nodes import (
    value, input_nodes, color_node, time_node, prop_in, attribute_node,
    mqtt_sub, math_node, map_node, clamp_node, easing_node, compare_node,
    float_curve, switch_node, array_node, array_reduce, string_node, json_node,
    prop_out, custom_prop, mqtt_pub, osc_in, osc_out, debug_out,
)

# Blender's own helper for adding node-type entries to a menu, when available.
# Its API differs across versions (e.g. Blender 5.2 has no add_node_type), so we
# only use it when the function exists and otherwise fall back to node.add_node.
try:
    from bl_ui import node_add_menu
    if not hasattr(node_add_menu, "add_node_type"):
        node_add_menu = None
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
    ("Math", [
        math_node.AQMathNode, map_node.AQMapNode, clamp_node.AQClampNode,
        easing_node.AQEasingNode, float_curve.AQFloatCurveNode,
    ]),
    ("Logic", [compare_node.AQCompareNode, switch_node.AQSwitchNode]),
    ("Array", [array_node.AQArrayNode, array_reduce.AQArrayReduceNode]),
    ("String", [string_node.AQStringOpNode]),
    ("JSON", [json_node.AQJsonParseNode, json_node.AQJsonStringifyNode]),
    ("MQTT", [mqtt_sub.AQMqttSubNode, mqtt_pub.AQMqttPubNode]),
    ("OSC", [osc_in.AQOscInNode, osc_out.AQOscOutNode]),
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
# Connector operators
# ---------------------------------------------------------------------------

def _active_item(settings):
    idx = settings.active_connector_index
    if 0 <= idx < len(settings.connectors):
        return settings.connectors[idx]
    return None


def _unique_name(collection, base):
    existing = {c.name for c in collection}
    name = base
    i = 1
    while name in existing:
        name = "%s.%03d" % (base, i)
        i += 1
    return name


class PHYNODES_OT_connector_add(Operator):
    bl_idname = "phynodes.connector_add"
    bl_label = "Add Connection"
    bl_description = "Add a new connection to the list"

    def execute(self, context):
        s = context.scene.phynodes
        name = _unique_name(s.connectors, "MQTT")
        item = s.connectors.add()
        item.name = name
        s.active_connector_index = len(s.connectors) - 1
        return {"FINISHED"}


class PHYNODES_OT_connector_remove(Operator):
    bl_idname = "phynodes.connector_remove"
    bl_label = "Remove Connection"
    bl_description = "Disconnect and remove the selected connection"

    def execute(self, context):
        s = context.scene.phynodes
        item = _active_item(s)
        if item is None:
            return {"CANCELLED"}
        connectors.stop(item.name)
        s.connectors.remove(s.active_connector_index)
        s.active_connector_index = min(
            s.active_connector_index, len(s.connectors) - 1)
        connectors.prune({c.name for c in s.connectors})
        return {"FINISHED"}


class PHYNODES_OT_connector_connect(Operator):
    bl_idname = "phynodes.connector_connect"
    bl_label = "Connect"
    bl_description = "Start the selected connection"

    def execute(self, context):
        s = context.scene.phynodes
        item = _active_item(s)
        if item is None:
            return {"CANCELLED"}
        cls = connectors.TYPES.get(item.conn_type)
        if cls is None:
            self.report({"ERROR"}, "Unknown connector type: %s" % item.conn_type)
            return {"CANCELLED"}
        if not cls.available():
            self.report({"ERROR"}, "%s is not installed in Blender's Python" % cls.requires)
            return {"CANCELLED"}
        # Sweep instances orphaned by renamed/removed entries before starting.
        connectors.prune({c.name for c in s.connectors})
        connectors.start(item.name, item.conn_type, cls.config_from_item(item))
        self.report({"INFO"}, "Connecting '%s'..." % item.name)
        return {"FINISHED"}


class PHYNODES_OT_connector_disconnect(Operator):
    bl_idname = "phynodes.connector_disconnect"
    bl_label = "Disconnect"
    bl_description = "Stop the selected connection"

    def execute(self, context):
        s = context.scene.phynodes
        item = _active_item(s)
        if item is not None:
            connectors.stop(item.name)
        connectors.prune({c.name for c in s.connectors})
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Node operators
# ---------------------------------------------------------------------------

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

_STATUS_ICONS = {
    connectors.CONNECTED: "LINKED",
    connectors.CONNECTING: "SORTTIME",
    connectors.ERROR: "ERROR",
    connectors.DISCONNECTED: "UNLINKED",
}


class PHYNODES_UL_connectors(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False)
        conn = connectors.get(item.name)
        status = conn.status if conn is not None else connectors.DISCONNECTED
        row.label(text="", icon=_STATUS_ICONS[status])


class NODE_PT_phynodes(Panel):
    bl_idname = "NODE_PT_phynodes"
    bl_label = "Connections"
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

        row = layout.row()
        row.template_list("PHYNODES_UL_connectors", "", s, "connectors",
                          s, "active_connector_index", rows=2)
        col = row.column(align=True)
        col.operator(PHYNODES_OT_connector_add.bl_idname, text="", icon="ADD")
        col.operator(PHYNODES_OT_connector_remove.bl_idname, text="", icon="REMOVE")

        item = _active_item(s)
        if item is not None:
            box = layout.box()
            box.prop(item, "conn_type", text="Type")
            cls = connectors.TYPES.get(item.conn_type)
            if cls is not None:
                if not cls.available():
                    box.label(text="%s not installed" % cls.requires, icon="ERROR")
                cls.draw_config(box, item)

            conn = connectors.get(item.name)
            status = conn.status if conn is not None else connectors.DISCONNECTED
            row = box.row(align=True)
            if status == connectors.CONNECTED:
                row.label(text="Connected", icon="LINKED")
                row.operator(PHYNODES_OT_connector_disconnect.bl_idname, text="", icon="X")
            elif status == connectors.CONNECTING:
                row.label(text="Connecting...", icon="SORTTIME")
                row.operator(PHYNODES_OT_connector_disconnect.bl_idname, text="", icon="X")
            else:
                row.operator(PHYNODES_OT_connector_connect.bl_idname, icon="PLAY")
            if conn is not None and conn.last_error:
                box.label(text=conn.last_error[:48], icon="ERROR")

        layout.prop(s, "enabled")
        layout.prop(s, "eval_interval")


classes = tuple(_category_menus) + (
    PHYNODES_OT_connector_add,
    PHYNODES_OT_connector_remove,
    PHYNODES_OT_connector_connect,
    PHYNODES_OT_connector_disconnect,
    PHYNODES_OT_copy_driver_path,
    PHYNODES_OT_reset_timer,
    PHYNODES_UL_connectors,
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
