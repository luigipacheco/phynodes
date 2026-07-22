# GPL-3.0-or-later
# FabNodes manifest layer — makes a fabnode-enabled MQTT connection announce
# itself under fabnodes/1.1 so FabFlow discovers Blender like any ESP32.
#
# Split of responsibilities:
#   connectors/mqtt.py  — transport protocol: LWT, $state online/offline,
#                         system/estop latch, the retained publishes.
#   fabnode.py (here)   — the parts that must touch bpy on the main thread:
#                         walk the PhyNodes graphs to derive the signal list,
#                         and pace manifest re-publishes + the diag heartbeat
#                         from the evaluator tick.
#
# FabFlow discovery hinges on one retained topic — fabnodes/manifest/<name> —
# plus <name>/$state for liveness and <name>/diag/uptime for the heartbeat it
# uses to grey out stale nodes (see ix-nodes hub/flow/src/lib/bus.svelte.js).

import hashlib
import json
import time

import bpy

from . import connectors
from .tree import TREE_ID

PROTOCOL = "fabnodes/1.1"
FW = "phynodes-0.4.0"

MANIFEST_MIN_INTERVAL = 1.0   # s between graph walks / hash checks (cheap)
HEARTBEAT_INTERVAL = 15.0     # s between diag/uptime publishes (FabFlow cadence)

# PhyNodes socket data_type -> fabnodes signal type. Vectors/colors travel as
# JSON arrays ([r,g,b,a]), matching the fabnodes array payload format.
_TYPE_MAP = {
    "FLOAT": "float",
    "INT": "int",
    "BOOL": "bool",
    "STRING": "string",
    "VECTOR": "array",
    "COLOR": "array",
}

_PUB_ID = "PhyNodesMqttPubNode"
_SUB_ID = "PhyNodesMqttSubNode"


def _signal_type_for_pub(node):
    """A PUB node's dtype = the type feeding its Value input, if linked."""
    sock = node.inputs.get("Value")
    if sock is not None and sock.is_linked and sock.links:
        return _TYPE_MAP.get(getattr(sock.links[0].from_socket, "data_type", ""), "string")
    return "string"


def _signal_type_for_sub(node):
    """A SUB node's dtype = the type it feeds downstream, if linked."""
    sock = node.outputs.get("Value")
    if sock is not None and sock.is_linked and sock.links:
        return _TYPE_MAP.get(getattr(sock.links[0].to_socket, "data_type", ""), "string")
    return "string"


def _collect_signals(conn):
    """Walk every PhyNodes graph and derive the signal descriptors for the
    PUB/SUB nodes routed through this connector. Advertised topics are the
    *actual* full topics (prefix applied) so the manifest is truthful."""
    signals = []
    for tree in bpy.data.node_groups:
        if tree.bl_idname != TREE_ID:
            continue
        for node in tree.nodes:
            bl = node.bl_idname
            if bl == _PUB_ID:
                direction = "pub"
            elif bl == _SUB_ID:
                direction = "sub"
            else:
                continue
            try:
                # get_connector() resolves the same way runtime routing does
                # (named entry, or the first live MQTT connector for an empty
                # name), so the manifest reflects what actually flows here.
                if node.get_connector() is not conn:
                    continue
            except Exception:
                continue
            topic = conn.full_topic(getattr(node, "topic", "") or "")
            stype = (_signal_type_for_pub(node) if direction == "pub"
                     else _signal_type_for_sub(node))
            signals.append({"topic": topic, "dir": direction, "type": stype})
    return signals


def _standard_signals(name):
    """The standard v1.1 descriptors this node actually publishes. rssi is
    omitted deliberately — meaningless for a PC-hosted node."""
    return [
        {"topic": name + "/status/safe", "dir": "pub", "type": "bool"},
        {"topic": name + "/diag/uptime", "dir": "pub", "type": "int", "unit": "s"},
    ]


def build_manifest(conn):
    name = conn.fab_name
    signals = _collect_signals(conn) + _standard_signals(name)
    payload = {
        "nodeName": name,
        "nodeType": conn.fab_type,
        "fw": FW,
        "protocol": PROTOCOL,
        "state": name + "/$state",
        "signals": signals,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def tick(now=None):
    """Called from the evaluator timer (main thread). Publishes the manifest
    when the graph topology changes and drives the diag heartbeat."""
    now = time.time() if now is None else now
    for conn in connectors.all_live():
        if not getattr(conn, "fab_enabled", False) or not getattr(conn, "fab_name", ""):
            continue
        if conn.status != connectors.CONNECTED:
            continue

        if now - conn._fab_last_manifest_at >= MANIFEST_MIN_INTERVAL:
            conn._fab_last_manifest_at = now
            try:
                payload = build_manifest(conn)
            except Exception as exc:
                print("[phynodes] fabnode manifest build error:", exc)
                payload = None
            if payload is not None:
                digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
                if digest != conn._fab_last_manifest_hash:
                    if conn.publish_manifest(payload):
                        conn._fab_last_manifest_hash = digest

        if now - conn._fab_last_heartbeat >= HEARTBEAT_INTERVAL:
            conn._fab_last_heartbeat = now
            conn.publish_heartbeat()
