import logging

from slixmpp import Message
from slixmpp.plugins import BasePlugin
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.matcher import StanzaPath

from . import stanza

log = logging.getLogger(__name__)


class XEP_0449(BasePlugin):
    """
    XEP-0449: Stickers

    Raises an event on incoming stickers.
    Nothing related to sticker packs is supported (yet).
    """

    name = "xep_0449"
    description = "XEP-0449: Stickers"
    dependencies = {"xep_0449"}
    stanza = stanza

    def plugin_init(self) -> None:
        stanza.register()
        self.xmpp.register_handler(
            Callback(
                "Sticker received",
                StanzaPath("message/sticker"),
                self._handle_sticker,
            )
        )

    def plugin_end(self) -> None:
        self.xmpp.remove_handler("Sticker received")

    def _handle_sticker(self, msg: Message) -> None:
        self.xmpp.event("sticker", msg)
