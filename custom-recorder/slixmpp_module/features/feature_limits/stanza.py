
# Slixmpp: The Slick XMPP Library
# Copyright (C) 2011  Nathanael C. Fritz
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.xmlstream import ElementBase


class Limits(ElementBase):
    name = 'limits'
    plugin_attrib = 'limits'
    namespace = 'urn:xmpp:stream-limits:0'
    interfaces = {'max-bytes', 'idle-seconds'}
    sub_interfaces = interfaces
