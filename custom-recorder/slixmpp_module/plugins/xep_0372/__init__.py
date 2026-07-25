from slixmpp.plugins.base import register_plugin

from . import stanza
from .references import XEP_0372

register_plugin(XEP_0372)

__all__ = ['stanza', 'XEP_0372']
