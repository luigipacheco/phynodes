# GPL-3.0-or-later
# Timer-driven graph evaluation. Every ~50ms we evaluate each sink node in every
# PhyNodes tree, which pulls the rest of the graph lazily.

import time

import bpy
from bpy.app.handlers import persistent

from . import base
from . import fabnode
from .tree import TREE_ID

EVAL_INTERVAL = 0.05  # 50ms, matching mqttouch

# Evaluation is cheap; *repainting* is not. A continuously changing value (a
# streaming toolpath index, a sensor) marks the graph dirty on every tick, and
# an unthrottled redraw then repaints every 3D viewport at the full eval rate —
# on a heavy scene that is the dominant cost of running PhyNodes, and it scales
# with the viewport, not with the graph. Cap repaints well below the eval rate:
# data still updates at full speed, only the visual refresh is rate-limited.
REDRAW_MIN_INTERVAL = 0.1  # seconds (=10 Hz max repaint)
_last_redraw = 0.0


def _redraw(now=None):
    """Request a redraw of 3D viewports and node editors so changes written
    from this timer repaint without the user clicking in the viewport.
    Rate-limited to REDRAW_MIN_INTERVAL — see above."""
    global _last_redraw
    now = time.time() if now is None else now
    if now - _last_redraw < REDRAW_MIN_INTERVAL:
        return
    _last_redraw = now
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

    # FabNode presence (manifest + heartbeat) is independent of graph
    # evaluation — a paused graph should still show as an online node.
    try:
        fabnode.tick()
    except Exception as exc:
        print("[phynodes] fabnode tick error:", exc)

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
