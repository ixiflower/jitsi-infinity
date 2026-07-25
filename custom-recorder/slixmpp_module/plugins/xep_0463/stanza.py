# Slixmpp: The Slick XMPP Library
# Copyright © 2026 nicoco <nicoco@nicoco.fr>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

"""
Usage:

>>> register_plugin(for_doctests=True)  # automatically done when enabling the XEP_0463 plugin
>>> presence = Presence()
>>> presence["muc_join"]["mav"]["since"] = "opaque-ver"
>>> presence.pretty_print()
<presence xmlns="jabber:client">
  <x xmlns="http://jabber.org/protocol/muc">
    <mav xmlns="urn:xmpp:muc:affiliations:1" since="opaque-ver" />
  </x>
</presence>

>>> msg = Message()
>>> msg["muc"]["mav"]["since"] = "since-ver"
>>> msg["muc"]["mav"]["until"] = "until-ver"
>>> msg.pretty_print()
<message xmlns="jabber:client">
  <x xmlns="http://jabber.org/protocol/muc#user">
    <mav xmlns="urn:xmpp:muc:affiliations:1" since="since-ver" until="until-ver" />
  </x>
</message>

>>> presence = Presence()
>>> presence["muc"]["mav"]["until"] = "XXX"
>>> presence.pretty_print()
<presence xmlns="jabber:client">
  <x xmlns="http://jabber.org/protocol/muc#user">
    <mav xmlns="urn:xmpp:muc:affiliations:1" until="XXX" />
  </x>
</presence>
"""

from slixmpp import Message, Presence
from slixmpp.plugins.xep_0045.stanza import MUCBase, MUCJoin, MUCPresence, MUCMessage
from slixmpp.xmlstream import ElementBase, register_stanza_plugin

NS = "urn:xmpp:muc:affiliations:1"


class Mav(ElementBase):
    namespace = NS
    name = "mav"
    plugin_attrib = "mav"
    interfaces = {"until", "since"}


def register_plugin(for_doctests=False) -> None:
    if for_doctests:
        register_stanza_plugin(Presence, MUCJoin)
        register_stanza_plugin(Presence, MUCBase)
        register_stanza_plugin(Presence, MUCPresence)
        register_stanza_plugin(Message, MUCMessage)
    register_stanza_plugin(MUCJoin, Mav)
    register_stanza_plugin(MUCBase, Mav)
    register_stanza_plugin(MUCMessage, Mav)
    register_stanza_plugin(MUCPresence, Mav)
