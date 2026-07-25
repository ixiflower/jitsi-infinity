# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.plugins import BasePlugin

from . import stanza


class XEP_0511(BasePlugin):
    """
    This plugin add supports for XEP-0511: Link Metadata.

    It does not register any stream handler, it just registers stanza interfaces.
    """

    name = "xep_0511"
    description = "XEP-0511: Link Metadata"
    dependencies = set()
    stanza = stanza

    def plugin_init(self) -> None:
        stanza.register_plugin()
