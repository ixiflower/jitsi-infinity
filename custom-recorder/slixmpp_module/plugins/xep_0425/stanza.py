
# Slixmpp: The Slick XMPP Library
# Copyright (C) 2020 Mathieu Pasquet <mathieui@mathieui.net>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission
from slixmpp.stanza import Iq
from slixmpp.xmlstream import (
    ElementBase,
    register_stanza_plugin,
)
from slixmpp.plugins.xep_0421.stanza import OccupantId
from slixmpp.plugins.xep_0424.stanza import Retract, Retracted


NS = 'urn:xmpp:message-moderate:1'


class Moderate(ElementBase):
    """
    Moderate request element.

    .. code-block:: xml

          <moderate id="stanza-id-1" xmlns='urn:xmpp:message-moderate:1'>
            <retract xmlns='urn:xmpp:message-retract:1'/>
            <reason>This message contains inappropriate content for this forum</reason>
          </moderate>

    """
    namespace = NS
    name = 'moderate'
    plugin_attrib = 'moderate'
    interfaces = {'id', 'reason'}
    sub_interfaces = {'reason'}


class Moderated(ElementBase):
    """
    Moderated message notification element.

    .. code-block:: xml

        <moderated by='room@muc.example.com/macbeth' xmlns='urn:xmpp:message-moderate:1'>
          <occupant-id xmlns="urn:xmpp:occupant-id:0" id="dd72603deec90a38ba552f7c68cbcc61bca202cd" />
        </moderated>

    """
    namespace = NS
    name = 'moderated'
    plugin_attrib = 'moderated'
    interfaces = {'by'}


def register_plugins():
    # for moderation requests
    register_stanza_plugin(Iq, Moderate)
    register_stanza_plugin(Moderate, Retract)

    # for moderation events
    register_stanza_plugin(Retract, Moderated)
    register_stanza_plugin(Moderated, OccupantId)

    # for tombstones
    register_stanza_plugin(Retracted, Moderated)
