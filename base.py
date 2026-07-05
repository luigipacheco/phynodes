# GPL-3.0-or-later
# Node base class + pull-based evaluation framework.

from .tree import TREE_ID

# Value/type utilities live in the bpy-free values.py (so they can be
# unit-tested outside Blender); re-exported here because node modules import
# them from ..base.
from .values import (  # noqa: F401
    is_array, to_float_safe, to_bool_safe, flatten_array, parse_payload,
    format_for_mqtt,
)

# Per-tick memoization so a value pulled by several downstream nodes is computed
# once. Keyed by (node pointer, output socket identifier).
_eval_cache = {}
# Recursion guard against cyclic graphs.
_eval_visiting = set()
# Set by sinks when they actually write something, so the evaluator knows it
# must request a viewport/node-editor redraw (otherwise changes from a timer
# don't repaint until the user interacts).
_dirty = False


def begin_tick():
    _eval_cache.clear()
    _eval_visiting.clear()


def mark_dirty():
    """Call from a sink when it writes a changed value."""
    global _dirty
    _dirty = True


def consume_dirty():
    """Return True if anything changed since the last call, and reset."""
    global _dirty
    was = _dirty
    _dirty = False
    return was


# ---------------------------------------------------------------------------
# Socket helpers
# ---------------------------------------------------------------------------

def _set_socket_default(sock, data_type, default):
    if data_type == "FLOAT":
        sock.value_float = float(default)
    elif data_type == "INT":
        sock.value_int = int(default)
    elif data_type == "BOOL":
        sock.value_bool = bool(default)
    elif data_type == "STRING":
        sock.value_string = str(default)
    elif data_type == "VECTOR":
        sock.value_vector = tuple(default)[:3]
    elif data_type == "COLOR":
        sock.value_color = tuple(default)[:4]


# ---------------------------------------------------------------------------
# Node base class
# ---------------------------------------------------------------------------

class AQBaseNode:
    """Mixin for all PhyNodes nodes. Subclass alongside bpy.types.Node."""

    # Sink nodes (PUB, Property Out, Debug) are evaluated by the timer each tick
    # and pull the graph upstream. Override to True and implement evaluate_sink.
    is_sink = False

    bl_width_default = 180

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == TREE_ID

    # -- wiring helpers ---------------------------------------------------
    def new_input(self, name, data_type="FLOAT", default=None, min=None, max=None):
        """Add an input socket with an optional preset default and min/max.

        Like geometry-node sockets: `data_type` picks the default widget +
        color, `default` seeds it, and min/max clamp the value when unlinked.
        """
        sock = self.inputs.new("PhyNodesSocketType", name)
        sock.data_type = data_type
        if default is not None:
            _set_socket_default(sock, data_type, default)
        if min is not None or max is not None:
            sock.use_clamp = True
            if min is not None:
                sock.min_value = min
            if max is not None:
                sock.max_value = max
        return sock

    def new_output(self, name, data_type="ANY"):
        sock = self.outputs.new("PhyNodesSocketType", name)
        sock.data_type = data_type
        return sock

    # -- sidebar (N-panel) ------------------------------------------------
    def draw_buttons_ext(self, context, layout):
        """N-panel view: node params plus per-socket type / default / min-max,
        like geometry nodes expose socket settings in the sidebar."""
        self.draw_buttons(context, layout)

        if len(self.inputs):
            layout.separator()
            layout.label(text="Inputs", icon="NODE_SEL")
            for sock in self.inputs:
                box = layout.box()
                box.label(text=sock.name or "Input")
                box.prop(sock, "data_type", text="Type")
                if sock.data_type != "ANY":
                    sock.draw_default(box, "Default")
                if sock.data_type in {"FLOAT", "INT"}:
                    box.prop(sock, "use_clamp", text="Clamp Min / Max")
                    if sock.use_clamp:
                        row = box.row(align=True)
                        row.prop(sock, "min_value")
                        row.prop(sock, "max_value")

        if len(self.outputs):
            layout.separator()
            layout.label(text="Outputs", icon="NODE_SEL")
            for sock in self.outputs:
                row = layout.row(align=True)
                row.label(text=sock.name or "Output")
                row.prop(sock, "data_type", text="")

    def get_input(self, name, default=None):
        """Resolve an input socket's value: linked source, else its default."""
        sock = self.inputs.get(name)
        if sock is None:
            return default
        if sock.is_linked and sock.links:
            link = sock.links[0]
            from_node = link.from_node
            if isinstance(from_node, AQBaseNode):
                return from_node.eval_output(link.from_socket)
            return default
        return sock.get_value()

    # -- evaluation -------------------------------------------------------
    def eval_output(self, socket):
        key = (self.as_pointer(), socket.identifier)
        if key in _eval_cache:
            return _eval_cache[key]
        if key in _eval_visiting:  # cycle: break with neutral value
            return 0.0
        _eval_visiting.add(key)
        try:
            value = self.compute_output(socket)
        except Exception as exc:
            print("[phynodes] eval error in", self.name, ":", exc)
            value = 0.0
        finally:
            _eval_visiting.discard(key)
        _eval_cache[key] = value
        return value

    def compute_output(self, socket):
        """Return this node's value for the given output socket."""
        return 0.0

    def evaluate_sink(self):
        """Sink nodes: pull inputs and push to MQTT / Blender each tick."""
        pass
