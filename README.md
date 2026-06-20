# PhyNodes

**Physical computing for Blender.** Wire sensors, actuators, and the physical
world into Blender through a native node editor — like shader nodes, but the
values come from real hardware over MQTT.

A temperature sensor rotates a dial. A distance sensor drives a mesh. A slider in
Blender dims a real LED. PhyNodes turns Blender into a live interface between the
3D scene and microcontrollers, robots, and installations.

Part of the **[Animaquina](https://www.animaquina.com)** robot-IDE family.
Ports the [mqttouch](https://github.com/luigipacheco/MqttTouch) (Godot) node
editor into Blender.

> Status: **beta** — under active development, APIs and nodes may change.

---

## What it's for

```mermaid
flowchart LR
    subgraph Hardware
      S[Sensors<br/>buttons · IMU · distance · temp]
      A[Actuators<br/>servos · LEDs · motors · relays]
    end
    B([MQTT Broker<br/>Mosquitto / HiveMQ])
    subgraph Blender
      G[PhyNodes graph]
      V[3D scene · drivers · geometry nodes]
    end

    S -- publish --> B -- MQTT SUB --> G --> V
    V -- Property / Attribute --> G -- MQTT PUB --> B -- subscribe --> A
```

- **Sense** — subscribe to sensor topics and drive object transforms, custom
  properties, shape keys, or geometry-node inputs (via drivers).
- **Actuate** — read any Blender property or geometry-node attribute and publish
  it to a topic that a microcontroller turns into motion, light, or sound.
- **Prototype** — build a digital twin that mirrors hardware in real time, or
  test motion logic in Blender before it ever touches a motor.

Anything that speaks MQTT works: ESP32 / ESP8266 / Arduino (PubSubClient),
Raspberry Pi, Node-RED, Home Assistant, or a Python script on your bench.

## Features

- **Native node editor** — a dedicated *PhyNodes* node tree; add nodes from the
  categorized **Add** menu, wire them like shader nodes.
- **Live evaluation** — the graph is evaluated on a timer (default 20 Hz,
  adjustable); changes repaint the viewport without you clicking.
- **Bi-directional MQTT** — one shared broker connection; SUB nodes bring data
  in, PUB nodes send it out.
- **Blender as I/O** — read/write object properties and **geometry-node
  attributes**; generate driver-ready custom properties.
- **Typed sockets** — Float / Int / Bool / Vector / Color / String / Any, with
  per-socket defaults shown in the N-panel, geometry-nodes style.
- **Time & math** — Scene Time, a continuous Timer, and a Blender-style Math
  node for LFOs, easing, and timing.
- **Nothing to install** — `paho-mqtt` is bundled with the add-on.

## Requirements

- **Blender 4.2 or newer**
- An **MQTT broker** — e.g. [Mosquitto](https://mosquitto.org), HiveMQ, or the
  public test server `test.mosquitto.org`

`paho-mqtt` is **bundled** and installed automatically, so there's no `pip` step.

## Install

1. Download the latest **`phynodes-x.y.z.zip`** from Releases.
2. Blender → **Edit ▸ Preferences ▸ Get Extensions ▸ Install from Disk…**
   (or **Add-ons ▸ Install…**) and pick the zip.
3. Enable **PhyNodes**. Blender installs the bundled `paho-mqtt` on enable.

> Install from the **zip** so the bundled MQTT wheel is picked up. If MQTT can't
> connect after enabling, disable then re-enable the add-on once.

## Quick start

1. Open a **Node Editor**, switch the tree-type dropdown (header) to
   **PhyNodes**, and create a new node tree.
2. In the sidebar (**N ▸ PhyNodes**), set **Broker Host** / **Port** /
   **Topic Prefix**, then **Connect**.
3. **Add ▸** pick nodes from the categories and wire them up.

### Drive a cube from a sensor

```
MQTT SUB  (topic: distance)
   └─▶ Map Range  (0..1023 → 0..3.14)
          └─▶ Custom Property  (name: dist)   →  Copy Var Path → ["dist"]
```

Add a **driver** to the cube's Rotation Z → *Single Property* variable, ID =
Scene, Path = `["dist"]`, expression `var`. Publish to `/phynodes/distance` and
the cube turns.

### Send Blender motion to an actuator

```
Property In  (bpy.data.objects["Cube"].location[2])
   └─▶ Math  (Multiply ×100)
          └─▶ MQTT PUB  (topic: servo)
```

Move the cube; a servo subscribed to `/phynodes/servo` follows.

### A continuous LFO (no playback needed)

```
Timer ──▶ Math (Sine) ──▶ Custom Property "wave"   (→ driver anything)
```

### Stream geometry-node data out

```
Geometry Attribute  (object, attribute: position, All Elements)
   └─▶ MQTT PUB  (topic: points)
```

## Node reference

### Inputs
| Node | Output |
|------|--------|
| **Value** | A 0–1 slider remapped to a Min/Max range |
| **Boolean** | A toggle (0/1) |
| **Integer** / **Vector** / **String** | Typed constants |
| **Color** | RGBA picker → `[r,g,b,a]` |
| **Scene Time** | Frame and Seconds from the timeline |
| **Timer** | Continuous wall-clock seconds, with Reset |
| **Property In** | Reads a Blender data path |
| **Geometry Attribute** | Reads a mesh / geometry-nodes attribute (scalar, vector, or per-element array) |
| **MQTT SUB** | Latest message on a topic (parses JSON / CSV / number / string) |

### Processors
| Node | Does |
|------|------|
| **Math** | Mirrors Blender's Math node; element-wise on arrays |
| **Map Range** | Linear remap between two ranges |
| **Clamp** | Constrain to `[min, max]` |
| **Easing** | Remap a 0–1 factor through a Penner easing curve (sine/quad/cubic/expo/circ/back/elastic/bounce, in/out/in-out) into a Min/Max range |
| **Float Curve** | Remap a 0–1 factor through a hand-drawn curve (Blender's native curve widget) into a Min/Max range |
| **Compare** | `<, <=, >, >=, ==, !=` → boolean |
| **Switch** | A boolean selects between two inputs |
| **Array** | Combine many inputs (multi-input socket) into an array |
| **Array Reduce** | Collapse an array to one value (sum, average, min/max, range, median, count, first/last) |
| **String Op** | Text ops: concatenate, case, strip, replace, slice, length, contains, split, join (sockets adapt to the operation) |
| **JSON Parse / Stringify** | Text ⇄ value |

### Outputs
| Node | Does |
|------|------|
| **Custom Property** | Generates a driver-ready custom property (`scene["name"]`) of a chosen type; **Copy Var Path** for a driver variable |
| **Set Property** | Writes directly into an existing data path each tick |
| **MQTT PUB** | Publishes the input to a topic (on change) |
| **Debug** | Shows the latest value in the node body |

**Sinks** (Custom Property, Set Property, MQTT PUB, Debug) are the roots the
timer evaluates each tick; everything upstream is pulled lazily and memoized.

## Typed sockets

Every socket carries a **data type** (Float / Int / Bool / Vector / Color /
String / Any) that drives its default widget and color — like geometry-node
sockets. Connections are permissive (any-to-any); types only shape the unlinked
default. Select a node and open the **N-panel** to edit per-socket type, default,
and optional min/max.

## Architecture

| File | Role |
|------|------|
| `tree.py` | The PhyNodes node tree + typed Variant socket |
| `base.py` | Node base class, pull-based memoized evaluation, value/type utils |
| `evaluator.py` | The timer: evaluates sink nodes and requests redraws |
| `connection.py` | One shared threaded `paho-mqtt` client |
| `settings.py` | Scene-level broker config + refresh interval |
| `nodes/` | One module per node |
| `ui.py` | Categorized Add menu + broker N-panel |

Evaluation is **pull-based**: each node computes its output by pulling upstream
inputs (cached per tick, cycle-guarded). Sink nodes are the entry points the
~50 ms timer drives.

## Building from source

**Any OS** — Blender's own extension builder (recommended):

```sh
blender --command extension build --source-dir . --output-dir .
```

**Windows / PowerShell** — convenience script that also compile-checks and can
sync into Blender for testing:

```powershell
.\build.ps1                       # compile-check + build phynodes-<version>.zip
.\build.ps1 -Sync                 # also copy into Blender's extensions folder
.\build.ps1 -Sync -Blender 5.2    # target a specific Blender version
```

The zip keeps `blender_manifest.toml` at its root (required by Blender) and
bundles the `paho-mqtt` wheel from `wheels/`. To refresh that wheel:

```sh
python -m pip download paho-mqtt --only-binary=:all: --no-deps -d wheels
```

## Troubleshooting

- **No nodes in the Add menu** — set the node editor's tree type to *PhyNodes*
  and make sure the add-on is enabled. After updating, **fully restart Blender**
  (a "Reload Scripts" can drop the evaluation timer).
- **A value doesn't propagate** — it only flows if it's wired to a **sink**
  (Custom Property / Set Property / MQTT PUB / Debug), and the graph is
  **Enabled** in the N-panel.
- **Can't connect** — check broker host/port; the N-panel shows the error.
- **paho-mqtt not installed** — install from the **zip** (so the bundled wheel
  is used), then disable/enable the add-on once.

## Roadmap

- More transports beyond MQTT (OSC, serial, …) behind a connector layer
- Geometry-Nodes-style typed sockets, unit subtypes, node groups
- Digital-twin helpers: record/playback, two-way binding, output safety
- Optional per-node broker override; writing back into geometry attributes

## License & credits

GPL-3.0-or-later. Built on the ideas of
[mqttouch](https://github.com/luigipacheco/MqttTouch) and the original Blender
MQTT addon by Aurel Wildfellner. Part of **Animaquina** by Luis Arturo
Pacheco — <https://www.animaquina.com>.
