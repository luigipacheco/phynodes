# GPL-3.0-or-later
# Shared base for transport I/O nodes (MQTT SUB/PUB, and OSC/Zenoh/... later).
#
# Concrete node classes set `connector_type_id` and declare their own
# `connector_name: StringProperty` annotation (bpy property annotations are
# declared per registered class, not inherited from the mixin). An empty
# connector_name means "the first live connector of my transport type", which
# keeps single-connection setups — and pre-0.2 files — working untouched.

from ..base import AQBaseNode
from ..connectors import resolve


class ConnectorIONode(AQBaseNode):
    connector_type_id = "MQTT"

    def get_connector(self):
        """The live connector this node talks to, or None."""
        return resolve(getattr(self, "connector_name", ""), self.connector_type_id)

    def draw_connector_selector(self, context, layout):
        """A connector picker, shown only once there's actually a choice."""
        s = getattr(context.scene, "phynodes", None)
        if s is None:
            return
        if len(s.connectors) > 1 or self.connector_name:
            layout.prop_search(self, "connector_name", s, "connectors", text="")
