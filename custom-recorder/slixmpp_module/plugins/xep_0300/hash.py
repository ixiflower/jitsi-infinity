# Slixmpp: The Slick XMPP Library
# Copyright (C) 2017 Emmanuel Gil Peyrot
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
import hashlib
import logging
from base64 import b64encode
from collections.abc import Callable
from pathlib import Path
from typing import IO, ClassVar, Protocol, overload

from slixmpp import JID, ClientXMPP, ComponentXMPP
from slixmpp.plugins import BasePlugin
from slixmpp.plugins.xep_0300 import Hash, stanza

log = logging.getLogger(__name__)


class HashFunc(Protocol):
    def update(self, data: bytes) -> None: ...
    def digest(self) -> bytes: ...


class XEP_0300(BasePlugin):
    """
    XEP-0300: Use of Cryptographic Hash Functions in XMPP
    """

    name = "xep_0300"
    description = "XEP-0300: Use of Cryptographic Hash Functions in XMPP"
    dependencies: ClassVar[set[str]] = {"xep_0030"}
    stanza = stanza
    default_config: ClassVar[dict] = {
        "block_size": 1024 * 1024,  # One MiB
        "preferred": "sha-256",
        "enable_sha-1": False,
        "enable_sha-256": True,
        "enable_sha-512": True,
        "enable_sha3-256": True,
        "enable_sha3-512": True,
        "enable_BLAKE2b256": True,
        "enable_BLAKE2b512": True,
    }
    block_size: int

    _hashlib_function: ClassVar[dict[str, Callable[[], HashFunc]]] = {
        "sha-1": hashlib.sha1,
        "sha-256": hashlib.sha256,
        "sha-512": hashlib.sha512,
        "sha3-256": hashlib.sha3_256,
        "sha3-512": hashlib.sha3_512,
        "BLAKE2b256": lambda: hashlib.blake2b(digest_size=32),
        "BLAKE2b512": lambda: hashlib.blake2b(digest_size=64),
    }

    def __init__(self, xmpp: ClientXMPP | ComponentXMPP, config: dict | None) -> None:
        super().__init__(xmpp, config)
        self.enabled_hashes = []

    def plugin_init(self) -> None:
        namespace = "urn:xmpp:hash-function-text-names:%s"
        self.enabled_hashes.clear()
        for algo in self._hashlib_function:
            if getattr(self, "enable_" + algo, False):
                self.enabled_hashes.append(namespace % algo)

    def session_bind(self, jid: JID | str) -> None:
        self.xmpp.plugin["xep_0030"].add_feature(Hash.namespace)

        for namespace in self.enabled_hashes:
            self.xmpp.plugin["xep_0030"].add_feature(namespace)

    def plugin_end(self) -> None:
        for namespace in self.enabled_hashes:
            self.xmpp.plugin["xep_0030"].del_feature(feature=namespace)
        self.enabled_hashes.clear()

        self.xmpp.plugin["xep_0030"].del_feature(feature=Hash.namespace)

    @overload
    def compute_hash(
        self,
        filename: str | Path,
        function: str | None,
        *,
        data: None,
        file: None,
    ) -> Hash: ...

    @overload
    def compute_hash(
        self,
        filename: None,
        function: str | None,
        *,
        data: bytes,
        file: None,
    ) -> Hash: ...

    @overload
    def compute_hash(
        self,
        filename: None,
        function: str | None,
        *,
        data: None,
        file: IO[bytes],
    ) -> Hash: ...

    def compute_hash(
        self,
        filename: str | Path | None = None,
        function: str | None = None,
        *,
        data: bytes | None = None,
        file: IO[bytes] | None = None,
    ) -> Hash:
        """
        Compute the hash of a file, and return the relevant hash XML element.

        :param filename: Path of the file to hash.
        :param function: Name of the hash function to use. If left empty,
                         the preferred function set in ``self.preferred``
                         will be used.
        :returns: A Hash element.
        """
        if function is None:
            function = self.preferred
        h = self._hashlib_function[function]()
        if data is not None:
            h.update(data)
        elif file is not None:
            file.seek(0)
            while block := file.read(self.block_size):
                h.update(block)
        elif filename is not None:
            with open(filename, "rb") as file:
                while block := file.read(self.block_size):
                    h.update(block)

        hash_elem = Hash()
        hash_elem["algo"] = function
        hash_elem["value"] = b64encode(h.digest()).decode()
        return hash_elem
