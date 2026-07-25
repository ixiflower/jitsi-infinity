from slixmpp.plugins.base import register_plugin

from . import stanza
from .pubsub_type_filtering import XEP_0462

register_plugin(XEP_0462)

__all__ = ("stanza", "XEP_0462")
