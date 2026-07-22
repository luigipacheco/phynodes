# GPL-3.0-or-later
# MQTT connector: one threaded paho-mqtt client per configured connection.
#
# The worker thread owns the paho client: it connects, pumps the network loop,
# and reconnects with exponential backoff when the broker drops. Subscriptions
# are per-topic (nodes register interest via ensure_subscribed) instead of a
# prefix-wide '#' wildcard, so the inbox only holds topics the graph uses.

import threading
import time

try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:  # allow the addon to load and warn in the UI
    mqtt = None

from .base import Connector, DISCONNECTED, CONNECTING, CONNECTED, ERROR

RECONNECT_MAX_WAIT = 30.0  # seconds; backoff doubles from 1s up to this
HEARTBEAT_INTERVAL = 15.0  # FabNodes diag/uptime cadence (FabFlow stales at 45s)


class MQTTConnector(Connector):
    type_id = "MQTT"
    label = "MQTT"
    requires = "paho-mqtt"
    DEFAULT_PORT = 1883

    def __init__(self, name=""):
        super().__init__(name)
        self._client = None
        self._thread = None
        self._host = ""
        self._port = self.DEFAULT_PORT
        self._prefix = ""
        self._username = ""
        self._password = ""
        # Full topics nodes declared interest in; (re)subscribed on every
        # (re)connect. Guarded: added on the main thread, iterated on the
        # worker thread in _on_connect.
        self._subs = set()
        self._subs_lock = threading.Lock()
        # FabNodes identity (fabnode.py drives the manifest/heartbeat pacing;
        # this class owns the transport-level protocol: LWT, $state, estop).
        self.fab_enabled = False
        self.fab_name = ""
        self.fab_type = "fab-blender"
        self.estop_active = False
        self._fab_started_at = 0.0
        self._fab_last_manifest_hash = None
        self._fab_last_manifest_at = 0.0
        self._fab_last_heartbeat = 0.0

    # -- availability / config --------------------------------------------
    @classmethod
    def available(cls):
        return mqtt is not None

    @classmethod
    def config_from_item(cls, item):
        return {
            "host": item.host,
            "port": item.port,
            "prefix": item.topic_prefix,
            "username": item.username,
            "password": item.password,
            "fab_enabled": bool(getattr(item, "fabnode_enabled", False)),
            "fab_name": (getattr(item, "fabnode_name", "") or "").strip(),
            "fab_type": (getattr(item, "fabnode_type", "") or "").strip() or "fab-blender",
            "fab_verify": bool(getattr(item, "fabnode_verify", False)),
        }

    @classmethod
    def apply_defaults(cls, item):
        item.host = "test.mosquitto.org"
        item.port = 1883
        item.topic_prefix = "/phynodes/"
        item.username = ""
        item.password = ""

    @classmethod
    def draw_config(cls, layout, item):
        col = layout.column(align=True)
        col.prop(item, "host")
        col.prop(item, "port")
        col.prop(item, "topic_prefix")
        col.prop(item, "username")
        col.prop(item, "password")

        layout.separator()
        box = layout.box()
        box.prop(item, "fabnode_enabled")
        if item.fabnode_enabled:
            box.prop(item, "fabnode_name")
            box.prop(item, "fabnode_type")
            box.prop(item, "fabnode_verify")
            box.operator("phynodes.fabnode_republish", icon="FILE_REFRESH")

    @staticmethod
    def _normalize_prefix(prefix):
        if not prefix:
            return ""
        if not prefix.endswith("/"):
            prefix += "/"
        return prefix

    # -- lifecycle ----------------------------------------------------------
    @property
    def connected(self):
        client = self._client
        if client is None:
            return False
        try:
            return client.is_connected()
        except Exception:
            return False

    @property
    def status(self):
        if self.connected:
            return CONNECTED
        thread = self._thread
        if thread is not None and thread.is_alive():
            return CONNECTING
        return ERROR if self.last_error else DISCONNECTED

    def start(self, config):
        if mqtt is None:
            self.last_error = "paho-mqtt is not installed in Blender's Python"
            return False
        self.stop()
        self._host = config["host"]
        self._port = int(config.get("port", self.DEFAULT_PORT))
        self._prefix = self._normalize_prefix(config.get("prefix", ""))
        self._username = config.get("username", "") or ""
        self._password = config.get("password", "") or ""
        self.fab_name = (config.get("fab_name", "") or "").strip()
        self.fab_type = (config.get("fab_type", "") or "fab-blender").strip() or "fab-blender"
        # A FabNode with no name has no topic namespace — treat as disabled.
        self.fab_enabled = bool(config.get("fab_enabled", False)) and bool(self.fab_name)
        self.fab_verify = bool(config.get("fab_verify", False))
        self.estop_active = False
        self._fab_started_at = time.time()
        self._fab_last_manifest_hash = None
        self._fab_last_manifest_at = 0.0
        self._fab_last_heartbeat = 0.0
        self.last_error = ""
        gen = self._next_generation()
        self._thread = threading.Thread(
            target=self._run, args=(gen,), daemon=True,
            name="phynodes-mqtt-" + (self.name or "unnamed"),
        )
        self._thread.start()
        return True

    def stop(self):
        # Graceful offline: the LWT only fires on an *ungraceful* drop, so on a
        # deliberate disconnect publish offline ourselves (retained, so FabFlow
        # keeps the node listed but greyed).
        if self.fab_enabled and self.fab_name and self.connected:
            client = self._client
            if client is not None:
                try:
                    client.publish(self.fab_name + "/$state", "offline", qos=1, retain=True)
                except Exception:
                    pass
        self._next_generation()  # workers see the change and bail out
        thread = self._thread
        if thread is not None:
            # A thread stuck in a slow connect() can outlive this join; the
            # generation check makes it exit on its own without touching state.
            thread.join(timeout=1.0)
            self._thread = None
        self._client = None

    # -- worker thread -------------------------------------------------------
    def _make_client(self):
        # paho-mqtt 2.x requires an explicit callback API version; 1.x has no
        # such argument. Use the v1 callback signatures on both.
        try:
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        except (AttributeError, TypeError):
            return mqtt.Client()

    def _run(self, gen):
        backoff = 1.0
        while self._current(gen):
            client = None
            try:
                client = self._make_client()
                client.user_data_set(self)
                if self._username:
                    client.username_pw_set(self._username, self._password or None)
                client.on_connect = MQTTConnector._on_connect
                client.on_message = MQTTConnector._on_message
                if self.fab_enabled and self.fab_name:
                    # Last Will: broker publishes this if we drop ungracefully.
                    try:
                        client.will_set(self.fab_name + "/$state", "offline",
                                        qos=1, retain=True)
                    except Exception:
                        pass
                client.connect(self._host, self._port, 60)
                if not self._current(gen):  # stopped while connecting
                    try:
                        client.disconnect()
                    except Exception:
                        pass
                    return
                self._client = client
                self.last_error = ""
                backoff = 1.0
                while self._current(gen):
                    rc = client.loop(timeout=0.2)
                    if rc != 0 and not client.is_connected():
                        self.last_error = "connection lost - reconnecting"
                        break
                    # FabNodes heartbeat from the worker thread — Blender's
                    # main-thread timers stall during renders / heavy scenes,
                    # and FabFlow greys nodes after 45 s without diag/uptime.
                    # The worker keeps beating as long as the socket is alive.
                    if self.fab_enabled and self.fab_name:
                        now = time.time()
                        if now - self._fab_last_heartbeat >= HEARTBEAT_INTERVAL:
                            self._fab_last_heartbeat = now
                            self.publish_heartbeat()
            except Exception as exc:
                if self._current(gen):
                    self.last_error = str(exc)
                    print("[phynodes] mqtt '%s': %s" % (self.name, exc))
            if self._current(gen):
                self._client = None
            if client is not None:
                try:
                    client.disconnect()
                except Exception:
                    pass
            # Reconnect after a growing wait, leaving promptly on stop().
            waited = 0.0
            while self._current(gen) and waited < backoff:
                time.sleep(0.1)
                waited += 0.1
            backoff = min(backoff * 2.0, RECONNECT_MAX_WAIT)

    @staticmethod
    def _on_connect(client, userdata, flags, rc):
        conn = userdata
        with conn._subs_lock:
            topics = list(conn._subs)
        for topic in topics:
            try:
                client.subscribe(topic)
            except Exception:
                pass
        if conn.fab_enabled and conn.fab_name:
            # Announce liveness + join the safety bus. The manifest itself is
            # published from the main thread (fabnode.tick) because it must
            # walk the node graph; force a republish by clearing the hash.
            try:
                client.publish(conn.fab_name + "/$state", "online", qos=1, retain=True)
                client.subscribe("system/estop", qos=1)
                client.publish(conn.fab_name + "/status/safe",
                               "1" if conn.estop_active else "0", retain=True)
            except Exception:
                pass
            conn._fab_last_manifest_hash = None
            conn._fab_last_manifest_at = 0.0
            conn._fab_last_heartbeat = 0.0
        print("[phynodes] mqtt '%s': connected to %s (%d topics)"
              % (conn.name, conn._host, len(topics)))

    @staticmethod
    def _on_message(client, userdata, msg):
        conn = userdata
        try:
            topic = str(msg.topic)
            payload = msg.payload.decode("utf-8", "replace")
            conn._inbox[topic] = payload
            if topic == "system/estop":
                conn._handle_estop(payload)
        except Exception:
            pass

    def _handle_estop(self, payload):
        """Latch/clear the FabNodes e-stop and acknowledge via status/safe.

        While latched, fabnode PUB nodes suppress control output (fail-safe),
        mirroring the firmware rule."""
        text = (payload or "").strip().lower()
        active = text in ("1", "true", "on")
        if not active and text not in ("", "0", "false", "off"):
            try:
                active = float(text) >= 0.5
            except ValueError:
                active = False
        if active == self.estop_active:
            return
        self.estop_active = active
        print("[phynodes] mqtt '%s': ESTOP %s"
              % (self.name, "LATCHED" if active else "cleared"))
        client = self._client
        if client is not None and self.fab_name:
            try:
                client.publish(self.fab_name + "/status/safe",
                               "1" if active else "0", retain=True)
            except Exception:
                pass

    # -- node-facing I/O ----------------------------------------------------
    def ensure_subscribed(self, address):
        full = self._prefix + address
        with self._subs_lock:
            if full in self._subs:
                return
            self._subs.add(full)
        # Subscribe live when already connected; _on_connect re-subscribes the
        # whole set on every (re)connect, which covers the races around it.
        client = self._client
        if client is not None:
            try:
                client.subscribe(full)
            except Exception:
                pass

    def read(self, address):
        return self._inbox.get(self._prefix + address)

    def write(self, address, payload, qos=0, retain=False):
        client = self._client
        if client is None or not self.connected:
            return False
        try:
            client.publish(self._prefix + address, payload, qos=qos, retain=retain)
            return True
        except Exception as exc:
            print("[phynodes] mqtt '%s' publish error: %s" % (self.name, exc))
            return False

    def full_topic(self, address):
        """The actual topic a node publishes/subscribes to (prefix applied).
        Used by the manifest builder so advertised signal topics are truthful."""
        return self._prefix + address

    # -- FabNodes: absolute-topic publishes (not under the phynodes prefix) ---
    # These carry the protocol topics (fabnodes/manifest/<n>, <n>/$info,
    # <n>/diag/*). paho publish is thread-safe, but these are driven from the
    # main thread by fabnode.tick().
    def publish_manifest(self, payload):
        client = self._client
        if client is None or not self.connected or not self.fab_name:
            return False
        try:
            client.publish("fabnodes/manifest/" + self.fab_name, payload, retain=True)
            client.publish(self.fab_name + "/$info", payload, retain=True)
            return True
        except Exception as exc:
            print("[phynodes] mqtt '%s' manifest error: %s" % (self.name, exc))
            return False

    def publish_heartbeat(self):
        client = self._client
        if client is None or not self.connected or not self.fab_name:
            return
        uptime = int(max(0.0, time.time() - self._fab_started_at))
        try:
            client.publish(self.fab_name + "/diag/uptime", str(uptime))
        except Exception:
            pass

    def clear_retained_fabnode(self):
        """Erase this node's retained manifest/$state/$info so a removed
        connection doesn't linger as a ghost node in FabFlow (empty retained
        payload deletes the retained message)."""
        client = self._client
        if client is None or not self.connected or not self.fab_name:
            return
        for topic in ("fabnodes/manifest/" + self.fab_name,
                      self.fab_name + "/$info",
                      self.fab_name + "/$state"):
            try:
                client.publish(topic, "", retain=True)
            except Exception:
                pass
