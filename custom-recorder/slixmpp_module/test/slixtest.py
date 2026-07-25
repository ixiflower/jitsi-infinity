# Slixmpp: The Slick XMPP Library
# Copyright (C) 2010 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.
import asyncio
import atexit
import contextlib
import difflib
import os
import unittest
from collections.abc import Awaitable, Iterable, Iterator
from typing import Literal, TypeVar
from xml.etree.ElementTree import Element
from xml.parsers.expat import ExpatError

from slixmpp import JID, ClientXMPP, ComponentXMPP
from slixmpp.stanza import Iq, Message, Presence
from slixmpp.stanza.error import Error
from slixmpp.test import TestTransport
from slixmpp.test.mocksocket import TestSocket
from slixmpp.types import JidStr, OptJidStr
from slixmpp.xmlstream import ET, ElementBase
from slixmpp.xmlstream.matcher import (
    MatcherId,
    MatchIDSender,
    MatchXMLMask,
    MatchXPath,
    StanzaPath,
)
from slixmpp.xmlstream.stanzabase import register_stanza_plugin
from slixmpp.xmlstream.tostring import highlight, tostring, tostring_fmt

TestMethod = Literal["exact", "mask", "id", "xpath", "stanzapath"]
T = TypeVar("T")


class SlixTest(unittest.TestCase):
    """
    A Slixmpp specific TestCase class that provides
    methods for comparing message, iq, and presence stanzas.

    Methods:
        Message              -- Create a Message stanza object.
        Iq                   -- Create an Iq stanza object.
        Presence             -- Create a Presence stanza object.
        check_jid            -- Check a JID and its component parts.
        check                -- Compare a stanza against an XML string.
        stream_start         -- Initialize a dummy XMPP client.
        stream_close         -- Disconnect the XMPP client.
        make_header          -- Create a stream header.
        send_header          -- Check that the given header has been sent.
        send_feature         -- Send a raw XML element.
        send                 -- Check that the XMPP client sent the given
                                generic stanza.
        recv                 -- Queue data for XMPP client to receive, or
                                verify the data that was received from a
                                live connection.
        recv_header          -- Check that a given stream header
                                was received.
        recv_feature         -- Check that a given, raw XML element
                                was recveived.
        fix_namespaces       -- Add top-level namespace to an XML object.
        compare              -- Compare XML objects against each other.
    """

    xmpp: ClientXMPP | ComponentXMPP = None  # type:ignore

    def parse_xml(self, xml_string: str) -> ET.Element:
        try:
            xml = ET.fromstring(xml_string)
            return xml
        except (SyntaxError, ExpatError) as e:
            msg = e.msg if hasattr(e, "msg") else e.message  # type:ignore[attr-defined]
            if "unbound" in msg:
                known_prefixes = {"stream": "http://etherx.jabber.org/streams"}

                prefix = xml_string.split("<")[1].split(":")[0]
                if prefix in known_prefixes:
                    xml_string = f'<fixns xmlns:{prefix}="{known_prefixes[prefix]}">{xml_string}</fixns>'
                xml = self.parse_xml(xml_string)
                xml = next(iter(xml))
                return xml
            else:
                self.fail(f"XML data was mal-formed:\n{xml_string}")

    # ------------------------------------------------------------------
    # Shortcut methods for creating stanza objects

    def Message(self, *args: object, **kwargs: object) -> Message:
        """
        Create a Message stanza.

        Uses same arguments as StanzaBase.__init__

        Arguments:
            xml -- An XML object to use for the Message's values.
        """
        return Message(self.xmpp, *args, **kwargs)

    def Iq(self, *args: object, **kwargs: object) -> Iq:
        """
        Create an Iq stanza.

        Uses same arguments as StanzaBase.__init__

        Arguments:
            xml -- An XML object to use for the Iq's values.
        """
        return Iq(self.xmpp, *args, **kwargs)

    def Presence(self, *args: object, **kwargs: object) -> Presence:
        """
        Create a Presence stanza.

        Uses same arguments as StanzaBase.__init__

        Arguments:
            xml -- An XML object to use for the Iq's values.
        """
        return Presence(self.xmpp, *args, **kwargs)  # type:ignore

    def check_jid(
        self,
        jid: JID,
        user: str | None = None,
        domain: str | None = None,
        resource: str | None = None,
        bare: str | None = None,
        full: str | None = None,
        string: str | None = None,
    ) -> None:
        """
        Verify the components of a JID.

        Arguments:
            jid      -- The JID object to test.
            user     -- Optional. The user name portion of the JID.
            domain   -- Optional. The domain name portion of the JID.
            resource -- Optional. The resource portion of the JID.
            bare     -- Optional. The bare JID.
            full     -- Optional. The full JID.
            string   -- Optional. The string version of the JID.
        """
        if user is not None:
            self.assertEqual(jid.user, user, f"User does not match: {jid.user}")
        if domain is not None:
            self.assertEqual(jid.domain, domain, f"Domain does not match: {jid.domain}")
        if resource is not None:
            self.assertEqual(
                jid.resource, resource, f"Resource does not match: {jid.resource}"
            )
        if bare is not None:
            self.assertEqual(jid.bare, bare, f"Bare JID does not match: {jid.bare}")
        if full is not None:
            self.assertEqual(jid.full, full, f"Full JID does not match: {jid.full}")
        if string is not None:
            self.assertEqual(str(jid), string, f"String does not match: {jid!s}")

    def check_roster(
        self,
        owner: JidStr,
        jid: JID,
        name: str | None = None,
        subscription: str | None = None,
        afrom: OptJidStr = None,
        ato: OptJidStr = None,
        pending_out: str | None = None,
        pending_in: str | None = None,
        groups: str | None = None,
    ) -> None:
        roster = self.xmpp.roster[owner][jid]
        if name is not None:
            self.assertEqual(
                roster["name"], name, "Incorrect name value: {}".format(roster["name"])
            )
        if subscription is not None:
            self.assertEqual(
                roster["subscription"],
                subscription,
                "Incorrect subscription: {}".format(roster["subscription"]),
            )
        if afrom is not None:
            self.assertEqual(
                roster["from"], afrom, "Incorrect from state: {}".format(roster["from"])
            )
        if ato is not None:
            self.assertEqual(
                roster["to"], ato, "Incorrect to state: {}".format(roster["to"])
            )
        if pending_out is not None:
            self.assertEqual(
                roster["pending_out"],
                pending_out,
                "Incorrect pending_out state: {}".format(roster["pending_out"]),
            )
        if pending_in is not None:
            self.assertEqual(
                roster["pending_in"],
                pending_out,
                "Incorrect pending_in state: {}".format(roster["pending_in"]),
            )
        if groups is not None:
            self.assertEqual(
                roster["groups"],
                groups,
                "Incorrect groups: {}".format(roster["groups"]),
            )

    # ------------------------------------------------------------------
    # Methods for comparing stanza objects to XML strings

    def check(
        self,
        stanza: ElementBase,
        criteria: str | ElementBase,
        method: TestMethod = "exact",
        defaults: list[str] | None = None,
        use_values: bool = True,
    ) -> None:
        """
        Create and compare several stanza objects to a correct XML string.

        If use_values is False, tests using stanza.values will not be used.

        Some stanzas provide default values for some interfaces, but
        these defaults can be problematic for testing since they can easily
        be forgotten when supplying the XML string. A list of interfaces that
        use defaults may be provided and the generated stanzas will use the
        default values for those interfaces if needed.

        However, correcting the supplied XML is not possible for interfaces
        that add or remove XML elements. Only interfaces that map to XML
        attributes may be set using the defaults parameter. The supplied XML
        must take into account any extra elements that are included by default.

        Arguments:
            stanza       -- The stanza object to test.
            criteria     -- An expression the stanza must match against.
            method       -- The type of matching to use; one of:
                            'exact', 'mask', 'id', 'xpath', and 'stanzapath'.
                            Defaults to the value of self.match_method.
            defaults     -- A list of stanza interfaces that have default
                            values. These interfaces will be set to their
                            defaults for the given and generated stanzas to
                            prevent unexpected test failures.
            use_values   -- Indicates if testing using stanza.values should
                            be used. Defaults to True.
        """
        if method is None and hasattr(self, "match_method"):
            method = getattr(self, "match_method")

        if method != "exact":
            matchers = {
                "stanzapath": StanzaPath,
                "xpath": MatchXPath,
                "mask": MatchXMLMask,
                "idsender": MatchIDSender,
                "id": MatcherId,
            }
            Matcher = matchers.get(method)
            if Matcher is None:
                raise ValueError("Unknown matching method.")
            test = Matcher(criteria)  # type:ignore
            self.assertTrue(
                test.match(stanza),  # type:ignore
                f"Stanza did not match using {method} method:\n"
                + f"Criteria:\n{criteria!s}\n"
                + f"Stanza:\n{stanza!s}",
            )
        else:
            stanza_class = stanza.__class__
            # Hack to preserve namespaces instead of having jabber:client
            # everywhere.
            old_ns = stanza_class.namespace
            stanza_class.namespace = stanza.namespace
            if not isinstance(criteria, ElementBase):
                xml = self.parse_xml(criteria)
            else:
                xml = criteria.xml

            # Ensure that top level namespaces are used, even if they
            # were not provided.
            self.fix_namespaces(stanza.xml)
            self.fix_namespaces(xml)

            stanza2 = stanza_class(xml=xml)

            if use_values:
                # Using stanza.values will add XML for any interface that
                # has a default value. We need to set those defaults on
                # the existing stanzas and XML so that they will compare
                # correctly.
                default_stanza = stanza_class()
                if defaults is None:
                    if stanza_class is Message:
                        defaults = ["type"]
                    elif stanza_class is Presence:
                        defaults = ["priority"]
                    else:
                        defaults = []
                for interface in defaults:
                    stanza[interface] = stanza[interface]
                    stanza2[interface] = stanza2[interface]
                    # Can really only automatically add defaults for top
                    # level attribute values. Anything else must be accounted
                    # for in the provided XML string.
                    if (
                        interface not in xml.attrib
                        and interface in default_stanza.xml.attrib
                    ):
                        value = default_stanza.xml.attrib[interface]
                        xml.attrib[interface] = value

                values = stanza2.values
                stanza3 = stanza_class()
                stanza3.values = values
                result = self.compare(xml, stanza.xml, stanza2.xml, stanza3.xml)
            else:
                result = self.compare(xml, stanza.xml, stanza2.xml)
            stanza_class.namespace = old_ns

            if result:
                debug = ""
            else:
                debug = f"{'three' if use_values else 'two'} methods for creating stanzas do not match.\n"
                debug += f"Given XML:\n{highlight(tostring_fmt(xml))}\n"
                debug += f"Given stanza:\n{highlight(tostring_fmt(stanza.xml))}\n"
                diff1 = "\n".join(diff(xml, stanza.xml))
                if diff1:
                    debug += f"diff:\n{diff1}\n"
                debug += f"Generated stanza:\n{highlight(tostring_fmt(stanza2.xml))}\n"
                diff2 = "\n".join(diff(xml, stanza2.xml))
                if diff2:
                    debug += f"diff:\n{diff2}\n"
                if use_values:
                    debug += f"Second generated stanza:\n{highlight(tostring_fmt(stanza3.xml))}\n"
                    diff3 = "\n".join(diff(xml, stanza3.xml))
                    if diff3:
                        debug += f"diff:\n{diff3}\n"

            self.assertTrue(result, debug)

    # ------------------------------------------------------------------
    # Methods for simulating stanza streams.

    def stream_disconnect(self) -> None:
        """
        Simulate a stream disconnection.
        """
        if self.xmpp and self.xmpp.socket is not None:
            self.xmpp.socket.disconnect_error()  # type:ignore

    def stream_start(
        self,
        mode: str = "client",
        skip: bool = True,
        header: str | None = None,
        socket: str = "mock",
        jid: str = "tester@localhost/resource",
        password: str = "test",
        server: str = "localhost",
        port: int = 5222,
        sasl_mech: Iterable[str] | None = None,
        plugins: Iterable[str] | None = None,
        plugin_config: dict[str, dict[str, object]] = {},
    ) -> None:
        """
        Initialize an XMPP client or component using a dummy XML stream.

        Arguments:
            mode     -- Either 'client' or 'component'. Defaults to 'client'.
            skip     -- Indicates if the first item in the sent queue (the
                        stream header) should be removed. Tests that wish
                        to test initializing the stream should set this to
                        False. Otherwise, the default of True should be used.
            socket   -- Either 'mock' or 'live' to indicate if the socket
                        should be a dummy, mock socket or a live, functioning
                        socket. Defaults to 'mock'.
            jid      -- The JID to use for the connection.
                        Defaults to 'tester@localhost/resource'.
            password -- The password to use for the connection.
                        Defaults to 'test'.
            server   -- The name of the XMPP server. Defaults to 'localhost'.
            port     -- The port to use when connecting to the server.
                        Defaults to 5222.
            plugins  -- List of plugins to register. By default, all plugins
                        are loaded.
        """
        if not plugin_config:
            plugin_config = {}

        self.mode = mode
        if mode == "client":
            self.xmpp = ClientXMPP(
                jid, password, sasl_mech=sasl_mech, plugin_config=plugin_config
            )
        elif mode == "component":
            self.xmpp = ComponentXMPP(
                jid, password, server, port, plugin_config=plugin_config
            )
        else:
            raise ValueError("Unknown XMPP connection mode.")
        self.xmpp._always_send_everything = True

        self.xmpp.connection_made(TestTransport(self.xmpp))  # type:ignore[arg-type]
        self.xmpp.session_bind_event.set()
        # Remove unique ID prefix to make it easier to test
        self.xmpp.default_lang = None
        self.xmpp.peer_default_lang = None

        _id = 0

        def new_id() -> str:
            nonlocal _id
            _id += 1
            return str(_id)

        self.xmpp.new_id = new_id  # type:ignore

        # Must have the stream header ready for the asyncio loop to work.
        if not header:
            header = self.xmpp.stream_header

        self.xmpp.data_received(header)
        self.wait_for_send_queue()

        if skip:
            assert isinstance(self.xmpp.socket, TestSocket)
            self.xmpp.socket.next_sent()
            if mode == "component":
                self.xmpp.socket.next_sent()

        if plugins is None:
            self.xmpp.register_plugins()
        else:
            for plugin in plugins:
                self.xmpp.register_plugin(plugin)

        # Some plugins require messages to have ID values. Set
        # this to True in tests related to those plugins.
        self.xmpp.use_message_ids = False
        self.xmpp.use_presence_ids = False

    def make_header(
        self,
        sto: JidStr = "",
        sfrom: JidStr = "",
        sid: str = "",
        stream_ns: str = "http://etherx.jabber.org/streams",
        default_ns: str = "jabber:client",
        default_lang: str = "en",
        version: str = "1.0",
        xml_header: bool = True,
    ) -> str:
        """
        Create a stream header to be received by the test XMPP agent.

        The header must be saved and passed to stream_start.

        Arguments:
            sto        -- The recipient of the stream header.
            sfrom      -- The agent sending the stream header.
            sid        -- The stream's id.
            stream_ns  -- The namespace of the stream's root element.
            default_ns -- The default stanza namespace.
            version    -- The stream version.
            xml_header -- Indicates if the XML version header should be
                          appended before the stream header.
        """
        header = "<stream:stream %s>"
        parts = []
        if xml_header:
            header = '<?xml version="1.0"?>' + header
        if sto:
            parts.append(f'to="{sto}"')
        if sfrom:
            parts.append(f'from="{sfrom}"')
        if sid:
            parts.append(f'id="{sid}"')
        if default_lang:
            parts.append(f'xml:lang="{default_lang}"')
        parts.append(f'version="{version}"')
        parts.append(f'xmlns:stream="{stream_ns}"')
        parts.append(f'xmlns="{default_ns}"')
        return header % " ".join(parts)

    def recv(
        self,
        data: str | bytes,
        defaults: list[str] | None = None,
        method: TestMethod = "exact",
        use_values: bool = True,
        timeout: float = 1,
    ) -> None:
        """
        Pass data to the dummy XMPP client as if it came from an XMPP server.

        If using a live connection, verify what the server has sent.

        Arguments:
            data         -- If a dummy socket is being used, the XML that is to
                            be received next. Otherwise it is the criteria used
                            to match against live data that is received.
            defaults     -- A list of stanza interfaces with default values that
                            may interfere with comparisons.
            method       -- Select the type of comparison to use for
                            verifying the received stanza. Options are 'exact',
                            'id', 'stanzapath', 'xpath', and 'mask'.
                            Defaults to the value of self.match_method.
            use_values   -- Indicates if stanza comparisons should test using
                            stanza.values. Defaults to True.
            timeout      -- Time to wait in seconds for data to be received by
                            a live connection.
        """
        self.wait_()
        self.xmpp.data_received(data)
        self.wait_()

    def recv_header(
        self,
        sto: JidStr = "",
        sfrom: JidStr = "",
        sid: str = "",
        stream_ns: str = "http://etherx.jabber.org/streams",
        default_ns: str = "jabber:client",
        version: str = "1.0",
        xml_header: bool = False,
        timeout: float = 1,
    ) -> None:
        """
        Check that a given stream header was received.

        Arguments:
            sto        -- The recipient of the stream header.
            sfrom      -- The agent sending the stream header.
            sid        -- The stream's id. Set to None to ignore.
            stream_ns  -- The namespace of the stream's root element.
            default_ns -- The default stanza namespace.
            version    -- The stream version.
            xml_header -- Indicates if the XML version header should be
                          appended before the stream header.
            timeout    -- Length of time to wait in seconds for a
                          response.
        """
        header = self.make_header(
            sto,
            sfrom,
            sid,
            stream_ns=stream_ns,
            default_ns=default_ns,
            version=version,
            xml_header=xml_header,
        )
        assert isinstance(self.xmpp.socket, TestTransport)
        recv_header = self.xmpp.socket.next_recv(timeout)
        if recv_header is None:
            raise ValueError("Socket did not return data.")

        # Apply closing elements so that we can construct
        # XML objects for comparison.
        header2 = header + "</stream:stream>"
        recv_header2 = recv_header + "</stream:stream>"

        xml = self.parse_xml(header2)
        recv_xml = self.parse_xml(recv_header2)

        if sid is None and "id" in recv_xml.attrib:
            # Ignore the id sent by the server since
            # we can't know in advance what it will be.
            del recv_xml.attrib["id"]

        # Ignore the xml:lang attribute for now.
        if "xml:lang" in recv_xml.attrib:
            del recv_xml.attrib["xml:lang"]
        xml_ns = "http://www.w3.org/XML/1998/namespace"
        if f"{{{xml_ns}}}lang" in recv_xml.attrib:
            del recv_xml.attrib[f"{{{xml_ns}}}lang"]

        if list(recv_xml):
            # We received more than just the header
            for xml in recv_xml:
                self.xmpp.data_received(tostring(xml))

            attrib = recv_xml.attrib
            recv_xml.clear()
            recv_xml.attrib = attrib

        self.assertTrue(
            self.compare(xml, recv_xml),
            "Stream headers do not match:\nDesired:\n{}\nReceived:\n{}".format(
                f"{xml.tag} {xml.attrib}",
                f"{recv_xml.tag} {recv_xml.attrib}",
            ),
        )

    def recv_feature(
        self,
        data: str | bytes,
        method: TestMethod | None = "mask",
        use_values: bool = True,
        timeout: float = 1,
    ) -> None:
        """ """
        if method is None and hasattr(self, "match_method"):
            method = getattr(self, "match_method")
        assert isinstance(self.xmpp.socket, TestTransport)

        self.xmpp.socket.data_received(data)

    def send_header(
        self,
        sto: JidStr = "",
        sfrom: JidStr = "",
        sid: str = "",
        stream_ns: str = "http://etherx.jabber.org/streams",
        default_ns: str = "jabber:client",
        default_lang: str = "en",
        version: str = "1.0",
        xml_header: bool = False,
        timeout: float = 1,
    ) -> None:
        """
        Check that a given stream header was sent.

        Arguments:
            sto        -- The recipient of the stream header.
            sfrom      -- The agent sending the stream header.
            sid        -- The stream's id.
            stream_ns  -- The namespace of the stream's root element.
            default_ns -- The default stanza namespace.
            version    -- The stream version.
            xml_header -- Indicates if the XML version header should be
                          appended before the stream header.
            timeout    -- Length of time to wait in seconds for a
                          response.
        """
        header = self.make_header(
            sto,
            sfrom,
            sid,
            stream_ns=stream_ns,
            default_ns=default_ns,
            default_lang=default_lang,
            version=version,
            xml_header=xml_header,
        )
        assert isinstance(self.xmpp.socket, TestSocket)
        sent_header = self.xmpp.socket.next_sent(timeout)
        if sent_header is None:
            raise ValueError("Socket did not return data.")

        # Apply closing elements so that we can construct
        # XML objects for comparison.
        header2 = header + "</stream:stream>"
        sent_header2 = sent_header + b"</stream:stream>"

        xml = self.parse_xml(header2)
        sent_xml = self.parse_xml(sent_header2)

        self.assertTrue(
            self.compare(xml, sent_xml),
            f"Stream headers do not match:\nDesired:\n{header}\nSent:\n{sent_header}",
        )

    def send_feature(
        self,
        data: str,
        method: TestMethod = "mask",
        use_values: bool = True,
        timeout: float = 1,
    ) -> None:
        """ """
        assert isinstance(self.xmpp.socket, TestTransport)
        sent_data = self.xmpp.socket.next_sent(timeout)
        xml = self.parse_xml(data)
        sent_xml = self.parse_xml(sent_data)
        if sent_data is None:
            self.fail("No stanza was sent.")
        if method == "exact":
            self.assertTrue(
                self.compare(xml, sent_xml),
                f"Features do not match.\nDesired:\n{highlight(tostring(xml))}\nReceived:\n{highlight(tostring(sent_xml))}",
            )
        elif method == "mask":
            matcher = MatchXMLMask(xml)  # type:ignore
            self.assertTrue(
                matcher.match(sent_xml),  # type:ignore
                f"Stanza did not match using {method} method:\n"
                + f"Criteria:\n{highlight(tostring(xml))}\n"
                + f"Stanza:\n{highlight(tostring(sent_xml))}",
            )
        else:
            raise ValueError(f"Unknown matching method: {method}")

    def send(
        self,
        data: str | None,
        defaults: list[str] | None = None,
        use_values: bool = True,
        timeout: float = 0.5,
        method: TestMethod = "exact",
    ) -> None:
        """
        Check that the XMPP client sent the given stanza XML.

        Extracts the next sent stanza and compares it with the given
        XML using check.

        Arguments:
            stanza_class -- The class of the sent stanza object.
            data         -- The XML string of the expected Message stanza,
                            or an equivalent stanza object.
            use_values   -- Modifies the type of tests used by check_message.
            defaults     -- A list of stanza interfaces that have defaults
                            values which may interfere with comparisons.
            timeout      -- Time in seconds to wait for a stanza before
                            failing the check.
            method       -- Select the type of comparison to use for
                            verifying the sent stanza. Options are 'exact',
                            'id', 'stanzapath', 'xpath', and 'mask'.
                            Defaults to the value of self.match_method.
        """
        self.wait_for_send_queue()
        assert isinstance(self.xmpp.socket, TestSocket)
        sent = self.xmpp.socket.next_sent(timeout)
        if data is None and sent is None:
            return
        if data is None and sent is not None:
            self.fail(f"Stanza data was sent: {sent}")
        if sent is None:
            self.fail("No stanza was sent.")

        xml = self.parse_xml(sent)
        self.fix_namespaces(xml)
        sent = self.xmpp._build_stanza(xml)
        self.check(sent, data, method=method, defaults=defaults, use_values=use_values)

    def wait_for_send_queue(self) -> None:
        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(self.xmpp.run_filters(), loop=loop)
        queue = self.xmpp.waiting_queue
        loop.run_until_complete(queue.join())
        future.cancel()

    def wait_(self, timeout: int | float | None = None) -> None:
        async def yield_some() -> None:
            for i in range(100):
                await asyncio.sleep(0)

        loop = asyncio.get_event_loop()
        if timeout is not None:
            loop.run_until_complete(asyncio.sleep(timeout))
        else:
            loop.run_until_complete(yield_some())

    def run_coro(self, coro: Awaitable[T]) -> T:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

    def stream_close(self) -> None:
        """
        Disconnect the dummy XMPP client.

        Can be safely called even if stream_start has not been called.

        Must be placed in the tearDown method of a test class to ensure
        that the XMPP client is disconnected after an error.
        """
        if hasattr(self, "xmpp") and self.xmpp is not None:
            self.xmpp.data_received(self.xmpp.stream_footer)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.xmpp.disconnect(wait=0.01))

    # ------------------------------------------------------------------
    # XML Comparison and Cleanup

    def fix_namespaces(self, xml: ET.Element, ns: str | None = None) -> None:
        """
        Assign a namespace to an element and any children that
        don't have a namespace.

        Arguments:
            xml -- The XML object to fix.
            ns  -- The namespace to add to the XML object.
        """
        if ns is None:
            ns = "jabber:client"
            if self.xmpp:
                ns = self.xmpp.default_ns
        if xml.tag.startswith("{"):
            return
        xml.tag = f"{{{ns}}}{xml.tag}"
        for child in xml:
            self.fix_namespaces(child, ns)

    def compare(self, xml: ET.Element, *others: ET.Element) -> bool:
        """
        Compare XML objects.

        Arguments:
            xml    -- The XML object to compare against.
            *other -- The list of XML objects to compare.
        """
        if not others:
            return False

        # Compare multiple objects
        if len(others) > 1:
            return all(self.compare(xml, xml2) for xml2 in others)

        other = others[0]

        # Step 1: Check tags
        if xml.tag != other.tag:
            return False

        # Step 2: Check attributes
        if xml.attrib != other.attrib:
            return False

        # Step 3: Check text
        if xml.text is None:
            xml.text = ""
        if other.text is None:
            other.text = ""
        xml.text = xml.text.strip()
        other.text = other.text.strip()

        if xml.text != other.text:
            return False

        # Step 4: Check children count
        if len(list(xml)) != len(list(other)):
            return False

        # Step 5: Recursively check children
        for child in xml:
            child2s = other.findall(f"{child.tag}")
            if child2s is None:
                return False
            for child2 in child2s:
                if self.compare(child, child2):
                    break
            else:
                return False

        # Step 6: Recursively check children the other way.
        for child in other:
            child2s = xml.findall(f"{child.tag}")
            if child2s is None:
                return False
            for child2 in child2s:
                if self.compare(child, child2):
                    break
            else:
                return False

        # Everything matches
        return True

    def tearDown(self) -> None:
        self.stream_close()
        if getattr(self, "mode", None) == "component":
            Error.namespace = "jabber:client"
            for st in Message, Iq, Presence:
                register_stanza_plugin(st, Error)


@atexit.register
def cleanup() -> None:
    with contextlib.suppress(BaseException):
        loop = asyncio.get_event_loop()
        loop.close()


def diff(xml1: Element, xml2: Element) -> Iterator[str]:
    yield from colored_diff(
        difflib.unified_diff(
            tostring_fmt(xml1).splitlines(), tostring_fmt(xml2).splitlines()
        )
    )


def colored_diff(diff_lines: Iterable[str]) -> Iterator[str]:
    if os.getenv("SLIXTEST_MONOCHROME") in ("0", "false"):
        yield from diff_lines
    for line in diff_lines:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            yield f"{GREEN}{line}{RESET}"
        elif line.startswith("-"):
            yield f"{RED}{line}{RESET}"
        else:
            yield line


RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"
