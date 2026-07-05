# GPL-3.0-or-later
# Transport-agnostic connector interface. Every transport (MQTT, OSC, Zenoh,
# serial, ...) subclasses Connector, so nodes and the UI deal in one contract:
# start/stop a connection, declare inbound interest, read the latest value for
# an address, write a value to an address.
#
# Deliberately bpy-free (the draw_config hook receives a bpy layout but never
# imports bpy) so this module is unit-testable outside Blender.
#
# Threading model, shared by all transports:
# - Network I/O runs on the connector's worker thread(s); Blender's main
#   thread must never block on it.
# - Inbound values land in `_inbox` (last-value cache): written from the
#   worker thread, read on the main thread. Python's GIL makes a single dict
#   get/set atomic, which is sufficient for last-value semantics.
# - `_generation` guards restarts: worker threads capture the generation they
#   were started with and bail out (without touching shared state) as soon as
#   it changes, so a stale thread — e.g. one stuck in a slow DNS lookup —
#   can't clobber a newer connection.

DISCONNECTED = "DISCONNECTED"
CONNECTING = "CONNECTING"
CONNECTED = "CONNECTED"
ERROR = "ERROR"


class Connector:
    type_id = "BASE"   # EnumProperty identifier, e.g. "MQTT" | "OSC" | "ZENOH"
    label = "Base"     # human-readable transport name
    requires = ""      # pip name of the backing library, for UI error messages

    def __init__(self, name=""):
        self.name = name          # matches the scene config entry's name
        self.last_error = ""
        # Latest inbound value per address (full routing key, e.g. an MQTT
        # topic or OSC path). Written from the worker thread, read on the
        # main thread.
        self._inbox = {}
        self._generation = 0

    # -- availability / config --------------------------------------------
    @classmethod
    def available(cls):
        """False when the backing Python library is missing."""
        return True

    @classmethod
    def config_from_item(cls, item):
        """Extract a plain config dict from a scene connector entry. Runs on
        the main thread; workers must only ever see plain Python values,
        never bpy properties."""
        return {}

    @classmethod
    def apply_defaults(cls, item):
        """Reset the transport fields of a scene connector entry to this
        transport's sensible defaults (called when the user switches an
        entry's type)."""
        pass

    @classmethod
    def draw_config(cls, layout, item):
        """Draw this transport's config fields in the N-panel."""
        pass

    # -- lifecycle ----------------------------------------------------------
    def start(self, config):
        """Open the connection (spawn the worker thread). Returns False and
        sets last_error when it can't even try (e.g. missing library)."""
        raise NotImplementedError

    def stop(self):
        """Signal workers to exit; must not block the UI for long."""
        self._next_generation()

    @property
    def status(self):
        return DISCONNECTED

    def _next_generation(self):
        self._generation += 1
        return self._generation

    def _current(self, generation):
        return generation == self._generation

    # -- node-facing I/O ----------------------------------------------------
    def ensure_subscribed(self, address):
        """Declare inbound interest in an address. Called by SUB-type nodes
        every evaluation; must be idempotent and cheap. MQTT subscribes to
        the topic, Zenoh declares a subscriber for the key expression, OSC
        needs nothing (the listen port receives everything)."""
        pass

    def read(self, address):
        """Latest inbound value for an address, or None."""
        return self._inbox.get(address)

    def write(self, address, payload, **opts):
        """Send a payload to an address; opts are protocol-specific
        (e.g. qos/retain for MQTT). Returns True on accepted send."""
        raise NotImplementedError
