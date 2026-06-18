# GPL-3.0-or-later
# Timer-driven graph evaluation. Every ~50ms we evaluate each sink node in every
# PhyNodes tree, which pulls the rest of the graph lazily.

import bpy
from bpy.app.handlers import persistent

from . import base
from .tree import TREE_ID

EVAL_INTERVAL = 0.05  # 50ms, matching mqttouch


def _redraw():
    """Request a redraw of 3D viewports and node editors so changes written
    from this timer repaint without the user clicking in the viewport."""
    wm = bpy.context.window_manager
    if not wm:
        return
    for window in wm.windows:
        screen = window.screen
        if not screen:
            continue
        for area in screen.areas:
            if area.type in {"VIEW_3D", "NODE_EDITOR"}:
                area.tag_redraw()


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

    if base.consume_dirty():
        _redraw()
    return interval


def _ensure_timer():
    """(Re)register the eval timer if it isn't running."""
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=0.2)


@persistent
def _on_load(*_args):
    # App timers don't survive opening a new .blend / reloading scripts, so
    # make sure the eval timer is alive again afterwards.
    _ensure_timer()


def register():
    _ensure_timer()
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)


def unregister():
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
