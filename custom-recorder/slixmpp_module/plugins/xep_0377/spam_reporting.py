
# Slixmpp: The Slick XMPP Library
# Copyright (C) 2020 Mathieu Pasquet
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
import logging

from asyncio import Future
from typing import (
    Literal,
)

from slixmpp.jid import JID
from slixmpp.plugins import BasePlugin
from slixmpp.xmlstream import register_stanza_plugin
from slixmpp.plugins.xep_0377 import stanza
from slixmpp.plugins.xep_0191 import BlockItem


log = logging.getLogger(__name__)

BlockedJIDs = (
    JID |
    set[JID] |
    list[JID]
)

class XEP_0377(BasePlugin):
    """XEP-0377: Spam reporting"""

    name = 'xep_0377'
    description = 'XEP-0377: Spam Reporting'
    dependencies = {'xep_0030', 'xep_0191'}
    stanza = stanza

    SPAM = 'urn:xmpp:reporting:spam'
    ABUSE = 'urn:xmpp:reporting:abuse'

    def plugin_init(self):
        register_stanza_plugin(BlockItem, stanza.Report)
        register_stanza_plugin(stanza.Report, stanza.Text)

    def plugin_end(self):
        self.xmpp.plugin['xep_0030'].del_feature(feature=stanza.Report.namespace)

    def session_bind(self, jid):
        self.xmpp.plugin['xep_0030'].add_feature(stanza.Report.namespace)

    def report(self,
        jids: BlockedJIDs,
        reason: Literal['spam', 'abuse'] = 'spam',
        ifrom: JID | None = None,
        **iqkwargs,
    ) -> Future:
        """Report a JID or a list of JIDs.

        :param jids: JID(s) to block.
        """
        iq = self.xmpp.make_iq_set(ifrom=ifrom)
        if not isinstance(jids, (set, list)):
            jids = [jids]

        for jid in jids:
            item = BlockItem(parent=iq['block'])
            item['jid'] = jid
            if reason == 'spam':
                item['report']['reason'] = self.SPAM
            else:
                item['report']['reason'] = self.ABUSE

        return iq.send(**iqkwargs)
