# GPL-3.0-or-later
# Node registry. Add new node modules here and they get registered + offered in
# the Add menu (see ui.py, which reads NODE_CLASSES).

import bpy

from . import (
    value, input_nodes, math_node, map_node, clamp_node, compare_node,
    switch_node, array_node, color_node, json_node,
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
    prop_in.AQPropInNode,
    attribute_node.AQAttributeNode,
    mqtt_sub.AQMqttSubNode,
    # Processors
    math_node.AQMathNode,
    map_node.AQMapNode,
    clamp_node.AQClampNode,
    compare_node.AQCompareNode,
    switch_node.AQSwitchNode,
    array_node.AQArrayNode,
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
