"""
Stanza interfaces for XEP-0513: Explicit Mentions

Basic usage:

>>> register_plugin()  # automatically done if you use this plugin
>>> msg = Message()
>>> msg["body"] = "Hello, Alice!"
>>> msg["mention"]["begin"] = 7
>>> msg["mention"]["end"] = 12
>>> msg["mention"]["occupantid"] = "alice@occupant-id"
>>> msg.pretty_print()
<message xmlns="jabber:client">
  <body>Hello, Alice!</body>
  <mention xmlns="urn:xmpp:mentions:0" begin="7" end="12" occupantid="alice@occupant-id" />
</message>
"""

# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

import logging
from typing import Literal

from slixmpp.jid import JID, InvalidJID
from slixmpp.stanza.message import Message
from slixmpp.xmlstream import ElementBase, register_stanza_plugin

GroupMentionLiteral = Literal[
    "channel",
    "space",
    "server",
    "moderators",
    "participants",
    "visitors",
    "owner",
    "admin",
    "member",
    "none",
]


NAMESPACE = "urn:xmpp:mentions:0"


class Mention(ElementBase):
    name = "mention"
    namespace = NAMESPACE
    plugin_attrib = "mention"
    plugin_multi_attrib = "mentions"
    interfaces = {
        "begin",
        "end",
        "occupantid",
        "jid",
        "mentions",
        "uri",
    }

    def set_begin(self, begin: int) -> None:
        self._set_attr("begin", str(begin))

    def get_begin(self) -> int | None:
        return _int_or_none(self._get_attr("begin"))

    def set_end(self, end: int) -> None:
        self._set_attr("end", str(end))

    def get_end(self) -> int | None:
        return _int_or_none(self._get_attr("end"))

    def mention_group(self, who: GroupMentionLiteral) -> None:
        """
        Mention a group of participants, see section 3.2 of the XEP.
        """
        self._set_attr("mentions", f"{self.namespace}#{who}")

    def set_jid(self, jid: JID | str) -> None:
        self._set_attr("jid", str(jid))

    def get_jid(self) -> JID | None:
        jid_str = self._get_attr("jid")
        if not jid_str:
            return None
        try:
            return JID(jid_str)
        except InvalidJID:
            log.warning("Failed to parse %s as a JID", jid_str)
            return None


class Active(ElementBase):
    namespace = NAMESPACE
    name = plugin_attrib = "active"


class NoPing(ElementBase):
    namespace = NAMESPACE
    name = plugin_attrib = "noping"


def _int_or_none(v: str | None) -> int | None:
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        log.warning("Failed to parse %s as an integer", v)
        return None


def register_plugin() -> None:
    register_stanza_plugin(Message, Mention, iterable=True)
    register_stanza_plugin(Mention, NoPing, iterable=True)
    register_stanza_plugin(Mention, Active, iterable=True)


log = logging.getLogger(__name__)
