# PhyNodes — Roadmap & Architecture Plan

> Living document. The goal here is to agree on direction before building, so
> the early architecture doesn't box us in.

## 1. Vision

**PhyNodes bridges the physical world and Blender.** Sensors, actuators, and
real devices become first-class citizens in a Blender node graph — so Blender
can be a **control surface, a visualizer, and a digital twin** for physical
systems.

Three pillars:

- **Sense** — bring real-world signals (buttons, IMUs, distance, temperature,
  audio, motion capture…) into Blender to drive objects, drivers, geometry
  nodes, shading.
- **Actuate** — drive servos, LEDs, motors, relays, lights, sound from Blender
  values, animation, or simulation.
- **Twin** — keep a Blender scene and a physical rig in continuous two-way sync;
  rehearse motion in Blender before it touches hardware, or mirror hardware live.

MQTT is the **first** transport. It must not be the **only** one — OSC, serial,
and others are coming, so the graph must be **transport-agnostic**.

## 2. Design principles

1. **Blender-native.** Behave like Geometry Nodes wherever it makes sense
   (typed-ish sockets, unit subtypes, sidebar interface, naming). See §7.
2. **Transport-agnostic graph.** Nodes deal in *values and channels*, not in
   "MQTT." Protocols live behind a connector interface.
3. **Live + safe.** Real-time evaluation, but never block Blender's UI thread;
   network/IO runs on connector threads.
4. **Composable.** Small nodes that combine (the mqttouch heritage), not
   monolithic "do everything" nodes.
5. **Animaquina-ready.** Stays installable standalone, folds into the Animaquina
   robot-IDE later.

## 3. Current state (Phase 0 — done)

- Custom `PhyNodes` node tree + pull-based 50 ms evaluator with viewport redraw.
- One shared MQTT connector (`connection.py`, threaded paho-mqtt).
- ~23 nodes: inputs (Value, Boolean, Integer, Vector, String, Color, Scene Time,
  Timer, Property In, Geometry Attribute, MQTT SUB), processors (Math, Map,
  Clamp, Compare, Switch, Array, Array Reduce, Easing, Float Curve, String Op,
  JSON), outputs (Custom Property, Set Property, MQTT PUB, Debug).
- Typed Variant socket, categorized Add menu, N-panel broker config, build.ps1.

**Limitation to fix first:** MQTT is hard-wired. `connection.py`, the SUB/PUB
nodes, and the settings panel all assume one broker. Adding OSC/serial today
means copy-pasting that structure. Phase 1 generalizes it.

> **Status: Phase 1 landed in v0.2.0, Phase 2 (OSC) in v0.3.0.**
> `connection.py` became the `connectors/` package (base interface + registry
> + MQTT with auto-reconnect and per-topic subscriptions + OSC), the N-panel
> is a named connections list, and I/O nodes resolve their connector by name
> (empty = first connection of their type, which keeps old files working).

## 4. Core architecture: the Connector layer

Introduce a small abstraction so every transport plugs in the same way.

```
        ┌─────────────────────────── Blender ───────────────────────────┐
        │   Node graph  (Channel In / Channel Out / protocol nodes)      │
        │                         │            ▲                          │
        │                         ▼            │                          │
        │                 ConnectorRegistry (by name)                     │
        │        ┌───────────┬───────────┬───────────┬─────────┐         │
        │        ▼           ▼           ▼           ▼         ▼         │
        │   MQTTConn    OSCConn     SerialConn   WSConn    (future)      │
        └────────┼───────────┼───────────┼───────────┼─────────┘
                 ▼           ▼           ▼           ▼
              broker       UDP        COM port     ws://      …hardware
```

### Connector interface (sketch)

```python
class Connector:
    type_id = "MQTT"               # "MQTT" | "OSC" | "ZENOH" | "SERIAL" | ...
    label   = "MQTT"

    def start(self, config): ...   # open the connection (on a worker thread)
    def stop(self): ...
    @property
    def status(self): ...          # DISCONNECTED | CONNECTING | CONNECTED | ERROR

    def ensure_subscribed(self, address):     # declare inbound interest
        ...                        # MQTT: per-topic subscribe · Zenoh: declare a
                                   # subscriber · OSC/serial: no-op (the port
                                   # receives everything)
    def read(self, address):       # latest inbound value for an address, or None
        ...
    def write(self, address, value, **opts):  # outbound; opts are protocol-specific
        ...
```

- **Inbound** values are cached per address (written from the connector's
  thread, read on the main thread — the pattern already used for MQTT).
- **`ensure_subscribed`** is part of the contract because transports differ:
  MQTT and Zenoh need explicit per-address subscriptions, OSC/serial receive
  everything on the port. SUB-type nodes call it every evaluation; it must be
  idempotent and cheap. (It also keeps the inbox bounded — no more
  subscribe-to-`#`.)
- **Address** is the protocol's routing key: MQTT topic, OSC path, Zenoh key
  expression, serial line-key, etc.
- **Restart safety:** worker threads carry a *generation token* captured at
  start; `stop()` bumps it and workers bail out without touching shared state,
  so a thread stuck in a slow connect can't clobber a newer connection.
- Config lives in `scene.phynodes.connectors` (a flat superset of fields);
  each connector class draws only its own fields (`draw_config`) and extracts
  a plain dict for its worker (`config_from_item` — bpy properties never cross
  the thread boundary).

### Scene data model

- `scene.phynodes.connectors`: a `CollectionProperty` of connector configs
  (type enum + per-type fields), edited in an N-panel list — "add a connector,
  pick MQTT/OSC/Serial, configure, connect."
- Live connector objects live in a module-level registry keyed by name.

### Node model — decided: Option B

- **Option A — Generic Channel I/O:** `Channel In` / `Channel Out` nodes with a
  *connector* dropdown + *address* field. Scales to any transport with two
  nodes, but hides the transport in the Add menu.
- **Option B — Per-protocol nodes (chosen):** `MQTT SUB/PUB`, `OSC In/Out`,
  `Zenoh Sub/Pub` … all sharing the `ConnectorIONode` base
  (`nodes/io_base.py`). Discoverable in the Add menu; the connector *instance*
  is configured in the N-panel list, so a node just picks "which connection" +
  address. An empty connector name means "first live connection of my type",
  which keeps one-connection setups zero-config.

## 5. Connector catalogue

| Transport | Python lib | Dir. | Why it matters | Priority |
|-----------|-----------|------|----------------|----------|
| **MQTT** | paho-mqtt | ⇄ | IoT, ESP32, Node-RED, Home Assistant | ✅ done |
| **OSC** | python-osc | ⇄ | TouchOSC, Max/MSP, Pd, VJ/interactive, mocap | ✅ done |
| **Zenoh** | eclipse-zenoh | ⇄ | Broker-less peer mode, ROS 2 interop (rmw_zenoh / zenoh-bridge-ros2dds), robot fleets | ★ next |
| **Serial** | pyserial | ⇄ | Arduino/microcontrollers direct, no broker | ◐ |
| **WebSocket** | websockets | ⇄ | Browsers, web dashboards, p5.js | ◐ |
| **Art-Net / sACN / DMX** | (lib) | → | Stage lighting, LED fixtures | ◐ |
| **MIDI** | mido / rtmidi | ⇄ | Controllers, music-reactive, faders | ◐ |
| **HTTP / REST** | stdlib | ⇄ | Webhooks, cloud APIs, polling sensors | ◐ |
| **GPIO** | RPi.GPIO/gpiozero | ⇄ | Blender on a Raspberry Pi driving pins | ○ |
| **Firmata** | pyfirmata | ⇄ | Standard Arduino pin protocol over serial | ○ |

(✅ done · ★ next · ◐ later · ○ exploratory)

**Why OSC before Zenoh:** python-osc is pure Python (one universal wheel, zero
packaging risk) and stresses the abstraction differently — it's *asymmetric*
(a UDP listen port for inbound, a host:port client for outbound) and already
typed (type tags), so it proves the seam cheaply. Zenoh's cost is mostly the
Rust-backed per-platform wheels and the release-pipeline change they require.

**Why Zenoh at all:** it's the strategic transport for Animaquina — no broker
to run in peer mode (one less moving part in installations), key expressions
(`robot/arm/**`) that map one-to-one onto the topic model, and a straight path
to ROS 2 robots via `rmw_zenoh` / `zenoh-bridge-ros2dds`. API stable since
1.x (late 2024); EPL-2.0/Apache-2.0, GPL-compatible. Pub/sub first;
queryables/liveliness (e.g. a "device online" node) are later extras.

## 6. Phased roadmap

- **Phase 1 — Connector refactor. ✅ done (v0.2.0).** `Connector` base +
  registry (`connectors/`); MQTT behind it with auto-reconnect (exponential
  backoff), per-topic subscriptions, and generation-guarded worker threads;
  named connections list in the N-panel with legacy-settings migration;
  SUB/PUB on the `ConnectorIONode` base; bpy-free helpers split into
  `values.py` with unit tests + CI.
- **Phase 2 — OSC. ✅ done (v0.3.0).** python-osc bundled (universal wheel);
  `connectors/osc.py` with listen port (0 = receive off) + send host:port,
  `ThreadingOSCUDPServer` feeding the inbox (1 arg → scalar, n args → array),
  `SimpleUDPClient` for send; OSC In/Out nodes; switching an entry's type in
  the N-panel resets its fields to that transport's defaults; loopback test
  runs against the vendored wheel. Follow-ups: OSC pattern matching
  (`/fader/*`), bundles/timetags, manual TouchOSC / Protokol verification.
- **Phase 3 — Zenoh.** Packaging first: per-platform eclipse-zenoh wheels,
  `--split-platforms` release builds, lazy import (a platform without a wheel
  just shows "Zenoh unavailable"). Config = mode (peer/client) + optional
  router endpoints; `ensure_subscribed` declares a subscriber per key
  expression; `write` = `session.put`. Reuse `parse_payload` so MQTT and Zenoh
  graphs behave identically. Zenoh Sub/Pub nodes. Later: liveliness ("device
  online" node), queryables, documented ROS 2 recipe via zenoh-bridge-ros2dds.
- **Phase 4 — Serial.** Line/JSON framing, COM port + baud, hot-plug handling.
- **Phase 5 — Breadth.** WebSocket, Art-Net/DMX, MIDI as the abstraction proves
  out; community-addable connectors.
- **Phase 6 — Digital twin.** Two-way binding presets, record & playback of
  channel streams, "Blender drives / hardware drives" arbitration, lag/health
  monitoring, calibration nodes.

## 7. Node-system evolution (Geometry-Nodes alignment)

From the GN review — fold these in across phases:

- **Unit subtypes** on Float sockets (Angle→degrees/radians, Distance, Factor,
  Time) so values read in scene units but flow SI.
- **Socket shapes** (circle vs diamond) to signal scalar vs array, like fields.
- **Socket model:** hybrid — concrete typed sockets with implicit conversion for
  everything touching Blender, `Any` only at the dynamic transport boundary.
- **Node groups / `tree.interface`** for reusable sub-graphs (e.g. a packaged
  "servo channel" group).
- Naming toward `class == bl_idname`; category header colors.

## 8. Digital-twin building blocks

- **Binding presets** — one-click "bind this object's rotation to this channel"
  both ways.
- **Record / playback** — capture inbound channel streams to re-run offline.
- **Simulation-ahead** — run motion in Blender, preview, then commit to hardware.
- **Health & safety** — connection status surfaced in the header; rate limits;
  clamp/limit nodes on outputs to protect actuators.

## 9. Packaging & dependencies

- Each connector adds a Python dependency. Move to **vendored wheels** in
  `blender_manifest.toml` (`[build] / wheels`) so users don't run pip — and only
  load a connector's lib when that connector is used (lazy import).
- Keep connectors **optional**: a missing lib disables just that transport, with
  a clear note (the MQTT panel already does this for paho).
- **Pure-Python vs binary wheels:** paho-mqtt and python-osc ship one universal
  wheel each. eclipse-zenoh is Rust-backed — per-platform wheels (~5–10 MB
  each, win/mac/linux × x64/arm64), listed together in the manifest and split
  into per-platform zips with `blender --command extension build
  --split-platforms`. That release-pipeline change is the bulk of Phase 3.

## 10. Decisions & open questions

Decided (v0.2.0):

1. **Node model:** Option B — per-protocol nodes sharing the `ConnectorIONode`
   base, with the connector instance picked from the N-panel list (empty =
   first of type).
2. **Connector scope:** multiple **named** instances
   (`scene.phynodes.connectors` collection) — two brokers, an MQTT + an OSC
   endpoint, etc.
3. **Next transports:** OSC (Phase 2), then Zenoh (Phase 3) — see §5 for the
   rationale. Serial moves to Phase 4.
4. **Scope of Phase 1:** refactor only; OSC ships separately.

Still open:

5. **Serial framing:** newline `key value`, JSON-lines, CSV, or Firmata?
   (Probably JSON-lines + raw line modes.)
6. How much of the **GN socket-model** work (§7) to pull forward vs defer.
7. **Renaming a connected connector** orphans its live instance until the next
   connect/disconnect sweep (`registry.prune`). Good enough, or key live
   instances by a stable UID instead of the name?
