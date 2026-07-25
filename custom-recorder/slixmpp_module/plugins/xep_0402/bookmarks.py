from slixmpp.plugins import BasePlugin

from . import stanza


class XEP_0402(BasePlugin):

    """
    XEP-0402: PEP Native Bookmarks
    """

    name = "xep_0402"
    description = "XEP-0402: PEP Native Bookmarks"
    dependencies = {"xep_0402"}
    stanza = stanza

    def plugin_init(self):
        stanza.register_plugin()
