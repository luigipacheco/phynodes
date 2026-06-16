# GPL-3.0-or-later
# Node registry. Add new node modules here and they get registered + offered in
# the Add menu (see ui.py, which reads NODE_CLASSES).

import bpy

from . import value, math_node, map_node, mqtt_sub, mqtt_pub, prop_in, prop_out, debug_out

# Ordered for the Add menu, grouped by role.
NODE_CLASSES = (
    # Inputs / sources
    value.AQValueNode,
    prop_in.AQPropInNode,
    mqtt_sub.AQMqttSubNode,
    # Processors
    math_node.AQMathNode,
    map_node.AQMapNode,
    # Outputs / sinks
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
