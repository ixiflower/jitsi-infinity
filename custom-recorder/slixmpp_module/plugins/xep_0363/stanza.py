# slixmpp: The Slick XMPP Library
# Copyright (C) 2018 Emmanuel Gil Peyrot
# This file is part of slixmpp.
# See the file LICENSE for copying permission.
from typing import ClassVar

from slixmpp.xmlstream import ElementBase


class Request(ElementBase):
    plugin_attrib = "http_upload_request"
    name = "request"
    namespace = "urn:xmpp:http:upload:0"
    interfaces: ClassVar[set[str]] = {"filename", "size", "content-type"}


class Slot(ElementBase):
    plugin_attrib = "http_upload_slot"
    name = "slot"
    namespace = "urn:xmpp:http:upload:0"


class Put(ElementBase):
    plugin_attrib = "put"
    name = "put"
    namespace = "urn:xmpp:http:upload:0"
    interfaces: ClassVar[set[str]] = {"url"}


class Get(ElementBase):
    plugin_attrib = "get"
    name = "get"
    namespace = "urn:xmpp:http:upload:0"
    interfaces: ClassVar[set[str]] = {"url"}


class Header(ElementBase):
    plugin_attrib = "header"
    name = "header"
    namespace = "urn:xmpp:http:upload:0"
    plugin_multi_attrib = "headers"
    interfaces: ClassVar[set[str]] = {"name", "value"}

    def get_value(self) -> str | None:
        return self.xml.text

    def set_value(self, value: str) -> None:
        self.xml.text = value

    def del_value(self) -> None:
        self.xml.text = ""


PURPOSE_NAMESPACE = "urn:xmpp:http:upload:purpose:0"


class MessagePurpose(ElementBase):
    namespace = PURPOSE_NAMESPACE
    plugin_attrib = name = "message"


class ProfilePurpose(ElementBase):
    namespace = PURPOSE_NAMESPACE
    plugin_attrib = name = "profile"


class EphemeralPurpose(ElementBase):
    namespace = PURPOSE_NAMESPACE
    plugin_attrib = name = "ephemeral"


class PermanentPurpose(ElementBase):
    namespace = PURPOSE_NAMESPACE
    plugin_attrib = name = "permanent"
