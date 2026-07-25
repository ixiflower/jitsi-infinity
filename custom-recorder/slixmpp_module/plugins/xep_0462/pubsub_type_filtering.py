from slixmpp.plugins import BasePlugin

from . import stanza


class XEP_0462(BasePlugin):
    """
    XEP-0462: PubSub Type Filtering

    This plugin makes it possible to filter pubsub items based on their types
    in disco#items queries.

    Registering the plugin sets the disco feature, and registers stanza plugins.
    """

    name = "xep_0462"
    description = "XEP-0462: PubSub Type Filtering"
    dependencies = {"xep_0004", "xep_0030"}
    stanza = stanza

    def plugin_init(self) -> None:
        stanza.register_plugin()
        self.xmpp.plugin["xep_0030"].add_feature(stanza.NS)

    def plugin_end(self):
        self.xmpp.plugin["xep_0030"].del_feature(stanza.NS)
