# GPL-3.0-or-later
# Animaquina PhyNodes — a visual MQTT node graph for Blender.
#
# Ports the mqttouch (Godot) node editor into a native Blender NodeTree: wire
# Value / Math / Map / MQTT / Property nodes together and a timer evaluates the
# graph every ~50ms. Designed to live standalone now and fold into Animaquina
# as a sub-module later.

bl_info = {
    "name": "PhyNodes",
    "author": "Luis Arturo Pacheco",
    "description": "Connect Blender to physical inputs and outputs through MQTT and OSC, using a node graph.",
    "blender": (4, 2, 0),
    "version": (0, 4, 0),
    "location": "Node Editor > PhyNodes",
    "warning": "Beta — requires paho-mqtt in Blender's Python.",
    "doc_url": "https://www.animaquina.com",
    "category": "Node",
}

import bpy

from . import settings, tree, base, evaluator, ui, connectors
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
    connectors.stop_all()


if __name__ == "__main__":
    register()
