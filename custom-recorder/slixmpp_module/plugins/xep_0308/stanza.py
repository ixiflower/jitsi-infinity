
# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permissio
from slixmpp.xmlstream import ElementBase


class Replace(ElementBase):
    """
    Replace element, containing the id of the message to replace.

    .. code-block:: xml

        <replace id='bad1' xmlns='urn:xmpp:message-correct:0'/>
    """
    name = 'replace'
    namespace = 'urn:xmpp:message-correct:0'
    plugin_attrib = 'replace'
    interfaces = {'id'}
