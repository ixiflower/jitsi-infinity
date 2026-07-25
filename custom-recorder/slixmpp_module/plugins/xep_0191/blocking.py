
# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
import logging

from asyncio import Future

from slixmpp.stanza import Iq
from slixmpp.plugins import BasePlugin
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.matcher import StanzaPath
from slixmpp.xmlstream import register_stanza_plugin, JID
from slixmpp.plugins.xep_0191 import stanza, Block, Unblock, BlockList, BlockItem


log = logging.getLogger(__name__)

BlockedJIDs = (
    JID |
    set[JID] |
    list[JID]
)


class XEP_0191(BasePlugin):

    name = 'xep_0191'
    description = 'XEP-0191: Blocking Command'
    dependencies = {'xep_0030'}
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Iq, BlockList)
        register_stanza_plugin(Iq, Block)
        register_stanza_plugin(Iq, Unblock)
        register_stanza_plugin(BlockList, BlockItem, iterable=True)
        register_stanza_plugin(Block, BlockItem, iterable=True)
        register_stanza_plugin(Unblock, BlockItem, iterable=True)

        self.xmpp.register_handler(
                Callback('Blocked Contact',
                    StanzaPath('iq@type=set/block'),
                    self._handle_blocked))

        self.xmpp.register_handler(
                Callback('Unblocked Contact',
                    StanzaPath('iq@type=set/unblock'),
                    self._handle_unblocked))

    def plugin_end(self):
        self.xmpp.remove_handler('Blocked Contact')
        self.xmpp.remove_handler('Unblocked Contact')

    def get_blocked(self, ifrom: JID | None = None, **iqkwargs) -> Future:
        """Get the iq containing the blocklist."""
        iq = self.xmpp.make_iq_get(ifrom=ifrom)
        iq.enable('blocklist')
        return iq.send(**iqkwargs)

    async def get_blocked_jids(self, ifrom: JID | None = None, **iqkwargs) -> set[JID]:
        """Get the list of blocked JIDs."""
        iq = self.xmpp.make_iq_get(ifrom=ifrom)
        iq.enable('blocklist')
        result = await iq.send(**iqkwargs)
        return {JID(item['jid']) for item in result['blocklist']}

    def block(self, jids: BlockedJIDs,
              ifrom: JID | None = None, **iqkwargs) -> Future:
        """Block a JID or a list of JIDs.

        :param jids: JID(s) to block.
        """
        iq = self.xmpp.make_iq_set(ifrom=ifrom)
        if not isinstance(jids, (set, list)):
            jids = [jids]

        for jid in jids:
            item = BlockItem(parent=iq['block'])
            item['jid'] = jid

        return iq.send(**iqkwargs)

    def unblock(self, jids: BlockedJIDs, ifrom: JID | None = None, **iqkwargs) -> Future:
        """Unblock a JID or a list of JIDs.

        :param jids: JID(s) to unblock.
        """
        if jids is None:
            raise ValueError("jids cannot be empty.")
        iq = self.xmpp.make_iq_set(ifrom=ifrom)

        if not isinstance(jids, (set, list)):
            jids = [jids]

        for jid in jids:
            item = BlockItem(parent=iq['unblock'])
            item['jid'] = jid

        return iq.send(**iqkwargs)

    def _handle_blocked(self, iq):
        self.xmpp.event('blocked', iq)

    def _handle_unblocked(self, iq):
        self.xmpp.event('unblocked', iq)
