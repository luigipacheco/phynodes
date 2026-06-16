# GPL-3.0-or-later
# Shared MQTT connection manager.
#
# One threaded paho-mqtt client per Blender session (not per node), adapted from
# the blender_mqtt_nodes addon. MQTT SUB nodes read the latest message for their
# topic from `messages`; MQTT PUB / Property Out nodes publish through publish().
#
# Threading: paho runs its network loop in a background thread. The `messages`
# dict is written from that thread and read from the main thread. Python's GIL
# makes single dict get/set atomic, which is sufficient for last-value caching.

try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:  # allow the addon to load and warn in the UI
    mqtt = None


class MQTTManager:
    DEFAULT_PORT = 1883

    def __init__(self):
        self._client = None
        self._thread = None
        self._keep_running = False
        self._broker_host = ""
        self._topic_prefix = "/mqttouch/"
        # Latest raw payload (str) per full topic, written from the network thread.
        self.messages = {}
        self.last_error = ""

    # -- lifecycle --------------------------------------------------------
    @property
    def available(self):
        return mqtt is not None

    @property
    def connected(self):
        if not self._client:
            return False
        try:
            return self._client.is_connected()
        except Exception:
            return False

    @property
    def topic_prefix(self):
        return self._topic_prefix

    def _normalize_prefix(self, prefix):
        if not prefix:
            return ""
        if not prefix.endswith("/"):
            prefix += "/"
        return prefix

    def run(self, broker_host, topic_prefix, port=DEFAULT_PORT):
        """(Re)start the client thread with the given broker + prefix."""
        if mqtt is None:
            self.last_error = "paho-mqtt is not installed in Blender's Python."
            return False
        self.stop()
        self._broker_host = broker_host
        self._topic_prefix = self._normalize_prefix(topic_prefix)
        self._port = port
        self.last_error = ""
        self._keep_running = True
        import threading
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._keep_running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self._client = None

    # -- network thread ---------------------------------------------------
    def _make_client(self):
        # paho-mqtt 2.x requires an explicit callback API version; 1.x has no
        # such argument. Use the v1 callback signatures on both.
        try:
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        except (AttributeError, TypeError):
            return mqtt.Client()

    def _run(self):
        try:
            client = self._make_client()
            client.user_data_set(self)
            client.on_connect = MQTTManager._on_connect
            client.on_message = MQTTManager._on_message
            client.connect(self._broker_host, self._port, 60)
            self._client = client
            while self._keep_running:
                client.loop(timeout=0.2)
        except Exception as exc:  # surface connection errors to the UI
            self.last_error = str(exc)
            print("[mqttouch] connection error:", exc)
            self._client = None

    @staticmethod
    def _on_connect(client, userdata, flags, rc):
        manager = userdata
        client.subscribe(manager._topic_prefix + "#")
        print("[mqttouch] connected, subscribed to", manager._topic_prefix + "#")

    @staticmethod
    def _on_message(client, userdata, msg):
        manager = userdata
        try:
            manager.messages[str(msg.topic)] = msg.payload.decode("utf-8", "replace")
        except Exception:
            pass

    # -- node-facing API --------------------------------------------------
    def get_message(self, topic_postfix):
        """Latest raw payload (str) for a topic postfix, or None."""
        return self.messages.get(self._topic_prefix + topic_postfix)

    def publish(self, topic_postfix, payload, qos=0, retain=False):
        if not self.connected:
            return False
        try:
            self._client.publish(self._topic_prefix + topic_postfix, payload, qos=qos, retain=retain)
            return True
        except Exception as exc:
            print("[mqttouch] publish error:", exc)
            return False


# Session singleton.
manager = MQTTManager()
