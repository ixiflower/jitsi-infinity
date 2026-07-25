from slixmpp import register_stanza_plugin
from slixmpp.plugins.xep_0060.stanza import Item
from slixmpp.xmlstream import ElementBase
from slixmpp.plugins.xep_0359.stanza import StanzaID

NS = "urn:xmpp:mds:displayed:0"


class Displayed(ElementBase):
    """
    Displayed element.

    .. code-block:: xml

        <displayed xmlns='urn:xmpp:mds:displayed:0'>
          <stanza-id xmlns='urn:xmpp:sid:0'
                     id='ca21deaf-812c-48f1-8f16-339a674f2864'
                     by='example@conference.shakespeare.lit'/>
        </displayed>
    """
    namespace = NS
    name = "displayed"
    plugin_attrib = "displayed"


def register_plugin():
    register_stanza_plugin(Displayed, StanzaID)
    register_stanza_plugin(Item, Displayed)
