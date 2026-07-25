# Slixmpp: The Slick XMPP Library
# Copyright (C) 2011  Nathanael C. Fritz
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.plugins.base import register_plugin

from .limits import FeatureLimits


register_plugin(FeatureLimits)

__all__ = ['FeatureLimits']
