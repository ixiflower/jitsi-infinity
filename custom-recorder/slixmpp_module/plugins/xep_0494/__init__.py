# Slixmpp: The Slick XMPP Library
# Copyright (C) 2025 Mathieu Pasquet
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

from slixmpp.plugins.base import register_plugin

from . import stanza
from .cam import XEP_0494
from .stanza import ClientType, PermissionEnum, Client

register_plugin(XEP_0494)

__all__ = ["XEP_0494", "Client", "ClientType", "PermissionEnum", "stanza"]
