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
        # Full topics nodes declared interest in; (re)subscribed on every
        # (re)connect. Guarded: added on the main thread, iterated on the
        # worker thread in _on_connect.
        self._subs = set()
        self._subs_lock = threading.Lock()

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
        }

    @classmethod
    def apply_defaults(cls, item):
        item.host = "test.mosquitto.org"
        item.port = 1883
        item.topic_prefix = "/phynodes/"

    @classmethod
    def draw_config(cls, layout, item):
        col = layout.column(align=True)
        col.prop(item, "host")
        col.prop(item, "port")
        col.prop(item, "topic_prefix")

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
        self.last_error = ""
        gen = self._next_generation()
        self._thread = threading.Thread(
            target=self._run, args=(gen,), daemon=True,
            name="phynodes-mqtt-" + (self.name or "unnamed"),
        )
        self._thread.start()
        return True

    def stop(self):
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
                client.on_connect = MQTTConnector._on_connect
                client.on_message = MQTTConnector._on_message
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
        print("[phynodes] mqtt '%s': connected to %s (%d topics)"
              % (conn.name, conn._host, len(topics)))

    @staticmethod
    def _on_message(client, userdata, msg):
        conn = userdata
        try:
            conn._inbox[str(msg.topic)] = msg.payload.decode("utf-8", "replace")
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
