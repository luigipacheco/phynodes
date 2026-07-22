# GPL-3.0-or-later
# Value / type / payload utilities, ported from mqttouch's BaseGraphNode.
#
# Deliberately bpy-free: this module is imported by base.py inside Blender and
# loaded directly by the unit tests (tests/) outside it. Keep it that way — no
# bpy imports here.

import json


def is_array(value):
    return isinstance(value, (list, tuple))


def to_float_safe(value, default=0.0):
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    if is_array(value) and value:
        return to_float_safe(value[0], default)
    return default


def to_bool_safe(value):
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return 1.0 if float(value) >= 0.5 else 0.0
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "1", "on", "yes"):
            return 1.0
        return 0.0
    return 0.0


def flatten_array(arr):
    out = []
    for item in arr:
        if is_array(item):
            out.extend(flatten_array(item))
        else:
            out.append(item)
    return out


def parse_payload(message):
    """Parse a raw inbound payload into a scalar / string / (nested) array.

    Mirrors mqttouch's MQTT SUB parsing: JSON first, then CSV, then number,
    then plain string. Shared by every text-payload transport (MQTT, Zenoh,
    serial), so graphs behave the same regardless of connector.
    """
    if message is None:
        return 0.0
    message = message.strip()
    # JSON (preserves nested arrays like [[r,g,b],...])
    try:
        data = json.loads(message)
        if isinstance(data, (list, dict, int, float)):
            return data
    except (ValueError, TypeError):
        pass
    # CSV / semicolon-grouped
    arr = _parse_csv(message)
    if arr is not None:
        return arr
    # scalar number
    try:
        return float(message)
    except ValueError:
        return message


def _parse_csv(message):
    if "," not in message and ";" not in message:
        return None
    result = []
    if ";" in message:
        for group in (g for g in message.split(";") if g.strip()):
            if "," in group:
                result.append([_num(v) for v in group.split(",") if v.strip()])
            else:
                result.append(_num(group))
    else:
        result = [_num(v) for v in message.split(",") if v.strip()]
    return result if len(result) >= 2 else None


def _num(token):
    token = token.strip()
    try:
        return float(token)
    except ValueError:
        return token


def _compact_numbers(value):
    """Integral floats -> ints, recursively ([179.0, 0.0] -> [179, 0])."""
    if is_array(value):
        return [_compact_numbers(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def format_for_mqtt(value):
    """Format a value as a text payload string (arrays -> JSON).

    Integral floats print without the decimal point, matching JS
    JSON.stringify / String() in values.js. Firmware array parsers read digits
    only (fab-hello's `sscanf("[%d,%d,%d]")`, fab-led's byte parser), so a
    stray "179.0" makes the whole payload unparseable and the node ignores it.
    """
    if is_array(value):
        return json.dumps(_compact_numbers(value), separators=(",", ":"))
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
