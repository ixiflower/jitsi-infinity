# Slixmpp: The Slick XMPP Library
# Copyright (C) 2025 Mathieu Pasquet
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

from slixmpp.plugins.base import register_plugin

from .muc_activity import XEP_0502

register_plugin(XEP_0502)

__all__ = ["XEP_0502"]
