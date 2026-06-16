# GPL-3.0-or-later
# Animaquina MQTTouch — a visual MQTT node graph for Blender.
#
# Ports the mqttouch (Godot) node editor into a native Blender NodeTree: wire
# Value / Math / Map / MQTT / Property nodes together and a timer evaluates the
# graph every ~50ms. Designed to live standalone now and fold into Animaquina
# as a sub-module later.

bl_info = {
    "name": "Animaquina MQTTouch",
    "author": "Luis Arturo Pacheco",
    "description": "Visual MQTT node graph: wire Blender properties and sensors through MQTT.",
    "blender": (4, 2, 0),
    "version": (0, 1, 0),
    "location": "Node Editor > MQTTouch",
    "warning": "Beta — requires paho-mqtt in Blender's Python.",
    "doc_url": "https://www.animaquina.com",
    "category": "Node",
}

import bpy

from . import settings, tree, base, evaluator, ui
from . import nodes as aq_nodes


def register():
    settings.register()
    tree.register()
    aq_nodes.register()
    ui.register()
    evaluator.register()


def unregister():
    evaluator.unregister()
    ui.unregister()
    aq_nodes.unregister()
    tree.unregister()
    settings.unregister()


if __name__ == "__main__":
    register()
