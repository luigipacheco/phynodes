# GPL-3.0-or-later
# Unit tests for the connector base class and registry (bpy-free).
# The MQTT connector is exercised only up to the network boundary: config
# parsing, prefix normalization, and subscription bookkeeping.

from _loader import load_module, run_tests

connectors = load_module("phynodes_connectors", "connectors/__init__.py",
                         package_dir="connectors")


class DummyConnector(connectors.Connector):
    type_id = "DUMMY"
    label = "Dummy"

    def __init__(self, name=""):
        super().__init__(name)
        self.started = False
        self.written = []

    def start(self, config):
        self.started = True
        return True

    def stop(self):
        super().stop()
        self.started = False

    def write(self, address, payload, **opts):
        self.written.append((address, payload))
        return True


def _fresh_registry():
    connectors.stop_all()
    connectors.TYPES["DUMMY"] = DummyConnector
    return connectors


def test_base_read_defaults_to_none():
    conn = connectors.Connector("x")
    assert conn.read("nope") is None
    conn._inbox["addr"] = "1.0"
    assert conn.read("addr") == "1.0"


def test_generation_token():
    conn = connectors.Connector("x")
    gen = conn._next_generation()
    assert conn._current(gen)
    conn.stop()  # bumps the generation
    assert not conn._current(gen)


def test_registry_start_stop_resolve():
    reg = _fresh_registry()
    conn = reg.start("a", "DUMMY", {})
    assert conn is not None and conn.started
    assert reg.get("a") is conn
    # named resolve, and empty-name resolve to first of type
    assert reg.resolve("a", "DUMMY") is conn
    assert reg.resolve("", "DUMMY") is conn
    # wrong type never matches
    assert reg.resolve("a", "MQTT") is None
    reg.stop("a")
    assert reg.get("a") is None
    assert not conn.started
    reg.stop_all()


def test_registry_restart_replaces_instance():
    reg = _fresh_registry()
    first = reg.start("a", "DUMMY", {})
    second = reg.start("a", "DUMMY", {})
    assert second is not first
    assert not first.started and second.started
    reg.stop_all()


def test_registry_prune_stops_orphans():
    reg = _fresh_registry()
    reg.start("kept", "DUMMY", {})
    orphan = reg.start("renamed-away", "DUMMY", {})
    reg.prune({"kept"})
    assert reg.get("kept") is not None
    assert reg.get("renamed-away") is None
    assert not orphan.started
    reg.stop_all()


def test_registry_unknown_type():
    reg = _fresh_registry()
    assert reg.start("a", "NOPE", {}) is None
    reg.stop_all()


def test_mqtt_prefix_normalization():
    norm = connectors.MQTTConnector._normalize_prefix
    assert norm("") == ""
    assert norm("/phynodes/") == "/phynodes/"
    assert norm("/phynodes") == "/phynodes/"


def test_mqtt_subscription_bookkeeping():
    conn = connectors.MQTTConnector("m")
    conn._prefix = "/p/"
    # no client yet: interest is only recorded
    conn.ensure_subscribed("sensor")
    conn.ensure_subscribed("sensor")  # idempotent
    assert conn._subs == {"/p/sensor"}
    # inbox reads are prefix-qualified
    conn._inbox["/p/sensor"] = "1.0"
    assert conn.read("sensor") == "1.0"
    assert conn.read("other") is None


def test_mqtt_write_without_client_fails_cleanly():
    conn = connectors.MQTTConnector("m")
    assert conn.write("topic", "1") is False


def test_mqtt_start_without_paho_reports_error():
    if connectors.MQTTConnector.available():
        return  # paho installed here; the no-lib path can't be exercised
    conn = connectors.MQTTConnector("m")
    ok = conn.start({"host": "localhost", "port": 1883, "prefix": ""})
    assert ok is False
    assert "paho" in conn.last_error


# -- FabNodes identity (transport-level, bpy-free) ---------------------------

class _FakeConfigItem:
    """Stand-in for a scene connector entry (config_from_item uses getattr)."""
    host = "broker.local"
    port = 1883
    topic_prefix = "/phynodes/"
    username = ""
    password = ""
    fabnode_enabled = True
    fabnode_name = "blender1"
    fabnode_type = "fab-blender"


def test_mqtt_config_extracts_fabnode_fields():
    cfg = connectors.MQTTConnector.config_from_item(_FakeConfigItem())
    assert cfg["fab_enabled"] is True
    assert cfg["fab_name"] == "blender1"
    assert cfg["fab_type"] == "fab-blender"


def test_mqtt_config_fabnode_type_default_when_blank():
    item = _FakeConfigItem()
    item.fabnode_type = "   "
    cfg = connectors.MQTTConnector.config_from_item(item)
    assert cfg["fab_type"] == "fab-blender"


def test_mqtt_fabnode_defaults_off():
    conn = connectors.MQTTConnector("m")
    assert conn.fab_enabled is False
    assert conn.estop_active is False


def test_mqtt_estop_latch_and_clear():
    conn = connectors.MQTTConnector("m")
    conn.fab_name = "blender1"
    # no client attached: _handle_estop must still latch without raising
    for truthy in ("1", "true", "on", "0.9"):
        conn.estop_active = False
        conn._handle_estop(truthy)
        assert conn.estop_active is True, truthy
    for falsy in ("0", "false", "off", "", "0.1"):
        conn.estop_active = True
        conn._handle_estop(falsy)
        assert conn.estop_active is False, falsy


def test_mqtt_fabnode_publishes_need_connection():
    # Guards: no live client → manifest/heartbeat/clear are safe no-ops.
    conn = connectors.MQTTConnector("m")
    conn.fab_name = "blender1"
    assert conn.publish_manifest("{}") is False
    conn.publish_heartbeat()        # must not raise
    conn.clear_retained_fabnode()   # must not raise


def test_base_connector_answers_fabnode_query():
    # fabnode.tick() asks every live connector uniformly; non-MQTT ones must
    # answer the identity attributes without special-casing.
    conn = connectors.OSCConnector("o")
    assert getattr(conn, "fab_enabled", None) is False
    assert getattr(conn, "estop_active", None) is False


# -- OSC ----------------------------------------------------------------------

def test_osc_address_normalization():
    norm = connectors.OSCConnector._norm
    assert norm("/fader/1") == "/fader/1"
    assert norm("fader/1") == "/fader/1"


def test_osc_write_without_client_fails_cleanly():
    conn = connectors.OSCConnector("o")
    assert conn.write("/x", 1.0) is False


def test_osc_start_unconfigured_reports_error():
    conn = connectors.OSCConnector("o")
    ok = conn.start({"listen_port": 0, "send_host": "", "send_port": 0})
    # fails either as "nothing to do" or as "python-osc missing" — both are
    # errors surfaced to the panel, never a silent half-start
    assert ok is False
    assert conn.last_error


def test_osc_loopback():
    if not connectors.OSCConnector.available():
        return  # python-osc not installed here (CI installs it)
    import socket
    import time

    # grab a free UDP port
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    conn = connectors.OSCConnector("o")
    ok = conn.start({"listen_port": port, "send_host": "127.0.0.1", "send_port": port})
    assert ok, conn.last_error
    try:
        assert conn.status == connectors.CONNECTED

        def _wait_for(address):
            for _ in range(100):
                value = conn.read(address)
                if value is not None:
                    return value
                time.sleep(0.02)
            raise AssertionError("no message on %s" % address)

        assert conn.write("/x", 1.5)
        assert _wait_for("/x") == 1.5
        # multi-argument messages come out as arrays
        assert conn.write("/multi", [1, 2])
        assert _wait_for("/multi") == [1, 2]
    finally:
        conn.stop()
    assert conn.status == connectors.DISCONNECTED


if __name__ == "__main__":
    run_tests(globals())
