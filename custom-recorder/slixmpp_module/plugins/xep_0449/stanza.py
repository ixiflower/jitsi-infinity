"""
Stanza interfaces for XEP-0449: Stickers

Basic usage:

>>> register()  # automatically done if you use this plugin
>>> msg = Message()
>>> msg["sticker"]["pack"] = "some-pack-id"
>>> msg.pretty_print()
<message xmlns="jabber:client">
  <sticker xmlns="urn:xmpp:stickers:0" pack="some-pack-id" />
</message>

You are supposed to also add a Stateless File Sharing payload if you do that.
"""

from slixmpp import JID, InvalidJID, Message
from slixmpp.types import JidStr
from slixmpp.xmlstream import ElementBase, register_stanza_plugin

NAMESPACE = "urn:xmpp:stickers:0"


class Sticker(ElementBase):
    name = "sticker"
    plugin_attrib = "sticker"
    namespace = NAMESPACE
    interfaces = {"pack", "jid", "node"}

    def get_jid(self) -> JID | None:
        try:
            return JID(self._get_attr("jid"))
        except InvalidJID:
            return None

    def set_jid(self, jid: JidStr) -> None:
        self._set_attr("jid", str(jid))


def register() -> None:
    register_stanza_plugin(Message, Sticker)
