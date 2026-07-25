# Slixmpp: The Slick XMPP Library
# Copyright © 2021 Mathieu Pasquet <mathieui@mathieui.net>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

"""
This file contains boilerplate to define types relevant to slixmpp.
"""

from typing import (
    Any,
    Iterable,
    Literal,
    NamedTuple,
    Protocol,
    TypedDict,
)

from slixmpp.jid import JID

PresenceTypes = Literal[
    'error', 'probe', 'subscribe', 'subscribed',
    'unavailable', 'unsubscribe', 'unsubscribed',
]

PresenceShows = Literal[
    'away', 'chat', 'dnd', 'xa',
]

# add the empty string, but not for sending
ExtPresenceShows = Literal[
    'away', 'chat', 'dnd', 'xa', ''
]

MessageTypes = Literal[
    'chat', 'error', 'groupchat',
    'headline', 'normal',
]

IqTypes = Literal[
    "error", "get", "set", "result",
]

MucRole = Literal[
    'moderator', 'participant', 'visitor', 'none'
]

MucAffiliation = Literal[
    'outcast', 'member', 'admin', 'owner', 'none'
]

OptJid = JID | None
JidStr = str | JID
OptJidStr = str | JID | None


class PresenceArgs(TypedDict, total=False):
    pfrom: JidStr
    pto: JidStr
    ptype: PresenceTypes
    pshow: PresenceShows | None
    pstatus: str | None


class MucRoomItem(TypedDict, total=False):
    jid: str
    role: MucRole
    affiliation: MucAffiliation
    show: PresenceShows | None
    status: str
    alt_nick: str


class ResourceDict(TypedDict, total=False):
    show: ExtPresenceShows
    priority: int
    status: str


RosterState = TypedDict(
    'RosterState',
    {
        'from': bool,
        'to': bool,
        'pending_in': bool,
        'pending_out': bool,
        'whitelisted': bool,
        'subscription': str,
        'name': str,
        'groups': list[str],
        'removed': bool,
    }
)


class RosterDBProtocol(Protocol):
    def load(self, owner: JidStr, jid: JidStr,
             db_state: dict[str, Any]) -> RosterState | None:
        ...

    def save(self, owner: JidStr, jid: JidStr,
             state: RosterState, db_state: dict[str, Any]):
        ...

    def entries(self, owner: OptJidStr,
                db_state: dict[str, Any] | None = None) -> Iterable[str]:
        ...


MucRoomItemKeys = Literal[
    'jid', 'role', 'affiliation', 'show', 'status',  'alt_nick',
]

MAMDefault = Literal['always', 'never', 'roster']

FilterString = Literal['in', 'out', 'out_sync', 'out_sce']

ErrorTypes = Literal["modify", "cancel", "auth", "wait", "cancel"]

ErrorConditions = Literal[
    "bad-request",
    "conflict",
    "feature-not-implemented",
    "forbidden",
    "gone",
    "internal-server-error",
    "item-not-found",
    "jid-malformed",
    "not-acceptable",
    "not-allowed",
    "not-authorized",
    "payment-required",
    "policy-violation",
    "recipient-unavailable",
    "redirect",
    "registration-required",
    "remote-server-not-found",
    "remote-server-timeout",
    "resource-constraint",
    "service-unavailable",
    "subscription-required",
    "undefined-condition",
    "unexpected-request",
]

# https://xmpp.org/registrar/disco-categories.html#client
ClientTypes = Literal[
    "bot",
    "console",
    "game",
    "handheld",
    "pc",
    "phone",
    "sms",
    "tablet",
    "web",
]


class HatTuple(NamedTuple):
    uri: str
    title: str
    hue: float | None = None


__all__ = [
    'Protocol', 'TypedDict', 'Literal', 'OptJid', 'OptJidStr', 'JidStr',
    'PresenceTypes', 'PresenceShows', 'MessageTypes', 'IqTypes', 'MucRole',
    'MucAffiliation', 'FilterString', 'ErrorConditions', 'ErrorTypes',
    'ClientTypes', 'HatTuple', 'ResourceDict', 'MAMDefault',
]
