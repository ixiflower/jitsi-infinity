import io
import logging
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import IO, ClassVar, Literal, overload

from slixmpp.plugins import BasePlugin
from slixmpp.stanza import Message
from slixmpp.xmlstream import register_stanza_plugin

from . import stanza

log = logging.getLogger(__name__)


class XEP_0447(BasePlugin):
    """
    XEP-0447: Stateless File Sharing

    Only support outgoing SFS, incoming is not handled at all.
    """

    name = "xep_0447"
    description = "XEP-0447: Stateless File Sharing"
    dependencies: ClassVar[set[str]] = {"xep_0300", "xep_0446"}
    stanza = stanza

    def plugin_init(self) -> None:
        register_stanza_plugin(Message, stanza.StatelessFileSharing)

        register_stanza_plugin(stanza.StatelessFileSharing, stanza.Sources)
        register_stanza_plugin(
            stanza.StatelessFileSharing, self.xmpp.plugin["xep_0446"].stanza.File
        )
        register_stanza_plugin(stanza.Sources, stanza.UrlData, iterable=True)

    @overload
    def get_sfs(
        self,
        path: Path,
        uris: Iterable[str] | None,
        media_type: str | None,
        desc: str | None,
        disposition: Literal["inline", "attachment"] | None,
        data: None,
        file: None,
    ) -> stanza.StatelessFileSharing: ...

    @overload
    def get_sfs(
        self,
        path: None,
        uris: Iterable[str] | None,
        media_type: str | None,
        desc: str | None,
        disposition: Literal["inline", "attachment"] | None,
        data: bytes,
        file: None,
    ) -> stanza.StatelessFileSharing: ...

    @overload
    def get_sfs(
        self,
        path: None,
        uris: Iterable[str] | None,
        media_type: str | None,
        desc: str | None,
        disposition: Literal["inline", "attachment"] | None,
        data: None,
        file: IO[bytes],
    ) -> stanza.StatelessFileSharing: ...

    def get_sfs(
        self,
        path: Path | None = None,
        uris: Iterable[str] | None = None,
        media_type: str | None = None,
        desc: str | None = None,
        disposition: Literal["inline", "attachment"] | None = None,
        data: bytes | None = None,
        file: IO[bytes] | None = None,
    ) -> stanza.StatelessFileSharing:
        """
        Produce an SFS element from a file present locally.

        :param path: Path of the file.
        :param uris: Iterable on uris to that file.
        :param media_type: Media type of the file.
        :param desc: Description of the file.
        :param disposition: The content-disposition of the file.
        :returns: The SFS element.
        """

        if not (path or data or file):
            raise TypeError("No data was passed")

        sfs = stanza.StatelessFileSharing()
        if disposition:
            sfs["disposition"] = disposition
        if uris is not None:
            for uri in uris:
                ref = stanza.UrlData()
                ref["target"] = uri
                sfs["sources"].append(ref)
        if media_type:
            sfs["file"]["media-type"] = media_type
        if desc:
            sfs["file"]["desc"] = desc
        if path:
            sfs["file"]["name"] = path.name
            stat = path.stat()
            sfs["file"]["size"] = stat.st_size
            sfs["file"]["date"] = datetime.fromtimestamp(stat.st_mtime)
        elif file:
            file.seek(0, io.SEEK_END)
            sfs["file"]["size"] = file.tell()
        elif data:
            sfs["file"]["size"] = len(data)

        h = self.xmpp.plugin["xep_0300"].compute_hash(  # type:ignore[call-overload] # ty:ignore[no-matching-overload]
            filename=path, data=data, file=file
        )
        sfs["file"].append(h)

        return sfs
