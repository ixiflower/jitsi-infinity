
# Slixmpp: The Slick XMPP Library
# Copyright (C) 2020 Mathieu Pasquet <mathieui@mathieui.net>
# This file is part of Slixmpp.
# See the file LICENSE for copying permissio
from slixmpp.stanza import Message
from slixmpp.xmlstream import (
    ElementBase,
    register_stanza_plugin,
)


NS = 'urn:xmpp:tmp:quick-response'


class Response(ElementBase):
    """
    Response element.

    .. code-block:: xml

        <response xmlns="urn:xmpp:tmp:quick-response" xml:lang="en" value="yes" label="Sure!" />
    """
    namespace = NS
    name = 'response'
    plugin_attrib = 'response'
    interfaces = {'value', 'label'}


class Action(ElementBase):
    """
    Action element.

    .. code-block:: xml

        <action xmlns="urn:xmpp:tmp:quick-response" id="merge-32643" label="Merge Now" />
    """
    namespace = NS
    name = 'action'
    plugin_attrib = 'action'
    interfaces = {'id', 'label'}


class ActionSelected(ElementBase):
    """
    Selected Action element.

    .. code-block:: xml

        <action-selected xmlns="urn:xmpp:tmp:quick-response" id="merge-32643" />
    """
    namespace = NS
    name = 'action-selected'
    plugin_attrib = 'action_selected'
    interfaces = {'id'}


def register_plugins():
    register_stanza_plugin(Message, Action, iterable=True)
    register_stanza_plugin(Message, ActionSelected)
    register_stanza_plugin(Message, Response, iterable=True)
