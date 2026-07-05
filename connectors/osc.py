# GPL-3.0-or-later
# OSC connector: UDP in/out via python-osc.
#
# OSC is asymmetric (unlike MQTT's single broker socket): inbound is a UDP
# server on a listen port, outbound is a client aimed at a host:port. Either
# side is optional — listen_port 0 disables receive, an empty send host
# disables send. Values arrive already typed (OSC type tags), so there's no
# payload parsing: one argument -> scalar, several -> list.

import threading

try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient
except ModuleNotFoundError:  # allow the addon to load and warn in the UI
    Dispatcher = ThreadingOSCUDPServer = SimpleUDPClient = None

from .base import Connector, DISCONNECTED, CONNECTING, CONNECTED, ERROR


class OSCConnector(Connector):
    type_id = "OSC"
    label = "OSC"
    requires = "python-osc"

    def __init__(self, name=""):
        super().__init__(name)
        self._server = None
        self._thread = None
        self._client = None

    # -- availability / config --------------------------------------------
    @classmethod
    def available(cls):
        return SimpleUDPClient is not None

    @classmethod
    def config_from_item(cls, item):
        return {
            "listen_port": item.listen_port,
            "send_host": item.host,
            "send_port": item.port,
        }

    @classmethod
    def apply_defaults(cls, item):
        item.host = "127.0.0.1"
        item.port = 9000
        item.listen_port = 9001

    @classmethod
    def draw_config(cls, layout, item):
        layout.prop(item, "listen_port")
        col = layout.column(align=True)
        col.prop(item, "host", text="Send Host")
        col.prop(item, "port", text="Send Port")

    @staticmethod
    def _norm(address):
        # OSC addresses always start with "/"; be forgiving about typing it.
        if not address.startswith("/"):
            address = "/" + address
        return address

    # -- lifecycle ----------------------------------------------------------
    @property
    def status(self):
        thread = self._thread
        if (thread is not None and thread.is_alive()) or self._client is not None:
            return CONNECTED
        return ERROR if self.last_error else DISCONNECTED

    def start(self, config):
        if SimpleUDPClient is None:
            self.last_error = "python-osc is not installed in Blender's Python"
            return False
        self.stop()
        self.last_error = ""
        listen_port = int(config.get("listen_port", 0))
        send_host = config.get("send_host", "")
        send_port = int(config.get("send_port", 0))
        if listen_port <= 0 and not (send_host and send_port > 0):
            self.last_error = "set a listen port and/or a send host + port"
            return False
        gen = self._next_generation()
        if send_host and send_port > 0:
            try:
                self._client = SimpleUDPClient(send_host, send_port)
            except Exception as exc:
                self.last_error = str(exc)
                return False
        if listen_port > 0:
            dispatcher = Dispatcher()
            dispatcher.set_default_handler(self._on_message)
            try:
                # binds here, so port-in-use errors surface immediately
                self._server = ThreadingOSCUDPServer(("0.0.0.0", listen_port), dispatcher)
            except OSError as exc:
                self.last_error = "port %d: %s" % (listen_port, exc)
                self._client = None
                return False
            self._thread = threading.Thread(
                target=self._serve, args=(gen, self._server), daemon=True,
                name="phynodes-osc-" + (self.name or "unnamed"),
            )
            self._thread.start()
        return True

    def stop(self):
        self._next_generation()
        server = self._server
        if server is not None:
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                pass
            self._server = None
        thread = self._thread
        if thread is not None:
            thread.join(timeout=1.0)
            self._thread = None
        self._client = None

    # -- worker thread -------------------------------------------------------
    def _serve(self, gen, server):
        try:
            server.serve_forever(poll_interval=0.2)
        except Exception as exc:
            if self._current(gen):
                self.last_error = str(exc)
                print("[phynodes] osc '%s': %s" % (self.name, exc))

    def _on_message(self, address, *args):
        # server thread; last-value cache like every transport
        if len(args) == 1:
            self._inbox[address] = args[0]
        else:
            self._inbox[address] = list(args)

    # -- node-facing I/O ----------------------------------------------------
    # ensure_subscribed: inherited no-op — the listen port receives everything.

    def read(self, address):
        return self._inbox.get(self._norm(address))

    def write(self, address, payload, **_opts):
        client = self._client
        if client is None:
            return False
        try:
            client.send_message(self._norm(address), payload)
            return True
        except Exception as exc:
            print("[phynodes] osc '%s' send error: %s" % (self.name, exc))
            return False
