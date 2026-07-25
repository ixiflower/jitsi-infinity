# Slixmpp: The Slick XMPP Library
# Copyright © 2026 nicoco <nicoco@nicoco.fr>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

from slixmpp.plugins.base import register_plugin

from . import stanza
from .mav import XEP_0463

register_plugin(XEP_0463)

__all__ = ("stanza", "XEP_0463")
