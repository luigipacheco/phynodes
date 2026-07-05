# GPL-3.0-or-later
# Connector registry: connector *types* (one class per transport) and *live*
# instances (one per connected entry in scene.phynodes.connectors).
#
# bpy-free on purpose: configs live in the scene (settings.py); this module
# only holds runtime objects, so it can be unit-tested outside Blender.

from .base import Connector, DISCONNECTED, CONNECTING, CONNECTED, ERROR
from .mqtt import MQTTConnector

# type_id -> class. New transports (OSC, Zenoh, Serial, ...) register here.
TYPES = {cls.type_id: cls for cls in (MQTTConnector,)}


def type_items():
    """(identifier, label, description) triples for the config EnumProperty."""
    return [(c.type_id, c.label, "%s connection" % c.label) for c in TYPES.values()]


# Live connector instances, keyed by the scene config entry's name.
_live = {}


def get(name):
    return _live.get(name)


def resolve(name, type_id):
    """The connector a node should use: the named one, or — with an empty
    name — the first live connector of the node's transport type."""
    if name:
        conn = _live.get(name)
        if conn is not None and conn.type_id == type_id:
            return conn
        return None
    for conn in _live.values():
        if conn.type_id == type_id:
            return conn
    return None


def start(name, type_id, config):
    """(Re)start the named connector from a plain config dict."""
    stop(name)
    cls = TYPES.get(type_id)
    if cls is None:
        return None
    conn = cls(name)
    conn.start(config)
    _live[name] = conn  # kept even on failure so the UI can show the error
    return conn


def stop(name):
    conn = _live.pop(name, None)
    if conn is not None:
        conn.stop()


def prune(valid_names):
    """Stop live connectors whose config entry no longer exists (deleted or
    renamed in the N-panel list)."""
    for name in [n for n in _live if n not in valid_names]:
        stop(name)


def stop_all():
    for name in list(_live):
        stop(name)
