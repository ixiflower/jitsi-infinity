# Slixmpp: The Slick XMPP Library
# Copyright (C) 2011  Nathanael C. Fritz
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
import logging
from typing import TYPE_CHECKING, ClassVar, NamedTuple

from slixmpp.plugins import BasePlugin
from slixmpp.stanza import StreamFeatures
from slixmpp.xmlstream import register_stanza_plugin

from . import stanza

if TYPE_CHECKING:
    from slixmpp.clientxmpp import ClientXMPP


class FeatureLimits(BasePlugin):
    xmpp: "ClientXMPP"
    name = "feature_limits"
    description = "XEP-0478: Stream Limits Advertisement"
    dependencies: ClassVar[set[str]] = set()
    stanza = stanza

    def plugin_init(self):
        if self.xmpp.is_component:
            raise RuntimeError("Stream limits does not work with XEP-0114")

        self.xmpp.register_feature(
            "limits", self._handle_limits, restart=False, order=10000
        )

        register_stanza_plugin(StreamFeatures, stanza.Limits)

    async def _handle_limits(self, features: StreamFeatures):
        self.xmpp.limits = Limits(
            _attempt_int(features["limits"]["max-bytes"]),
            _attempt_int(features["limits"]["idle-seconds"]),
        )


class Limits(NamedTuple):
    max_bytes: int | None = None
    idle_seconds: int | None = None


def _attempt_int(val: str) -> int | None:
    if not val:
        return None
    try:
        return int(val)
    except ValueError:
        log.warning("Received an invalid stream limit value: %s", val)
        return None


log = logging.getLogger(__name__)
