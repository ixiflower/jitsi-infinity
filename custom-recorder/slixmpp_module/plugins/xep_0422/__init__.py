# Slixmpp: The Slick XMPP Library
# Copyright (C) 2020 Mathieu Pasquet <mathieui@mathieui.net>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.plugins.base import register_plugin
from slixmpp.plugins.xep_0422.stanza import ApplyTo, External
from slixmpp.plugins.xep_0422.fastening import XEP_0422

register_plugin(XEP_0422)

__all__ = ['ApplyTo', 'External', 'XEP_0422']
