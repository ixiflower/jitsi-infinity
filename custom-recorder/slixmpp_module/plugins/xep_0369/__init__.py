# Slixmpp: The Slick XMPP Library
# Copyright (C) 2020 Mathieu Pasquet <mathieui@mathieui.net>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.plugins.base import register_plugin
from slixmpp.plugins.xep_0369.stanza import (
    MIX,  Setnick, Join, Leave, Subscribe, Unsubscribe, UpdateSubscription,
    Create, Participant, Destroy,
)
from slixmpp.plugins.xep_0369.mix_core import XEP_0369

register_plugin(XEP_0369)

__all__ = ['MIX', 'Setnick', 'Join', 'Leave', 'Subscribe', 'Unsubscribe',
           'UpdateSubscription', 'Create', 'Participant',
           'Destroy', 'XEP_0369']
