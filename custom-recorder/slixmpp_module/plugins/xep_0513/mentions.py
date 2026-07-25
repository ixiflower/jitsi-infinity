# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.plugins import BasePlugin
from slixmpp.xmlstream import StanzaBase
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.matcher import StanzaPath

from . import stanza


class XEP_0513(BasePlugin):
    """
    This plugin add supports for XEP-0513: Explicit Mentions

    """

    name = "xep_0513"
    description = "XEP-0513: Explicit Mentions"
    dependencies = set()
    stanza = stanza

    def plugin_init(self) -> None:
        stanza.register_plugin()
        self.xmpp.register_handler(
            Callback(
                "Explicit Mentions", StanzaPath("message/mention"), self._handle_mention
            )
        )

    def plugin_end(self):
        self.xmpp.remove_handler("Explicit Mentions")

    def _handle_mention(self, msg: StanzaBase) -> None:
        self.xmpp.event("mention", msg)
