# GPL-3.0-or-later
# Node registry. Add new node modules here and they get registered + offered in
# the Add menu (see ui.py, which reads NODE_CLASSES).

import bpy
from bpy.app.handlers import persistent

from . import (
    value, input_nodes, time_node, math_node, map_node, clamp_node,
    easing_node, float_curve, compare_node, switch_node, array_node,
    array_reduce, string_node, color_node, json_node,
    mqtt_sub, mqtt_pub, osc_in, osc_out, prop_in, attribute_node, prop_out,
    custom_prop, debug_out, aq_index,
)

# Ordered for the Add menu, grouped by role.
NODE_CLASSES = (
    # Inputs / sources
    value.AQValueNode,
    input_nodes.AQBooleanNode,
    input_nodes.AQIntegerNode,
    input_nodes.AQVectorNode,
    input_nodes.AQStringNode,
    color_node.AQColorNode,
    time_node.AQSceneTimeNode,
    time_node.AQTimerNode,
    prop_in.AQPropInNode,
    aq_index.AQAnimaquinaIndexNode,
    attribute_node.AQAttributeNode,
    mqtt_sub.AQMqttSubNode,
    osc_in.AQOscInNode,
    # Processors
    math_node.AQMathNode,
    map_node.AQMapNode,
    clamp_node.AQClampNode,
    easing_node.AQEasingNode,
    float_curve.AQFloatCurveNode,
    compare_node.AQCompareNode,
    switch_node.AQSwitchNode,
    array_node.AQArrayNode,
    array_reduce.AQArrayReduceNode,
    string_node.AQStringOpNode,
    json_node.AQJsonParseNode,
    json_node.AQJsonStringifyNode,
    # Outputs / sinks
    custom_prop.AQCustomPropertyNode,
    prop_out.AQPropOutNode,
    mqtt_pub.AQMqttPubNode,
    osc_out.AQOscOutNode,
    debug_out.AQDebugNode,
)


@persistent
def _on_load(*_args):
    attribute_node.version_index_sockets()


def _version_once():
    # Deferred to a timer: bpy.data is restricted while add-ons register during
    # Blender startup (same reason settings.py defers its migration).
    attribute_node.version_index_sockets()
    return None


def register():
    for cls in NODE_CLASSES:
        bpy.utils.register_class(cls)
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    bpy.app.timers.register(_version_once, first_interval=0.1)


def unregister():
    if bpy.app.timers.is_registered(_version_once):
        bpy.app.timers.unregister(_version_once)
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    for cls in reversed(NODE_CLASSES):
        bpy.utils.unregister_class(cls)
