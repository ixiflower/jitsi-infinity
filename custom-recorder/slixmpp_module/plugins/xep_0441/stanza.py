# Slixmpp: The Slick XMPP Library
# Copyright (C) 2021 Mathieu Pasquet
# This file is part of Slixmpp.
# See the file LICENSE for copying permissio
from collections import abc
import logging
from typing import (
    Iterable,
)

from slixmpp.jid import JID
from slixmpp.xmlstream import ElementBase, ET

log = logging.getLogger(__name__)


class Preferences(ElementBase):
    """MAM Preferences payload.

    .. code-block:: xml

        <iq type='set' id='juliet3'>
          <prefs xmlns='urn:xmpp:mam:2' default='roster'>
            <always>
              <jid>romeo@montague.lit</jid>
            </always>
            <never>
              <jid>montague@montague.lit</jid>
            </never>
          </prefs>
        </iq>

    """
    name = 'prefs'
    namespace = 'urn:xmpp:mam:2'
    plugin_attrib = 'mam_prefs'
    #: Available interfaces:
    #:
    #: - ``default``: Default MAM policy (must be one of 'roster', 'always',
    #:   'never'
    #: - ``always``  (``list[JID]``): list of JIDs to always store
    #:   conversations with.
    #: - ``never``  (``list[JID]``): list of JIDs to never store
    #:   conversations with.
    interfaces = {'default', 'always', 'never'}
    sub_interfaces = {'always', 'never'}

    def get_always(self) -> set[JID]:
        """
        Get a usable set of JIDs the server always stores conversations for.
        """
        results = set()

        jids = self.xml.findall('{%s}always/{%s}jid' % (
            self.namespace, self.namespace))

        for jid in jids:
            results.add(JID(jid.text))

        return results

    def set_always(self, value: Iterable[JID]):
        """
        Set the MAM policy to always archive for the specified JIDs.

        :param value: List of JIDs.
        """
        if not isinstance(value, abc.Iterable):
            if isinstance(value, JID):
                log.warning("Wrong type provided to set_always(): %s", value)
                value = [value]
            else:
                raise ValueError(f'Wrong type for "value" ({value}).')
        elif isinstance(value, str):
            raise ValueError('Wrong type for "value" (str).')

        self._set_sub_text('always', '', keep=True)
        always = self.xml.find('{%s}always' % self.namespace)
        if always is None:
            raise ValueError("<always/> was not found, it should not happen")
        always.clear()

        for jid in value:
            jid_xml = ET.Element('{%s}jid' % self.namespace)
            jid_xml.text = str(jid)
            always.append(jid_xml)

    def get_never(self) -> set[JID]:
        """
        Get a usable set of JIDs the server never stores conversations for.
        """
        results = set()

        jids = self.xml.findall('{%s}never/{%s}jid' % (
            self.namespace, self.namespace))

        for jid in jids:
            results.add(JID(jid.text))

        return results

    def set_never(self, value: Iterable[JID]):
        """
        Set the MAM policy to never archive for the specified JIDs.

        :param value: List of JIDs.
        """
        if not isinstance(value, abc.Iterable):
            if isinstance(value, JID):
                log.warning("Wrong type provided to set_never(): %s", value)
                value = [value]
            else:
                raise ValueError(f'Wrong type for "value" ({value}).')
        elif isinstance(value, str):
            raise ValueError('Wrong type for "value" (str).')

        self._set_sub_text('never', '', keep=True)
        never = self.xml.find('{%s}never' % self.namespace)
        never.clear()
        for jid in value:
            jid_xml = ET.Element('{%s}jid' % self.namespace)
            jid_xml.text = str(jid)
            never.append(jid_xml)
