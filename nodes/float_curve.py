# GPL-3.0-or-later
# Float Curve node: remap a 0..1 factor through a hand-drawn curve using
# Blender's native curve widget.
#
# A CurveMapping can only exist inside an owner datablock -- it is not a
# registerable property type -- so each node keeps its own ShaderNodeFloatCurve
# inside a single hidden, fake-user helper node tree and references it by name.
# This is the same approach Sverchok / Animation Nodes use for curve widgets.

import uuid
import bpy
from bpy.props import StringProperty
from bpy.types import Node

from ..base import AQBaseNode, is_array, to_float_safe

_HOST_TREE = "__phynodes_curves__"


def _host_tree():
    ng = bpy.data.node_groups.get(_HOST_TREE)
    if ng is None:
        ng = bpy.data.node_groups.new(_HOST_TREE, "ShaderNodeTree")
        # Fake user so the tree (and every node's curve) survives save/reload
        # even though nothing in the scene "uses" it.
        ng.use_fake_user = True
    return ng


def _make_host():
    host = _host_tree().nodes.new("ShaderNodeFloatCurve")
    host.name = "curve_" + uuid.uuid4().hex[:8]
    return host.name


def _copy_mapping(src, dst):
    """Mirror src's curve points onto dst (used when a node is duplicated)."""
    sc, dc = src.curves[0], dst.curves[0]
    while len(dc.points) > len(sc.points):
        dc.points.remove(dc.points[-1])
    while len(dc.points) < len(sc.points):
        dc.points.new(0.5, 0.5)
    for i, sp in enumerate(sc.points):
        dc.points[i].location = sp.location
        dc.points[i].handle_type = sp.handle_type
    dst.update()


class AQFloatCurveNode(AQBaseNode, Node):
    bl_idname = "PhyNodesFloatCurveNode"
    bl_label = "Float Curve"
    bl_icon = "FCURVE"

    # Name of this node's ShaderNodeFloatCurve inside the hidden host tree.
    host_node: StringProperty()

    def _host(self, create=True):
        ng = bpy.data.node_groups.get(_HOST_TREE)
        host = ng.nodes.get(self.host_node) if (ng and self.host_node) else None
        if host is None and create:
            self.host_node = _make_host()
            host = _host_tree().nodes.get(self.host_node)
        return host

    def init(self, context):
        self.host_node = _make_host()
        self.new_input("Fac", "FLOAT", default=0.0, min=0.0, max=1.0)
        self.new_input("To Min", "FLOAT", default=0.0)
        self.new_input("To Max", "FLOAT", default=1.0)
        self.new_output("Result", "FLOAT")

    def copy(self, node):
        # Duplicated node: drop the inherited reference and clone the curve so
        # the two nodes don't share one mapping.
        self.host_node = ""
        new_host = self._host(create=True)
        src = node._host(create=False)
        if src and new_host:
            _copy_mapping(src.mapping, new_host.mapping)

    def free(self):
        ng = bpy.data.node_groups.get(_HOST_TREE)
        host = ng.nodes.get(self.host_node) if (ng and self.host_node) else None
        if host:
            ng.nodes.remove(host)

    def draw_buttons(self, context, layout):
        host = self._host()
        if host is not None:
            layout.template_curve_mapping(host, "mapping", type="NONE")
        else:
            layout.label(text="curve unavailable", icon="ERROR")

    def _eval_one(self, x, lo, hi, cm, curve):
        t = max(0.0, min(1.0, to_float_safe(x)))
        y = cm.evaluate(curve, t)
        return lo + (hi - lo) * y

    def compute_output(self, socket):
        host = self._host()
        if host is None:
            return 0.0
        cm = host.mapping
        cm.update()  # required before evaluate(); cheap for a single curve
        curve = cm.curves[0]
        lo = to_float_safe(self.get_input("To Min", 0.0))
        hi = to_float_safe(self.get_input("To Max", 1.0))
        fac = self.get_input("Fac", 0.0)
        if is_array(fac):
            return [self._eval_one(x, lo, hi, cm, curve) for x in fac]
        return self._eval_one(fac, lo, hi, cm, curve)


classes = (AQFloatCurveNode,)
