# Slixmpp: The Slick XMPP Library
# Copyright (C) 2020 Mathieu Pasquet <mathieui@mathieui.net>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.plugins.base import register_plugin
from slixmpp.plugins.xep_0403.stanza import MIXPresence
from slixmpp.plugins.xep_0403.mix_presence import XEP_0403

register_plugin(XEP_0403)

__all__ = ['MIXPresence', 'XEP_0403']
