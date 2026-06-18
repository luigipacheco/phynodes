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
    type_id = "base"               # "mqtt" | "osc" | "serial" | ...
    label   = "Base"

    def start(self): ...           # open the connection (on a worker thread)
    def stop(self): ...
    @property
    def status(self): ...          # DISCONNECTED | CONNECTING | CONNECTED | ERROR

    def read(self, address):       # latest inbound value for an address, or None
        ...
    def write(self, address, value, **opts):  # outbound; opts are protocol-specific
        ...
```

- **Inbound** values are cached per address (written from the connector's
  thread, read on the main thread — the pattern already used for MQTT).
- **Address** is the protocol's routing key: MQTT topic, OSC path, serial
  line-key, etc.
- Each connector type ships a small **config PropertyGroup** (broker/port,
  host/port, COM/baud…) and draws its own settings.

### Scene data model

- `scene.phynodes.connectors`: a `CollectionProperty` of connector configs
  (type enum + per-type fields), edited in an N-panel list — "add a connector,
  pick MQTT/OSC/Serial, configure, connect."
- Live connector objects live in a module-level registry keyed by name.

### Node model — decision to review (see §9)

- **Option A — Generic Channel I/O:** `Channel In` / `Channel Out` nodes with a
  *connector* dropdown + *address* field; the node draws protocol-specific
  options based on the chosen connector. Scales to any transport with two nodes.
- **Option B — Per-protocol nodes:** `MQTT SUB/PUB`, `OSC In/Out`, `Serial
  In/Out` … all sharing a `ConnectorIO` base. More discoverable in the Add menu,
  more nodes to maintain.
- **Recommendation:** B for discoverability, all sharing one base, with the
  connector *instance* configured in the N-panel list (so a node just picks
  "which OSC endpoint" + address).

## 5. Connector catalogue

| Transport | Python lib | Dir. | Why it matters | Priority |
|-----------|-----------|------|----------------|----------|
| **MQTT** | paho-mqtt | ⇄ | IoT, ESP32, Node-RED, Home Assistant | ✅ done |
| **OSC** | python-osc | ⇄ | TouchOSC, Max/MSP, Pd, VJ/interactive, mocap | ★ next |
| **Serial** | pyserial | ⇄ | Arduino/microcontrollers direct, no broker | ★ next |
| **WebSocket** | websockets | ⇄ | Browsers, web dashboards, p5.js | ◐ |
| **Art-Net / sACN / DMX** | (lib) | → | Stage lighting, LED fixtures | ◐ |
| **MIDI** | mido / rtmidi | ⇄ | Controllers, music-reactive, faders | ◐ |
| **HTTP / REST** | stdlib | ⇄ | Webhooks, cloud APIs, polling sensors | ◐ |
| **GPIO** | RPi.GPIO/gpiozero | ⇄ | Blender on a Raspberry Pi driving pins | ○ |
| **Firmata** | pyfirmata | ⇄ | Standard Arduino pin protocol over serial | ○ |

(✅ done · ★ next · ◐ later · ○ exploratory)

## 6. Phased roadmap

- **Phase 1 — Connector refactor.** Extract `Connector` base + registry; make
  MQTT the first implementation behind it; connectors list in the N-panel;
  generalize SUB/PUB onto a `ConnectorIO` base. *No new features, just the seam.*
- **Phase 2 — OSC.** First proof the abstraction holds with a second transport.
  OSC In/Out nodes, address patterns, bundle/type-tag handling.
- **Phase 3 — Serial.** Line/JSON framing, COM port + baud, hot-plug handling.
- **Phase 4 — Breadth.** WebSocket, Art-Net/DMX, MIDI as the abstraction proves
  out; community-addable connectors.
- **Phase 5 — Digital twin.** Two-way binding presets, record & playback of
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

## 10. Open questions to review together

1. **Node model:** generic `Channel In/Out` (Option A) vs per-protocol nodes
   sharing a base (Option B)? (I lean B.)
2. **Connector scope:** one global connector per type, or multiple named
   instances (e.g. two brokers, three serial ports)? (I lean multiple/named.)
3. **Serial framing:** what's the default wire format — newline `key value`,
   JSON-lines, CSV, or Firmata? (Probably JSON-lines + raw line modes.)
4. **Next transport after the refactor:** OSC or Serial first?
5. **Scope of Phase 1:** refactor only (safe), or refactor + ship OSC together?
6. How much of the **GN socket-model** work to pull forward vs defer.
