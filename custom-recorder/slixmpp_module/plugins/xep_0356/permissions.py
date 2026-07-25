import dataclasses
from collections import defaultdict
from enum import StrEnum
from typing import ClassVar


class RosterAccess(StrEnum):
    NONE = "none"
    GET = "get"
    SET = "set"
    BOTH = "both"


class MessagePermission(StrEnum):
    NONE = "none"
    OUTGOING = "outgoing"


class IqPermission(StrEnum):
    NONE = "none"
    GET = "get"
    SET = "set"
    BOTH = "both"


class PresencePermission(StrEnum):
    NONE = "none"
    MANAGED_ENTITY = "managed_entity"
    ROSTER = "roster"


@dataclasses.dataclass
class Permissions:
    roster = RosterAccess.NONE
    message = MessagePermission.NONE
    iq: ClassVar[defaultdict[str, IqPermission]] = defaultdict(
        lambda: IqPermission.NONE
    )
    presence = PresencePermission.NONE
