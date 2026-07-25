# Slixmpp: The Slick XMPP Library
# Copyright © 2026 nicoco <nicoco@nicoco.fr>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

from slixmpp.plugins import BasePlugin

from . import stanza


class XEP_0463(BasePlugin):
    """
    XEP-0463: MUC Affiliation Versioning

    This plugin does only one thing: it registers the stanza plugins.
    """

    name = "xep_0463"
    description = "XEP-0463: MUC Affiliation Versioning"
    dependencies = {"xep_0045"}
    stanza = stanza

    def plugin_init(self) -> None:
        stanza.register_plugin()
