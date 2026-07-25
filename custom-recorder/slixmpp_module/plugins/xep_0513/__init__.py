# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

from slixmpp.plugins.base import register_plugin

from .mentions import XEP_0513

register_plugin(XEP_0513)

__all__ = ['XEP_0513']
