# Copyright © 2025 Mathieu Pasquet
# This file is part of slixmpp
# See the file LICENSE for copying permission.

from slixmpp.plugins.base import register_plugin
from .sos import XEP_0455, ExternalStatus


register_plugin(XEP_0455)

__all__ = ['XEP_0455', 'ExternalStatus']
