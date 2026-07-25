"""
Usage:

>>> from slixmpp import Iq
>>> register_stanza_plugin(Iq, DiscoItems)  # automatically done when loading
>>> register_plugin()                       # the XEP_0462 plugin
>>> iq = Iq()
>>> iq["disco_items"]["filter"]["included_types"] = ["type1", "type2"]
>>> iq.pretty_print()
<iq xmlns="jabber:client" id="0">
  <query xmlns="http://jabber.org/protocol/disco#items">
    <filter xmlns="urn:xmpp:pubsub-filter:0">
      <x xmlns="jabber:x:data" type="submit">
        <field var="FORM_TYPE" type="hidden">
          <value>urn:xmpp:pubsub-filter:0</value>
        </field>
        <field var="included-types">
          <value>type1</value>
          <value>type2</value>
        </field>
      </x>
    </filter>
  </query>
</iq>
>>> iq["disco_items"]["filter"]["included_types"]
['type1', 'type2']

And similarly, an "excluded_types" interface is present.
"""

from slixmpp.plugins.xep_0004 import Form
from slixmpp.plugins.xep_0030.stanza.items import DiscoItems
from slixmpp.xmlstream import ElementBase, register_stanza_plugin

NS = "urn:xmpp:pubsub-filter:0"


class Filter(ElementBase):
    namespace = NS
    name = "filter"
    plugin_attrib = "filter"
    interfaces = {"included_types", "excluded_types"}

    def set_included_types(self, types: list[str]) -> None:
        self.__set("in", types)

    def get_included_types(self) -> list[str]:
        return self.__get("in")

    def set_excluded_types(self, types: list[str]) -> None:
        self.__set("ex", types)

    def get_excluded_types(self) -> list[str]:
        return self.__get("ex")

    def __get(self, what: str) -> list[str]:
        try:
            return self["form"].field[f"{what}cluded-types"].values["value"]
        except KeyError:
            return []

    def __set(self, what: str, types: list[str]) -> None:
        if self.get_plugin("form", check=True):
            form: Form = self["form"]
            if f"{what}cluded-types" in form.field:
                form.field[f"{what}cluded-types"]["value"] = types
            else:
                form.add_field(
                    var="{what}cluded-types",
                    ftype="list-multi",
                    value=types,
                )
        else:
            form: Form = self["form"]
            form["type"] = "submit"
            form.add_field(var="FORM_TYPE", ftype="hidden", value=NS)
            form.add_field(
                var=f"{what}cluded-types",
                ftype="list-multi",
                value=types,
            )


def register_plugin():
    register_stanza_plugin(DiscoItems, Filter)
    register_stanza_plugin(Filter, Form)
