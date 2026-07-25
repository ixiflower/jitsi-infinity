
# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.xmlstream import ElementBase


class BlockList(ElementBase):
    name = 'blocklist'
    namespace = 'urn:xmpp:blocking'
    plugin_attrib = 'blocklist'


class Block(BlockList):
    name = 'block'
    plugin_attrib = 'block'


class Unblock(BlockList):
    name = 'unblock'
    plugin_attrib = 'unblock'


class BlockItem(ElementBase):
    name = 'item'
    namespace = 'urn:xmpp:blocking'
    plugin_attrib = 'item'
    plugin_multi_attrib = 'items'
    interfaces = {'jid'}
