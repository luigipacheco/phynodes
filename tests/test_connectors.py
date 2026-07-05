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


if __name__ == "__main__":
    run_tests(globals())
