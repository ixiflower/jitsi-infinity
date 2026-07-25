# Slixmpp: The Slick XMPP Library
# Copyright (C) 2020 Mathieu Pasquet
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

from slixmpp import JID
from slixmpp.plugins import BasePlugin
from slixmpp.stanza import Presence
from slixmpp.xmlstream.matcher import StanzaPath
from slixmpp.xmlstream.handler import Callback

from slixmpp.plugins.xep_0437 import stanza


class XEP_0437(BasePlugin):
    """
    XEP-0437: Room Activity Indicators plugin


    Defines two events:

    - ``room_activity_bare``: useful for components receiving a subscription request.
    - ``room_activity``: when receiving a room activity.
    """
    name = 'xep_0437'
    description = 'XEP-0437: Room Activity Indicators'
    stanza = stanza
    namespace = stanza.NS

    def plugin_init(self):
        stanza.register_plugins()
        self.xmpp.register_handler(Callback(
            'RAI Received',
            StanzaPath("presence/rai"),
            self._handle_rai,
        ))
        self.xmpp.register_handler(Callback(
            'RAI Activity Received',
            StanzaPath("presence/rai/activity"),
            self._handle_rai_activity,
        ))

    def plugin_end(self):
        self.xmpp.remove_handler('RAI received')
        self.xmpp.remove_handler('RAI Activity received')

    def _handle_rai(self, presence: Presence):
        self.xmpp.event('room_activity_bare', presence)

    def _handle_rai_activity(self, presence: Presence):
        self.xmpp.event('room_activity', presence)

    def subscribe(self, service: JID, *,
                  pfrom: JID | None = None):
        """
        Subscribe to room activity on a MUC service.

        :param JID service: MUC service
        :param pfrom: JID the subscribe request is sent from (for components).
        """
        pres = self.xmpp.make_presence(pto=service, pfrom=pfrom)
        pres.enable('rai')
        pres.send()

    def unsubscribe(self, service: JID, *,
                    pfrom: JID | None = None):
        """
        Unsubscribe from room activity on a MUC service.

        :param service: MUC service.
        :param pfrom: JID the unsubscribe request is sent from (for components).
        """
        pres = self.xmpp.make_presence(
            pto=service, pfrom=pfrom, ptype='unavailable',
        )
        pres.send()
