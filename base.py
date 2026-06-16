# GPL-3.0-or-later
# Node base class + pull-based evaluation framework, plus value/type utilities
# ported from mqttouch's BaseGraphNode.

import json
from .tree import TREE_ID

# Per-tick memoization so a value pulled by several downstream nodes is computed
# once. Keyed by (node pointer, output socket identifier).
_eval_cache = {}
# Recursion guard against cyclic graphs.
_eval_visiting = set()


def begin_tick():
    _eval_cache.clear()
    _eval_visiting.clear()


# ---------------------------------------------------------------------------
# Value / type utilities (port of BaseGraphNode static helpers)
# ---------------------------------------------------------------------------

def is_array(value):
    return isinstance(value, (list, tuple))


def to_float_safe(value, default=0.0):
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    if is_array(value) and value:
        return to_float_safe(value[0], default)
    return default


def to_bool_safe(value):
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return 1.0 if float(value) >= 0.5 else 0.0
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "1", "on", "yes"):
            return 1.0
        return 0.0
    return 0.0


def flatten_array(arr):
    out = []
    for item in arr:
        if is_array(item):
            out.extend(flatten_array(item))
        else:
            out.append(item)
    return out


def parse_payload(message):
    """Parse a raw MQTT payload into a scalar / string / (nested) array.

    Mirrors mqttouch's MQTT SUB parsing: JSON first, then CSV, then number,
    then plain string.
    """
    if message is None:
        return 0.0
    message = message.strip()
    # JSON (preserves nested arrays like [[r,g,b],...])
    try:
        data = json.loads(message)
        if isinstance(data, (list, dict, int, float)):
            return data
    except (ValueError, TypeError):
        pass
    # CSV / semicolon-grouped
    arr = _parse_csv(message)
    if arr is not None:
        return arr
    # scalar number
    try:
        return float(message)
    except ValueError:
        return message


def _parse_csv(message):
    if "," not in message and ";" not in message:
        return None
    result = []
    if ";" in message:
        for group in (g for g in message.split(";") if g.strip()):
            if "," in group:
                result.append([_num(v) for v in group.split(",") if v.strip()])
            else:
                result.append(_num(group))
    else:
        result = [_num(v) for v in message.split(",") if v.strip()]
    return result if len(result) >= 2 else None


def _num(token):
    token = token.strip()
    try:
        return float(token)
    except ValueError:
        return token


def format_for_mqtt(value):
    """Format a value as an MQTT payload string (arrays -> JSON)."""
    if is_array(value):
        return json.dumps(list(value))
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


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
    """Mixin for all MQTT Nodes nodes. Subclass alongside bpy.types.Node."""

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
        sock = self.inputs.new("MQTTNodesSocketType", name)
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
        sock = self.outputs.new("MQTTNodesSocketType", name)
        sock.data_type = data_type
        return sock

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
            print("[mqttouch] eval error in", self.name, ":", exc)
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
