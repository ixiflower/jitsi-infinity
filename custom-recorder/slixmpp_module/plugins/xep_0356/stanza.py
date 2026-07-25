from __future__ import annotations

from typing import ClassVar, Literal, overload

from slixmpp.plugins.xep_0297 import Forwarded
from slixmpp.stanza import Iq, Message
from slixmpp.xmlstream import ElementBase, register_stanza_plugin

NS = "urn:xmpp:privilege:2"


class Privilege(ElementBase):
    namespace = NS
    name = "privilege"
    plugin_attrib = "privilege"

    def permission(self, access: str) -> str | None:
        for perm in self["perms"]:
            if perm["access"] == access:
                return perm["type"]
        return None

    def roster(self) -> str | None:
        return self.permission("roster")

    def message(self) -> str | None:
        return self.permission("message")

    def presence(self) -> str | None:
        return self.permission("presence")

    @overload
    def add_perm(
        self, access: Literal["roster"], type_: Literal["none", "get", "set", "both"]
    ) -> None: ...

    @overload
    def add_perm(
        self, access: Literal["message"], type_: Literal["none", "outgoing"]
    ) -> None: ...

    @overload
    def add_perm(
        self, access: Literal["iq"], type_: Literal["none", "get", "set", "both"]
    ) -> None: ...

    @overload
    def add_perm(
        self,
        access: Literal["presence"],
        type_: Literal["none", "managed_entity", "roster"],
    ) -> None: ...

    def add_perm(
        self,
        access: Literal["roster", "message", "presence", "iq"],
        type_: Literal[
            "both", "get", "set", "none", "outgoing", "managed_entity", "roster"
        ],
    ) -> None:
        # This should only be needed for servers, so maybe out of scope for slixmpp
        perm = Perm()
        perm["type"] = type_
        perm["access"] = access
        self.append(perm)


class Perm(ElementBase):
    namespace = NS
    name = "perm"
    plugin_attrib = "perm"
    plugin_multi_attrib = "perms"
    interfaces: ClassVar[set[str]] = {"type", "access"}


class NameSpace(ElementBase):
    namespace = NS
    name = "namespace"
    plugin_attrib = "namespace"
    plugin_multi_attrib = "namespaces"
    interfaces: ClassVar[set[str]] = {"ns", "type"}


class PrivilegedIq(ElementBase):
    namespace = NS
    name = "privileged_iq"
    plugin_attrib = "privileged_iq"


def register() -> None:
    register_stanza_plugin(Message, Privilege)
    register_stanza_plugin(Iq, Privilege)
    register_stanza_plugin(Privilege, Forwarded)
    register_stanza_plugin(Privilege, Perm, iterable=True)
    register_stanza_plugin(Perm, NameSpace, iterable=True)
    register_stanza_plugin(Iq, PrivilegedIq)
