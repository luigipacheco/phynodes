# GPL-3.0-or-later
# Time sources.
#
# Scene Time  - mirrors Blender's Scene Time node: Frame + Seconds from the
#               timeline (advances on play / scrub).
# Timer       - wall-clock elapsed seconds with a Reset, advancing continuously
#               via the graph tick even when the animation isn't playing
#               (the real analog of mqttouch's counter/Timer node).

import time
import bpy
from bpy.types import Node

from ..base import AQBaseNode


class AQSceneTimeNode(AQBaseNode, Node):
    bl_idname = "PhyNodesSceneTimeNode"
    bl_label = "Scene Time"
    bl_icon = "TIME"

    def init(self, context):
        self.new_output("Seconds", "FLOAT")
        self.new_output("Frame", "FLOAT")

    def compute_output(self, socket):
        scene = bpy.context.scene
        if scene is None:
            return 0.0
        frame = scene.frame_current + scene.frame_subframe
        if socket.name == "Frame":
            return float(frame)
        r = scene.render
        fps = (r.fps / r.fps_base) if r.fps_base else r.fps
        return (frame / fps) if fps else 0.0


class AQTimerNode(AQBaseNode, Node):
    bl_idname = "PhyNodesTimerNode"
    bl_label = "Timer"
    bl_icon = "TIME"

    def init(self, context):
        self["start"] = time.time()
        self.new_output("Seconds", "FLOAT")

    def _elapsed(self):
        start = self.get("start")
        if start is None:
            return 0.0
        return max(0.0, time.time() - start)

    def draw_buttons(self, context, layout):
        op = layout.operator("phynodes.reset_timer", text="Reset", icon="FILE_REFRESH")
        op.tree_name = self.id_data.name
        op.node_name = self.name
        layout.label(text="%.2f s" % self._elapsed())

    def compute_output(self, socket):
        return self._elapsed()


classes = (AQSceneTimeNode, AQTimerNode)
