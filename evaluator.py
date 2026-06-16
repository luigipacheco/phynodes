# GPL-3.0-or-later
# Timer-driven graph evaluation. Every ~50ms we evaluate each sink node in every
# MQTTouch tree, which pulls the rest of the graph lazily.

import bpy

from . import base
from .tree import TREE_ID

EVAL_INTERVAL = 0.05  # 50ms, matching mqttouch


def _tick():
    scene = bpy.context.scene
    settings = getattr(scene, "aq_mqttouch", None)
    if settings is not None and not settings.enabled:
        return EVAL_INTERVAL

    for tree in bpy.data.node_groups:
        if tree.bl_idname != TREE_ID:
            continue
        base.begin_tick()
        for node in tree.nodes:
            if getattr(node, "is_sink", False):
                try:
                    node.evaluate_sink()
                except Exception as exc:
                    print("[mqttouch] sink error in", node.name, ":", exc)
    return EVAL_INTERVAL


def register():
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=0.5)


def unregister():
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
