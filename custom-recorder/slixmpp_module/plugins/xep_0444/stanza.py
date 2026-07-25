# Slixmpp: The Slick XMPP Library
# Copyright (C) 2020 Mathieu Pasquet
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from collections.abc import Iterable
from typing import ClassVar

from slixmpp.xmlstream import ElementBase

try:
    from emoji import is_emoji
except ImportError:

    def is_emoji(string: str) -> bool:
        return True


NS = "urn:xmpp:reactions:0"


class Reactions(ElementBase):
    """
    Reactions element.

    .. code-block:: xml

        <reactions id='744f6e18-a57a-11e9-a656-4889e7820c76' xmlns='urn:xmpp:reactions:0'>
          <reaction>👋</reaction>
          <reaction>🐢</reaction>
        </reactions>
    """

    name = "reactions"
    plugin_attrib = "reactions"
    namespace = NS
    interfaces: ClassVar[set[str]] = {"id", "values"}

    def get_values(self, *, all_chars: bool = False) -> set[str]:
        """ "Get all reactions as str"""
        reactions = set()
        for reaction in self:
            value = reaction["value"]
            if all_chars or is_emoji(value):
                reactions.add(reaction["value"])
        return reactions

    def set_values(self, values: Iterable[str], *, all_chars: bool = False) -> None:
        """ "Set all reactions as str"""
        for element in self.xml.findall("reaction"):
            self.xml.remove(element)
        for reaction_txt in values:
            reaction = Reaction()
            reaction.set_value(reaction_txt, all_chars=all_chars)
            self.append(reaction)


class Reaction(ElementBase):
    """
    Single reaction element.

    .. code-block:: xml

        <reaction>💜</reaction>
    """

    name = "reaction"
    namespace = NS
    interfaces: ClassVar[set[str]] = {"value"}

    def get_value(self) -> str | None:
        return self.xml.text

    def set_value(self, value: str, *, all_chars: bool = False) -> None:
        if not all_chars and not is_emoji(value):
            raise ValueError(f"{value} is not a valid emoji")
        self.xml.text = value
