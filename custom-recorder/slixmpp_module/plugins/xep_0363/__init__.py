# slixmpp: The Slick XMPP Library
# Copyright (C) 2018 Emmanuel Gil Peyrot
# This file is part of slixmpp.
# See the file LICENSE for copying permission.
from slixmpp.plugins.base import register_plugin
from slixmpp.plugins.xep_0363.http_upload import (
    XEP_0363,
    FileTooBig,
    FileUploadError,
    HTTPError,
    PurposeLiteral,
    UploadServiceNotFound,
)
from slixmpp.plugins.xep_0363.stanza import (
    PURPOSE_NAMESPACE,
    EphemeralPurpose,
    Get,
    Header,
    MessagePurpose,
    PermanentPurpose,
    ProfilePurpose,
    Put,
    Request,
    Slot,
)

register_plugin(XEP_0363)

__all__ = [
    "PURPOSE_NAMESPACE",
    "XEP_0363",
    "EphemeralPurpose",
    "FileTooBig",
    "FileUploadError",
    "Get",
    "HTTPError",
    "Header",
    "MessagePurpose",
    "PermanentPurpose",
    "ProfilePurpose",
    "PurposeLiteral",
    "Put",
    "Request",
    "Slot",
    "UploadServiceNotFound",
]
