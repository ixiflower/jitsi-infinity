# Slixmpp: The Slick XMPP Library
# Copyright (C) 2025 Mathieu Pasquet
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

from datetime import datetime
from enum import Enum
from slixmpp import Iq, register_stanza_plugin, ElementBase
from slixmpp.plugins.xep_0082 import parse, format_datetime

NS = 'urn:xmpp:cam:0'


class ClientType(Enum):
    """
    Enum representing the ``type`` attribute of the ``<client/>`` element.
    """
    SESSION = 'session'
    ACCESS = 'access'


class PermissionEnum(Enum):
    """
    Enum representing the ``status`` of the ``<permission/>`` element, e.g:

    .. code-block:: xml

        <permission status="normal/>

    """
    UNRESTRICTED = 'unrestricted'
    NORMAL = 'normal'
    RESTRICTED = 'restricted'


class Revoke(ElementBase):
    """
    Element used to revoke a device.
    """
    namespace = NS
    name = 'revoke'
    plugin_attrib = 'revoke'
    interfaces = {'id'}


class List(ElementBase):
    """
    Element used to request a list of devices to the server.
    """
    namespace = NS
    name = 'list'
    plugin_attrib = 'list'
    interfaces = {}


class Clients(ElementBase):
    """List of clients.

    Iterate on it to get all substanzas.

    .. code-block::

        <clients xmlns="urn:xmpp:cam:0">
            …
        </clients>
    """
    namespace = NS
    name = 'clients'
    plugin_attrib = 'clients'


class Client(ElementBase):
    """Client element.

    .. code-block:: xml

        <client xmlns="urn:xmpp:cam:0" type="session" id="a" connected="true">
            …
        </client>

    Many of the substanzas defined are using overrides to access and set
    data from this element, e.g.:

    .. code-block:: python

        client = Client()
        client['user_agent'] = {'software': 'slixmpp', 'device': 'toto'}

    will actually create

    .. code-block:: xml

        <client xmlns="urn:xmpp:cam:0">
            <user-agent>
                <software>slixmpp</software>
                <device>toto</device>
            </user-agent>
        </client>

    """
    namespace = NS
    name = 'client'
    plugin_attrib = 'client'
    interfaces = {
        'connected', 'id', 'type', 'first_seen', 'last_seen',
        'permission', 'permission_extra',
    }

    def get_type(self) -> ClientType | None:
        type_ = self.xml.attrib.get('type', None)
        if type_ is not None:
            return ClientType(type_)
        return None

    def set_type(self, type_: str | ClientType) -> None:
        if isinstance(type_, ClientType):
            value = type_.value
        else:
            ClientType(type_)
            value = type_
        self.xml.attrib['type'] = value

    def get_connected(self) -> bool | None:
        connected = self.xml.attrib.get('connected', None)
        if connected is None or connected.lower() not in ('true', 'false'):
            return None
        return connected.lower() == 'true'

    def set_connected(self, connected: bool) -> None:
        self.xml.attrib['connected'] = str(connected).lower()

    def get_first_seen(self) -> datetime | None:
        try:
            parse(self._get_sub_text('first-seen'))
        except:
            return None

    def get_last_seen(self) -> datetime | None:
        try:
            parse(self._get_sub_text('last-seen'))
        except:
            return None

    def set_first_seen(self, time: str | datetime) -> None:
        if isinstance(time, str):
            time = parse(time)
        self._set_sub_text('first-seen', format_datetime(time))

    def set_last_seen(self, time: str | datetime) -> None:
        if isinstance(time, str):
            time = parse(time)
        self._set_sub_text('last-seen', format_datetime(time))

    def del_permission(self) -> None:
        found = self.xml.findall('{%s}permission' % NS)
        if found:
            for permission in found:
                self.xml.remove(permission)

    def del_user_agent(self) -> None:
        found = self.xml.findall('{%s}user-agent' % NS)
        if found:
            for agent in found:
                self.xml.remove(agent)


class UserAgent(ElementBase):
    namespace = NS
    name = 'user-agent'
    plugin_attrib = 'user_agent'
    interfaces = {'software', 'uri', 'device'}
    sub_interfaces = {'software', 'uri', 'device'}

    def as_dict(self) -> dict[str, str]:
        return {key: self[key] for key in self.sub_interfaces}


class Permission(ElementBase):
    """
    Permission element.
    """
    namespace = NS
    name = 'permission'
    plugin_attrib = 'permission'
    interfaces = {'permission', 'permission_extra'}
    overrides = {
        'set_permission', 'get_permission',
        'set_permission_extra', 'get_permission_extra', 'del_permission_extra',
    }

    def get_permission(self) -> PermissionEnum | None:
        return PermissionEnum(self.xml.attrib.get('status'))

    def set_permission(self, permission: str | PermissionEnum) -> None:
        if isinstance(permission, PermissionEnum):
            value = permission.value
        else:
            PermissionEnum(permission)
            value = permission
        self.xml.attrib['status'] = value

    def get_permission_extra(self) -> list[ElementBase]:
        return list(self)

    def set_permission_extra(self, extras: list[ElementBase]) -> None:
        self.clear()
        for extra in extras:
            self.append(extra)

    def del_permission_extra(self) -> None:
        self.clear()


class Auth(ElementBase):
    """
    Auth element.


    .. code-block:: xml

        <auth>
            <fast/>
            <custom-element xmlns="urn:custom"/>
        </auth>
    """
    namespace = NS
    name = 'auth'
    plugin_attrib = 'auth'
    interfaces = {'password', 'fast', 'all'}
    bool_interfaces = {'password', 'fast'}
    overrides = {'get_auths'}

    def get_auths(self) -> dict:
        return {
            'password': self['password'],
            'grant': 'grant' in self,
            'fast': self['fast'],
            'others': [sub for sub in self],
        }


class Grant(ElementBase):
    """``<grant/>`` element."""
    namespace = NS
    name = 'grant'
    plugin_attrib = 'grant'


def register_plugins() -> None:
    register_stanza_plugin(Iq, Clients)
    register_stanza_plugin(Iq, List)
    register_stanza_plugin(Iq, Revoke)
    register_stanza_plugin(Clients, Client, iterable=True)
    register_stanza_plugin(Client, UserAgent, overrides=True)
    register_stanza_plugin(Client, Permission, overrides=True)
    register_stanza_plugin(Client, Auth, overrides=True)
    register_stanza_plugin(Grant, Permission, overrides=True)
    register_stanza_plugin(Auth, Grant)
