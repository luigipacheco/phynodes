# GPL-3.0-or-later
# Animaquina Index node (source): the current waypoint index of the toolpath
# running on an Animaquina robot slot.
#
# This is the cursor the whole per-point streaming model turns on. Animaquina
# publishes one canonical index per robot slot (sim playback, live streaming
# and polled exported programs all normalize into it); wire that index into any
# number of Geometry Attribute nodes and each one reads its own attribute at
# the same point. Streaming N per-point attributes costs N attribute nodes and
# one shared index wire — no per-attribute setup on the Animaquina side.
#
#     [Animaquina Index] ──┬──► [Geometry Attribute "PAR"]   ──► [MQTT PUB]
#                          ├──► [Geometry Attribute "led"]   ──► [MQTT PUB]
#                          └──► [Geometry Attribute "fan"]   ──► [MQTT PUB]
#
# Reads the documented contract (no import of Animaquina — it may not be
# installed, and the add-on stays optional):
#     bpy.context.scene.animaquina.robots[<slot>].run_idx / run_count /
#     run_source / run_object
#
# Outputs:
#   Index    - current waypoint (-1 while idle, so downstream can tell)
#   Running  - True while a toolpath is actually running (gate publishes with
#              this: at idle Index is -1 and attribute nodes clamp to point 0,
#              which would otherwise publish point 0's values forever)
#   Count    - total waypoints in the run
#   Progress - 0..1 along the run (0 when idle or unknown)

import bpy
from bpy.props import IntProperty
from bpy.types import Node

from ..base import AQBaseNode


def _slots(context=None):
    """The Animaquina robot slots, or None when the add-on isn't present."""
    scene = (context or bpy.context).scene
    props = getattr(scene, "animaquina", None)
    if props is None:
        return None
    return getattr(props, "robots", None)


def _slot(index, context=None):
    slots = _slots(context)
    if not slots:
        return None
    if 0 <= index < len(slots):
        return slots[index]
    return None


class AQAnimaquinaIndexNode(AQBaseNode, Node):
    bl_idname = "PhyNodesAnimaquinaIndexNode"
    bl_label = "Animaquina Index"
    bl_icon = "TRACKING"

    robot_slot: IntProperty(
        name="Robot",
        description="Animaquina robot slot to read the run index from "
                    "(0 = first robot in the Animaquina panel)",
        default=0,
        min=0,
    )

    def init(self, context):
        self.new_output("Index", "INT")
        self.new_output("Running", "BOOL")
        self.new_output("Count", "INT")
        self.new_output("Progress", "FLOAT")

    def draw_buttons(self, context, layout):
        slots = _slots(context)
        if slots is None:
            layout.label(text="Animaquina not found", icon="ERROR")
            return
        layout.prop(self, "robot_slot", text="Robot")
        slot = _slot(self.robot_slot, context)
        if slot is None:
            layout.label(text="(no robot in slot %d)" % self.robot_slot, icon="UNLINKED")
            return
        layout.label(text=getattr(slot, "label", "") or "Robot", icon="ARMATURE_DATA")
        source = getattr(slot, "run_source", "NONE")
        if source == "NONE":
            layout.label(text="idle", icon="DOT")
            return
        idx = int(getattr(slot, "run_idx", -1))
        count = int(getattr(slot, "run_count", 0))
        text = "%s  %d" % (source.title(), idx)
        if count > 0:
            text += " / %d" % (count - 1)
        layout.label(text=text, icon="PLAY")
        obj = getattr(slot, "run_object", None)
        if obj is not None:
            layout.label(text=obj.name, icon="MESH_DATA")

    def compute_output(self, socket):
        slot = _slot(self.robot_slot)
        if slot is None:
            # No Animaquina / empty slot: idle values, never an exception.
            return 0.0 if socket.name in {"Progress"} else (
                -1 if socket.name == "Index" else 0)

        name = socket.name
        if name == "Index":
            return int(getattr(slot, "run_idx", -1))
        if name == "Running":
            return getattr(slot, "run_source", "NONE") != "NONE"
        if name == "Count":
            return int(getattr(slot, "run_count", 0))
        if name == "Progress":
            idx = int(getattr(slot, "run_idx", -1))
            count = int(getattr(slot, "run_count", 0))
            if idx < 0 or count < 2:
                return 0.0
            return min(1.0, max(0.0, idx / float(count - 1)))
        return 0.0


classes = (AQAnimaquinaIndexNode,)
