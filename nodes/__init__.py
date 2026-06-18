# GPL-3.0-or-later
# Node registry. Add new node modules here and they get registered + offered in
# the Add menu (see ui.py, which reads NODE_CLASSES).

import bpy

from . import (
    value, input_nodes, time_node, math_node, map_node, clamp_node,
    easing_node, float_curve, compare_node, switch_node, array_node,
    array_reduce, string_node, color_node, json_node,
    mqtt_sub, mqtt_pub, prop_in, attribute_node, prop_out, custom_prop,
    debug_out,
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
    attribute_node.AQAttributeNode,
    mqtt_sub.AQMqttSubNode,
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
    debug_out.AQDebugNode,
)


def register():
    for cls in NODE_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(NODE_CLASSES):
        bpy.utils.unregister_class(cls)
