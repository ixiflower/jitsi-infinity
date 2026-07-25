# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
import logging

from typing import Awaitable

from slixmpp import Iq, JID
from slixmpp.plugins import BasePlugin
from slixmpp.plugins.xep_0257 import stanza


log = logging.getLogger(__name__)


class XEP_0257(BasePlugin):

    name = 'xep_0257'
    description = 'XEP-0257: Client Certificate Management for SASL EXTERNAL'
    dependencies = {'xep_0030'}
    stanza = stanza

    def plugin_init(self) -> None:
        stanza.register_plugins()

    async def get_certs(self, ifrom: JID | None = None,
                        timeout: float | None = None) -> set[tuple[str, str, tuple[str, ...]]]:
        """
        Return the list of cert items.

        :param ifrom: JID to send the stanza from (for components).
        :param timeout: Timeout of the query (in seconds)
        :returns: A list of certificate items as tuple of (name, cert, active users).
        :raises IqTimeout: When the query timeouts
        :raises IqError: If the server encounters an error while processing
                         the query.
        """
        iq = self.xmpp.Iq()
        iq['type'] = 'get'
        iq['from'] = ifrom
        iq.enable('sasl_certs')
        certs = await iq.send(timeout=timeout)
        return {
            (cert['name'], cert['x509cert'], tuple(cert['users']))
            for cert in certs['sasl_certs']['items']
        }

    def add_cert(self, name: str, cert: str,
                 allow_management: bool = True,
                 ifrom: JID | None = None,
                 timeout: float | None = None) -> Awaitable[Iq]:
        """
        Register a cert with the server.

        :param name: Name of the cert.
        :param cert: Base64 of the cert’s DER.
        :param allow_management: Allow management of this cert by a client
                                 logged in with it.
        :param ifrom: JID to send the stanza from (for components).
        :param timeout: Timeeout of the query (in seconds).
        """
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq['sasl_cert_append']['name'] = name
        iq['sasl_cert_append']['x509cert'] = cert
        iq['sasl_cert_append']['cert_management'] = allow_management
        return iq.send(timeout=timeout)

    def disable_cert(self, name: str, ifrom: JID | None = None,
                     timeout: float | None = None) -> Awaitable[Iq]:
        """
        Disable a cert. Clients using this cert are not immediately disconnected.

        :param name: Name of the cert.
        :param ifrom: JID to send the stanza from (for components).
        :param timeout: Timeeout of the query (in seconds).
        """
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq['sasl_cert_disable']['name'] = name
        return iq.send(timeout=timeout)

    def revoke_cert(self, name: str, ifrom: JID | None = None,
                    timeout: float | None = None) -> Awaitable[Iq]:
        """
        Revoke a cert. Clients using this cert are immediately disconnected.

        :param name: Name of the cert.
        :param ifrom: JID to send the stanza from (for components).
        :param timeout: Timeeout of the query (in seconds).
        """
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq['sasl_cert_revoke']['name'] = name
        return iq.send(timeout=timeout)
