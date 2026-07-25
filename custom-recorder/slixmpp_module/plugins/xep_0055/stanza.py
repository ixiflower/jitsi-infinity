from typing import ClassVar

from slixmpp.xmlstream import ElementBase


class Search(ElementBase):
    namespace = "jabber:iq:search"
    name = "query"
    plugin_attrib = "search"
    interfaces: ClassVar[set[str]] = set()
