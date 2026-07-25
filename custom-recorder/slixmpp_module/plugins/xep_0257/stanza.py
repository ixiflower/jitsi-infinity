# Slixmpp: The Slick XMPP Library
# Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
from slixmpp import Iq
from slixmpp.xmlstream import ElementBase, ET, register_stanza_plugin
from collections.abc import Sequence


class Certs(ElementBase):
    """
    List of certs returned by the server.
    This element is only useful for accessing the certs inside.

    .. code-block:: xml

          <items xmlns='urn:xmpp:saslcert:1'>
            <item>
              <name>Mobile Client</name>
              <x509cert>
                ...
              </x509cert>
              <users>
                <resource>Phone</resource>
              </users>
            </item>
            <item>
              <name>Laptop</name>
              <x509cert>
                ...
              </x509cert>
            </item>
          </items>
        </iq>
    """
    name = 'items'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'sasl_certs'
    interfaces = set()


class CertItem(ElementBase):
    """
    A single cert item.

    Contains the X.509 base64 DER representation, its name, as well
    as a list of users currently logged in with it.

    .. code-block:: xml

        <item xmlns='urn:xmpp:saslcert:1'>
          <name>Mobile Client</name>
          <x509cert>
            ...
          </x509cert>
          <users>
            <resource>Phone</resource>
          </users>
        </item>

    """
    name = 'item'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'item'
    plugin_multi_attrib = 'items'
    interfaces = {'name', 'x509cert', 'users'}
    sub_interfaces = {'name', 'x509cert'}

    def get_users(self) -> set[str]:
        """Return the resources currently using this cert."""
        resources = self.xml.findall('{%s}users/{%s}resource' % (
            self.namespace, self.namespace))
        return {res.text for res in resources if res is not None and res.text}

    def set_users(self, values: Sequence[str]) -> None:
        users = self.xml.find('{%s}users' % self.namespace)
        if users is not None:
            self.xml.remove(users)
        if not values:
            return
        users = ET.Element('{%s}users' % self.namespace)
        self.xml.append(users)
        for resource in values:
            res = ET.Element('{%s}resource' % self.namespace)
            res.text = resource
            users.append(res)

    def del_users(self) -> None:
        users = self.xml.find('{%s}users' % self.namespace)
        if users is not None:
            self.xml.remove(users)


class AppendCert(ElementBase):
    """
    Element used for adding a cert.

    .. code-block:: xml

        <append xmlns='urn:xmpp:saslcert:1'>
            <name>Simple Bot</name>
            <no-cert-management/>
            <x509cert>
              ...
            </x509cert>
        </append>
    """
    name = 'append'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'sasl_cert_append'
    interfaces = {'name', 'x509cert', 'cert_management'}
    sub_interfaces = {'name', 'x509cert'}

    def get_cert_management(self) -> bool:
        manage = self.xml.find('{%s}no-cert-management' % self.namespace)
        return manage is None

    def set_cert_management(self, value: bool) -> None:
        self.del_cert_management()
        if not value:
            manage = ET.Element('{%s}no-cert-management' % self.namespace)
            self.xml.append(manage)

    def del_cert_management(self) -> None:
        manage = self.xml.find('{%s}no-cert-management' % self.namespace)
        if manage is not None:
            self.xml.remove(manage)


class DisableCert(ElementBase):
    """
    Element used for disabling a cert.

    .. code-block:: xml

        <disable xmlns='urn:xmpp:saslcert:1'>
            <name>Mobile Client</name>
        </disable>
    """
    name = 'disable'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'sasl_cert_disable'
    interfaces = {'name'}
    sub_interfaces = interfaces


class RevokeCert(ElementBase):
    """
    Element used for revoking a cert.

    .. code-block:: xml

        <revoke xmlns='urn:xmpp:saslcert:1'>
            <name>Mobile Client</name>
        </revoke>
    """
    name = 'revoke'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'sasl_cert_revoke'
    interfaces = {'name'}
    sub_interfaces = interfaces


def register_plugins():
    register_stanza_plugin(Certs, CertItem, iterable=True)
    register_stanza_plugin(Iq, Certs)
    register_stanza_plugin(Iq, AppendCert)
    register_stanza_plugin(Iq, DisableCert)
    register_stanza_plugin(Iq, RevokeCert)
