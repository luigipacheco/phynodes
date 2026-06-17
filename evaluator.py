# GPL-3.0-or-later
# Timer-driven graph evaluation. Every ~50ms we evaluate each sink node in every
# PhyNodes tree, which pulls the rest of the graph lazily.

import bpy

from . import base
from .tree import TREE_ID

EVAL_INTERVAL = 0.05  # 50ms, matching mqttouch


def _tick():
    scene = bpy.context.scene
    settings = getattr(scene, "phynodes", None)
    interval = settings.eval_interval if settings is not None else EVAL_INTERVAL

    if settings is not None and not settings.enabled:
        return interval

    for tree in bpy.data.node_groups:
        if tree.bl_idname != TREE_ID:
            continue
        base.begin_tick()
        for node in tree.nodes:
            if getattr(node, "is_sink", False):
                try:
                    node.evaluate_sink()
                except Exception as exc:
                    print("[phynodes] sink error in", node.name, ":", exc)
    return interval


def register():
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=0.5)


def unregister():
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
