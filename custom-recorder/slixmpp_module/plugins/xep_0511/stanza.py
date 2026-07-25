"""
Stanza interfaces for XEP-0511: Link Metadata

Usage:

>>> register_plugin()  # automatically done if you use this plugin
>>> msg = Message()
>>> msg["link_metadata"]["about"] = "https://the.link.example.com/what-was-linked-to"
>>> msg["link_metadata"]["title"] = "A cool title"
>>> msg.pretty_print()
<message xmlns="jabber:client">
  <Description xmlns="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" rdf:about="https://the.link.example.com/what-was-linked-to">
    <title xmlns="https://ogp.me/ns#">A cool title</title>
  </Description>
</message>
"""

# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.


from slixmpp.stanza.message import Message
from slixmpp.xmlstream import ElementBase, register_stanza_plugin

RDF_NAMESPACE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
OG_NAMESPACE = "https://ogp.me/ns#"


class LinkMetadata(ElementBase):
    name = "Description"
    namespace = RDF_NAMESPACE
    plugin_attrib = "link_metadata"
    plugin_multi_attrib = "link_metadatas"
    interfaces = {"about", "title", "description", "url", "image", "type", "site_name"}

    def _set_og(self, el: ElementBase, value: str) -> None:
        el.xml.text = value
        self.xml.append(el.xml)

    def _get_og(self, el: type[ElementBase]) -> str | None:
        child = self.xml.find(f"{{{el.namespace}}}{el.name}")
        if child is None:
            return None
        return child.text

    def set_title(self, v: str) -> None:
        self._set_og(Title(), v)

    def get_title(self) -> str | None:
        return self._get_og(Title)

    def set_description(self, v: str) -> None:
        self._set_og(Description(), v)

    def get_description(self) -> str | None:
        return self._get_og(Description)

    def set_url(self, v: str) -> None:
        self._set_og(Url(), v)

    def get_url(self) -> str | None:
        return self._get_og(Url)

    def set_image(self, v: str) -> None:
        self._set_og(Image(), v)

    def get_image(self) -> str | None:
        return self._get_og(Image)

    def set_type(self, v: str) -> None:
        self._set_og(Type_(), v)

    def get_type(self) -> str | None:
        return self._get_og(Type_)

    def set_site_name(self, v: str) -> None:
        self._set_og(SiteName(), v)

    def get_site_name(self) -> str | None:
        return self._get_og(SiteName)

    # The following methods look overly complex, but I did not find anything better.
    # Maybe the following snippet helps understand what ElementBase does that breaks
    # the expected behaviour of get().
    # >>> msg = ET.Element("{jabber:client}message")
    # >>> desc = ET.Element("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description")
    # >>> desc.set("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", "link")
    # >>> msg.append(desc)
    # >>> print(ET.tostring(msg, 'unicode'))
    # <ns0:message xmlns:ns0="jabber:client" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    #   <rdf:Description rdf:about="link" />
    # </ns0:message>
    # The "rdf" prefix is automagically set because it is listed as a well-known prefix in python's stdlib `xml.etree`.

    def get_about(self) -> str | None:
        about = self.xml.get(f"{{{RDF_NAMESPACE}}}about")
        if about is not None:
            return about

        # When we set 'about' using set_about() below, the code above does not work.
        # Handling prefix definitions manually is the best I could come up with.
        for attrib, value in self.xml.attrib.items():
            if attrib.startswith("xmlns:") and value == RDF_NAMESPACE:
                prefix = attrib.removeprefix("xmlns:")
                return self.xml.get(f"{prefix}:about")

        return None

    def set_about(self, about: str) -> None:
        # If we use…
        # self.xml.set(f"{{{RDF_NAMESPACE}}}about", about)
        # …the about attrib is not visible in the output of ET.tostring().
        # It is a problem, since this is what we send in the stream.
        # It is probably due to some special handling of namespaces in ElementBase.
        # The following workaround seems to be OK…
        self.xml.set("xmlns:rdf", RDF_NAMESPACE)
        self.xml.set("rdf:about", about)


class _OpenGraphMixin(ElementBase):
    namespace = OG_NAMESPACE


class Title(_OpenGraphMixin):
    name = plugin_attrib = "title"


class Description(_OpenGraphMixin):
    name = plugin_attrib = "description"


class Url(_OpenGraphMixin):
    name = plugin_attrib = "url"


class Image(_OpenGraphMixin):
    name = plugin_attrib = "image"


class Type_(_OpenGraphMixin):
    name = plugin_attrib = "type"


class SiteName(_OpenGraphMixin):
    name = plugin_attrib = "site_name"


def register_plugin() -> None:
    for plugin in Title, Description, Url, Image, Type_, SiteName:
        register_stanza_plugin(LinkMetadata, plugin)
    register_stanza_plugin(Message, LinkMetadata, iterable=True)
