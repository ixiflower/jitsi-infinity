# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

from slixmpp.plugins.base import register_plugin

from .link_metadata import XEP_0511

register_plugin(XEP_0511)

__all__ = ['XEP_0511']
