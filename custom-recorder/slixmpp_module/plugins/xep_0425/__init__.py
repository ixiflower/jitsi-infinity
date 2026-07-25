# Slixmpp: The Slick XMPP Library
# Copyright (C) 2020 Mathieu Pasquet <mathieui@mathieui.net>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.plugins.base import register_plugin
from slixmpp.plugins.xep_0425.stanza import Moderate, Moderated
from slixmpp.plugins.xep_0425.moderation import XEP_0425

register_plugin(XEP_0425)

__all__ = ['Moderate', 'Moderated', 'XEP_0425']
