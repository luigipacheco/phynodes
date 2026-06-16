# MQTT Nodes

A Blender add-on that ports [mqttouch](../mqttoch) into a **native Blender node
editor**. Wire Value / Math / Map / MQTT / Property nodes together — like shader
nodes — and a 50 ms timer evaluates the graph, exchanging data with an MQTT
broker and with Blender properties.

Part of the **Animaquina** robot-IDE family. Standalone today, designed to fold
in as an Animaquina sub-module later.

## Requirements

- Blender 4.2+
- `paho-mqtt` in Blender's Python: `pip install paho-mqtt`
- An MQTT broker (Mosquitto, HiveMQ, `test.mosquitto.org`, …)

## Install

Install the `mqttnodes` folder via **Edit → Preferences → Add-ons → Install**,
or drop it in your Blender extensions/addons folder and enable it.

## Usage

1. Open a **Node Editor** and switch the tree-type dropdown (header) to
   **MQTT Nodes**. Create a new node group.
2. In the **N-panel → MQTT Nodes** tab, set the broker host / port / topic
   prefix and click **Connect**.
3. **Add → MQTT Nodes** to drop nodes. Wire them up.

### Nodes

| Node | Role | Notes |
|------|------|-------|
| **Value** | source | A constant float (slider). |
| **Color** | source | RGBA picker, outputs `[r,g,b,a]`. |
| **Property In** | source | Reads a Blender data path, e.g. `bpy.data.objects["Cube"].location[2]`. |
| **MQTT SUB** | source | Latest message on `prefix + topic`. Parses JSON / CSV / number / string. |
| **Math** | processor | Mirrors Blender's Math node; element-wise on arrays. |
| **Map Range** | processor | Linear remap between two ranges. |
| **Clamp** | processor | Constrain to `[min, max]`. |
| **Compare** | processor | `<, <=, >, >=, ==, !=` → boolean. |
| **Switch** | processor | Multiplexer; a boolean selects between two inputs. |
| **Array** | processor | Combine a configurable number of inputs into an array. |
| **JSON Parse** | processor | JSON string → value. |
| **JSON Stringify** | processor | Value → JSON string. |
| **Property Out** | sink | Writes the input into a Blender data path each tick. |
| **MQTT PUB** | sink | Publishes the input to `prefix + topic` (on change). |
| **Debug** | sink | Shows the input value in the node body (testing). |

Sinks (Property Out, MQTT PUB, Debug) are the roots the timer evaluates; they
pull the graph upstream lazily.

### Typed sockets

Each socket has a **data type** (Float / Int / Bool / String / Vector / Color /
Any), like geometry-node sockets. The type drives the unlinked default widget,
the socket color, and optional preset min/max clamping. Any socket can still
connect to any other — types only affect the default value shown when unlinked.

### Example loops

- `Property In (Cube.location.z)` → `Math ×2` → `MQTT PUB topic=cube_z`
- `MQTT SUB topic=cmd` → `Map (0..1 → 0..6.28)` → `Property Out (Cube.rotation_euler[2])`

## Architecture

- `connection.py` — one shared threaded paho client; SUB reads `messages`,
  PUB/Property-Out publish through it.
- `base.py` — `AQBaseNode`, pull-based memoized evaluation, value/type utils
  (ported from mqttouch's `BaseGraphNode`).
- `evaluator.py` — 50 ms timer evaluating sink nodes.
- `tree.py` — the `MQTT Nodes` node tree + typed Variant socket.
- `nodes/` — one module per node.
- `ui.py` — Add menu + broker N-panel.

## Status

Beta. Planned next: vendored `paho-mqtt` wheel for the extension; optional
per-node broker override; geometry-node attribute streaming.
