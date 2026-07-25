import logging
import uuid
from collections import defaultdict
from collections.abc import Callable
from typing import ClassVar
from xml.etree import ElementTree as ET

from slixmpp import JID, Iq, Message
from slixmpp.exceptions import IqError
from slixmpp.plugins.base import BasePlugin
from slixmpp.types import JidStr
from slixmpp.xmlstream import StanzaBase
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.matcher import StanzaPath

from . import stanza
from .permissions import IqPermission, MessagePermission, Permissions, RosterAccess

log = logging.getLogger(__name__)


class PrivilegedIqError(IqError):
    """
    Exception raised when sending a privileged IQ stanza fails.
    """

    def nested_error(self) -> IqError | None:
        """
        Return the IQError generated from the inner IQ stanza, if present.
        """
        if (
            "privilege" in self.iq
            and "forwarded" in self.iq["privilege"]
            and "iq" in self.iq["privilege"]["forwarded"]
        ):
            return IqError(self.iq["privilege"]["forwarded"]["iq"])
        return None


class XEP_0356(BasePlugin):
    """
    XEP-0356: Privileged Entity

    Events:

    ::

        privileges_advertised  -- Received message/privilege from the server
    """

    name = "xep_0356"
    description = "XEP-0356: Privileged Entity"
    dependencies: ClassVar[set[str]] = {"xep_0297"}
    stanza = stanza

    granted_privileges: ClassVar[defaultdict[JidStr, Permissions]] = defaultdict(
        Permissions
    )

    def plugin_init(self) -> None:
        if not self.xmpp.is_component:
            log.error("XEP 0356 is only available for components")
            return

        stanza.register()

        self.xmpp.register_handler(
            Callback(
                "Privileges",
                StanzaPath("message/privilege"),
                self._handle_privilege,
            )
        )

    def plugin_end(self) -> None:
        self.xmpp.remove_handler("Privileges")

    def _handle_privilege(self, msg: StanzaBase) -> None:
        """
        Called when the XMPP server advertise the component's privileges.

        Stores the privileges in this instance's granted_privileges attribute (a dict)
        and raises the privileges_advertised event
        """
        permissions = self.granted_privileges[msg.get_from()]
        for perm in msg["privilege"]["perms"]:
            access = perm["access"]
            if access == "iq":
                for ns in perm["namespaces"]:
                    permissions.iq[ns["ns"]] = ns["type"]
            elif access in _VALID_ACCESSES:
                setattr(permissions, access, perm["type"])
            else:
                log.warning("Received an invalid privileged access: %s", access)
        log.debug(f"Privileges: {self.granted_privileges}")
        self.xmpp.event("privileges_advertised")

    def send_privileged_message(self, msg: Message) -> None:
        if (
            self.granted_privileges[msg.get_from().domain].message
            != MessagePermission.OUTGOING
        ):
            raise PermissionError(
                "The server hasn't authorized us to send messages on behalf of other users"
            )
        else:
            self._make_privileged_message(msg).send()

    def _make_privileged_message(self, msg: Message) -> Message:
        server = msg.get_from().domain
        wrapped = self.xmpp.make_message(mto=server, mfrom=self.xmpp.boundjid.bare)
        wrapped["privilege"]["forwarded"].append(msg)
        return wrapped

    def _make_get_roster(self, jid: JID | str) -> Iq:
        return self.xmpp.make_iq_get(
            queryxmlns="jabber:iq:roster",
            ifrom=self.xmpp.boundjid.bare,
            ito=jid,
        )

    def _make_set_roster(
        self,
        jid: JID | str,
        roster_items: dict,
    ) -> Iq:
        iq = self.xmpp.make_iq_set(ifrom=self.xmpp.boundjid.bare, ito=jid)
        iq["roster"]["items"] = roster_items
        return iq

    async def get_roster(
        self,
        jid: JID | str,
        *,
        callback: Callable | None = None,
        timeout: float | None = None,
    ) -> Iq:
        """
        Return the roster of user on the server the component has privileged access to.

        Raises ValueError if the server did not advertise the corresponding privileges

        :param jid: user we want to fetch the roster from
        """
        if isinstance(jid, str):
            jid = JID(jid)
        if self.granted_privileges[jid.domain].roster not in (
            RosterAccess.GET,
            RosterAccess.BOTH,
        ):
            raise PermissionError(
                "The server did not grant us privileges to get rosters"
            )
        else:
            return await self._make_get_roster(jid).send(
                callback=callback, timeout=timeout
            )

    async def set_roster(
        self,
        jid: JID | str,
        roster_items: dict,
        *,
        callback: Callable | None = None,
        timeout: float | None = None,
    ) -> Iq:
        """
        Return the roster of user on the server the component has privileged access to.

        Raises ValueError if the server did not advertise the corresponding privileges

        Here is an example of a roster_items value:

        .. code-block:: json

            {
                "friend1@example.com": {
                    "name": "Friend 1",
                    "subscription": "both",
                    "groups": ["group1", "group2"],
                },
                "friend2@example.com": {
                    "name": "Friend 2",
                    "subscription": "from",
                    "groups": ["group3"],
                },
            }

        :param jid: user we want to add or modify roster items
        :param roster_items: a dict containing the roster items' JIDs as keys and
                             nested dicts containing names, subscriptions and groups.

        """
        if isinstance(jid, str):
            jid = JID(jid)
        if self.granted_privileges[jid.domain].roster not in (
            RosterAccess.GET,
            RosterAccess.BOTH,
        ):
            raise PermissionError(
                "The server did not grant us privileges to set rosters"
            )
        else:
            return await self._make_set_roster(jid, roster_items).send(
                callback=callback, timeout=timeout
            )

    async def send_privileged_iq(
        self, encapsulated_iq: Iq, iq_id: str | None = None
    ) -> Iq:
        """
        Send an IQ on behalf of a user

        Caution: the IQ *must* have the jabber:client namespace

        Raises :class:`PrivilegedIqError` on failure.
        """
        iq_id = iq_id or str(uuid.uuid4())
        encapsulated_iq["id"] = iq_id
        if encapsulated_iq.namespace != "jabber:client":
            _set_client_namespace(encapsulated_iq.xml)
        server = encapsulated_iq.get_from().domain
        perms = self.granted_privileges.get(server)
        if not perms:
            raise PermissionError(f"{server} has not granted us any privilege")
        itype = encapsulated_iq["type"]
        for ns in encapsulated_iq.plugins.values():
            type_ = perms.iq[ns.namespace]
            if type_ == IqPermission.NONE:
                raise PermissionError(
                    f"{server} has not granted any IQ privilege for namespace {ns.namespace}"
                )
            elif type_ == IqPermission.BOTH:
                pass
            elif type_ != itype:
                raise PermissionError(
                    f"{server} has not granted IQ {itype} privilege for namespace {ns.namespace}"
                )
        iq = self.xmpp.make_iq(
            itype=itype,
            ifrom=self.xmpp.boundjid.bare,
            ito=encapsulated_iq.get_from(),
            id=iq_id,
        )
        iq["privileged_iq"].append(encapsulated_iq)

        try:
            resp = await iq.send()
        except IqError as exc:
            raise PrivilegedIqError(exc.iq)

        return resp["privilege"]["forwarded"]["iq"]


def _set_client_namespace(xml: ET.Element) -> None:
    """
    Hack to fix namespaces between jabber:component and jabber:client

    Acts in-place.
    """
    xml.tag = xml.tag.replace("{jabber:component:accept}", "{jabber:client}")
    for child in xml:
        _set_client_namespace(child)


# does not include iq access that is handled differently
_VALID_ACCESSES = {"message", "roster", "presence"}
