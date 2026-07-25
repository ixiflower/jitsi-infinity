import warnings
from typing import Iterable

from slixmpp import Presence
from slixmpp.types import HatTuple
from slixmpp.xmlstream import ElementBase, register_stanza_plugin

NS = 'urn:xmpp:hats:0'


class Hats(ElementBase):
    """
    Hats element, container for multiple hats:

    .. code-block::xml


      <hats xmlns='urn:xmpp:hats:0'>
        <hat title='Host' uri='http://schemas.example.com/hats#host' xml:lang='en-us'>
            <badge xmlns="urn:example:badges" fgcolor="#000000" bgcolor="#58C5BA"/>
        </hat>
        <hat title='Presenter' uri='http://schemas.example.com/hats#presenter' xml:lang='en-us'>
            <badge xmlns="urn:example:badges" fgcolor="#000000" bgcolor="#EC0524"/>
        </hat>
      </hats>

    """

    name = 'hats'
    namespace = NS
    plugin_attrib = 'hats'

    def add_hats(self, hats: Iterable[HatTuple | tuple[str, str, float]]) -> None:
        for uri, title, hue in hats:
            hat = Hat()
            hat["uri"] = uri
            hat["title"] = title
            if hue is not None:
                hat["hue"] = hue
            self.append(hat)


class Hat(ElementBase):
    """
    Hat element, has a title and url, may contain arbitrary sub-elements.

    .. code-block::xml

        <hat title='Host' uri='http://schemas.example.com/hats#host' xml:lang='en-us'>
            <badge xmlns="urn:example:badges" fgcolor="#000000" bgcolor="#58C5BA"/>
        </hat>

    """
    name = 'hat'
    plugin_attrib = 'hat'
    namespace = NS
    interfaces = {'title', 'uri', 'hue'}
    plugin_multi_attrib = "hats"

    def set_hue(self, hue: float) -> None:
        self._set_attr("hue", str(hue))

    def get_hue(self) -> float | None:
        hue = self._get_attr("hue",)
        try:
            return None if hue == "" else float(hue)
        except ValueError:
            warnings.warn(f"Not a valid hue value: {hue}")
            return None


def register_plugin() -> None:
    register_stanza_plugin(Hats, Hat, iterable=True)
    register_stanza_plugin(Presence, Hats)
