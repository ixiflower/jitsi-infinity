# slixmpp: The Slick XMPP Library
# Copyright (C) 2018 Emmanuel Gil Peyrot
# This file is part of slixmpp.
# See the file LICENSE for copying permission.

import logging
import os.path
from asyncio import Future
from collections.abc import Callable
from mimetypes import guess_type
from pathlib import Path
from typing import IO, ClassVar, Literal

from aiohttp import ClientSession

from slixmpp import JID, __version__
from slixmpp.plugins import BasePlugin
from slixmpp.stanza import Iq
from slixmpp.xmlstream import register_stanza_plugin
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.matcher import StanzaPath

from . import stanza
from .stanza import Get, Header, Put, Request, Slot

log = logging.getLogger(__name__)


PurposeLiteral = Literal["message", "profile", "ephemeral", "permanent"]


class FileUploadError(Exception):
    pass


class UploadServiceNotFound(FileUploadError):
    """
    Raised if no upload service can be found.
    """


class FileTooBig(FileUploadError):
    """
    Raised if the file size is above advertised server limits.

    args:

    - size of the file
    - max file size allowed
    """

    def __str__(self) -> str:
        return f"File size too large: {self._human_readable(self.args[0])} (max: {self._human_readable(self.args[1])})"

    @staticmethod
    def _human_readable(size: float) -> str:
        """
        Convert a size in bytes to a human-readable string with decimals.
        """
        for unit in ["bytes", "KiB", "MiB", "GiB", "TiB"]:
            if size < 1024:
                if unit == "bytes":
                    return f"{size} {unit}"
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PiB"


class HTTPError(FileUploadError):
    """
    Raised when we receive an HTTP error response during upload.

    args:

    - HTTP Error code
    - Content of the HTTP response
    """

    def __str__(self) -> str:
        return f"Could not upload file: {self.args[0]} ({self.args[1]})"


class PurposeNotSupported(FileUploadError):
    """
    Raised when the upload service does not support the requested purpose,
    cf https://xmpp.org/extensions/xep-0363.html#purpose

    args:

    - service: JID
    - purpose: str
    """

    def __str__(self) -> str:
        return f"Could not upload file: '{self.args[0]}' does not support the '{self.args[1]}' purpose"


class XEP_0363(BasePlugin):
    """
    XEP-0363: HTTP File Upload

    Configuration:

    - 'upload_service': Upload service to use. If unset, slixmpp will attempt to
        automatically discover one
    - 'max_file_size': Defaults to ``float('+inf')``
    - 'default_content_type': Default content type to use when uploading files, when
        None is specified. Defaults to 'application/octet-stream'
    - 'handle_upload_requests': Defaults to False. Set this to True to implement a
        HTTP upload component, and hook on the 'http_upload_request' event.
    """

    name = "xep_0363"
    description = "XEP-0363: HTTP File Upload"
    dependencies: ClassVar[set[str]] = {"xep_0030", "xep_0128"}
    stanza = stanza
    default_config: ClassVar[dict] = {
        "upload_service": None,
        "max_file_size": float("+inf"),
        "default_content_type": "application/octet-stream",
        "handle_upload_requests": False,
    }

    handle_upload_requests: bool
    _upload_service_purposes: set[str] | None

    def plugin_init(self) -> None:
        register_stanza_plugin(Iq, Request)
        register_stanza_plugin(Iq, Slot)
        register_stanza_plugin(Slot, Put)
        register_stanza_plugin(Slot, Get)
        register_stanza_plugin(Put, Header, iterable=True)
        for purpose in (
            stanza.MessagePurpose,
            stanza.EphemeralPurpose,
            stanza.PermanentPurpose,
            stanza.ProfilePurpose,
        ):
            register_stanza_plugin(stanza.Request, purpose)
        self._upload_service_purposes = None

        if self.handle_upload_requests:
            self.xmpp.register_handler(
                Callback(
                    "HTTP Upload Request",
                    StanzaPath("iq@type=get/http_upload_request"),
                    self._handle_request,
                )
            )

    def plugin_end(self) -> None:
        if self.handle_upload_requests:
            self.xmpp.remove_handler("HTTP Upload Request")
            self.xmpp.plugin["xep_0030"].del_feature(feature=Request.namespace)

    def session_bind(self, jid: JID | str) -> None:
        if self.handle_upload_requests:
            self.xmpp.plugin["xep_0030"].add_feature(Request.namespace)

    def _handle_request(self, iq: Iq) -> None:
        self.xmpp.event("http_upload_request", iq)

    async def find_upload_service(
        self,
        domain: JID | None = None,
        *,
        callback: Callable | None = None,
        timeout: float | None = None,
    ) -> Iq | None:
        """Find an upload service on a domain (our own by default).

        :param domain: Domain to disco to find a service.
        """
        if domain is None and self.xmpp.is_component:
            domain = self.xmpp.server_host

        results = await self.xmpp.plugin["xep_0030"].get_info_from_domain(
            domain=domain, callback=callback, timeout=timeout
        )

        candidates = []
        for info in results:
            if not info.get_plugin("disco_info", check=True):
                continue
            for identity in info["disco_info"]["identities"]:
                if identity[0] == "store" and identity[1] == "file":
                    candidates.append(info)
        for info in candidates:
            for feature in info["disco_info"]["features"]:
                if feature == Request.namespace:
                    return info

    def request_slot(
        self,
        jid: JID,
        filename: Path | str,
        size: int,
        content_type: str | None = None,
        *,
        purpose: PurposeLiteral | None = None,
        ifrom: JID | None = None,
        callback: Callable | None = None,
        timeout: float | None = None,
    ) -> Future:
        """Request an HTTP upload slot from a service.

        :param jid: Service to request the slot from.
        :param filename: Name of the file that will be uploaded.
        :param size: size of the file in bytes.
        :param content_type: Type of the file that will be uploaded.
        """
        iq = self.xmpp.make_iq_get(ito=jid, ifrom=ifrom)
        request = iq["http_upload_request"]
        request["filename"] = str(filename)
        request["size"] = str(size)
        request["content-type"] = content_type or self.default_content_type
        if purpose is not None:
            request.enable(purpose)
        return iq.send(callback=callback, timeout=timeout)

    def _update_upload_service_purposes(self, iq: Iq) -> None:
        self._upload_service_purposes = set()
        for feature in iq["disco_info"]["features"]:
            if feature.startswith(stanza.PURPOSE_NAMESPACE):
                self._upload_service_purposes.add(
                    feature.removeprefix(stanza.PURPOSE_NAMESPACE)[1:].lower()
                )

    async def upload_file(
        self,
        filename: Path | str,
        size: int | None = None,
        content_type: str | None = None,
        *,
        input_file: IO[bytes] | None = None,
        domain: JID | None = None,
        purpose: PurposeLiteral | None = None,
        callback: Callable | None = None,
        timeout: float | None = None,
    ) -> str:
        """Helper function which does all of the uploading discovery and
        process.

        :param filename: Path to the file to upload (or only the name if
                         ``input_file`` is provided.
        :param size: size of the file in bytes.
        :param content_type: Type of the file that will be uploaded.
        :param input_file: Binary file stream on the file.
        :param domain: Domain to query to find an HTTP upload service.
        :raises .UploadServiceNotFound: If slixmpp is unable to find an
                                        an available upload service.
        :raises .FileTooBig: If the filesize is above what is accepted by
                             the service.
        :raises .HTTPError: If there is an error in the HTTP operation.
        :returns: The URL of the uploaded file.
        """
        filename = Path(filename)
        if self.upload_service is None:
            info_iq = await self.find_upload_service(
                domain=domain, callback=callback, timeout=timeout
            )
            if info_iq is None:
                raise UploadServiceNotFound()
            self.upload_service = info_iq["from"]
            for form in info_iq["disco_info"].iterables:
                values = form["values"]
                if values["FORM_TYPE"] == ["urn:xmpp:http:upload:0"]:
                    try:
                        self.max_file_size = int(values["max-file-size"])
                    except (TypeError, ValueError):
                        log.error(
                            "Invalid max size received from HTTP File Upload service"
                        )
                        self.max_file_size = float("+inf")
                    break
            self._update_upload_service_purposes(info_iq)

        # From the XEP:
        # > As the 'message' purpose is the default, explicitly announcing the
        # > feature and including this purpose in the slot request is technically
        # > redundant and is done solely for the sake of completeness.
        if purpose is not None and purpose != "message":
            if self._upload_service_purposes is None:
                info_iq = await self.xmpp.plugin["xep_0030"].get_info(
                    self.upload_service
                )
                self._update_upload_service_purposes(info_iq)
            assert self._upload_service_purposes is not None
            if purpose not in self._upload_service_purposes:
                raise PurposeNotSupported(self.upload_service, purpose)

        if input_file is None:
            input_file = open(filename, "rb")  # noqa

        if size is None:
            size = input_file.seek(0, 2)
            input_file.seek(0)

        if size > self.max_file_size:
            raise FileTooBig(size, self.max_file_size)

        if content_type is None:
            content_type = guess_type(filename)[0]
            if content_type is None:
                content_type = self.default_content_type

        basename = os.path.basename(filename)
        slot_iq = await self.request_slot(
            self.upload_service,
            basename,
            size,
            content_type,
            purpose=purpose,
            timeout=timeout,
            callback=callback,
        )
        slot = slot_iq["http_upload_slot"]

        headers = {
            "Content-Length": str(size),
            "Content-Type": content_type or self.default_content_type,
            **{header["name"]: header["value"] for header in slot["put"]["headers"]},
        }

        # Do the actual upload here.
        async with ClientSession(
            headers={"User-Agent": "slixmpp " + __version__}
        ) as session:
            response = await session.put(
                slot["put"]["url"], data=input_file, headers=headers
            )
            if response.status >= 400:
                raise HTTPError(response.status, await response.text())
            log.debug("Response code: %d (%s)", response.status, await response.text())
            response.close()
            return slot["get"]["url"]
