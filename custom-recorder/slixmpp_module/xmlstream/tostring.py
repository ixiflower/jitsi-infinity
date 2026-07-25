# slixmpp.xmlstream.tostring
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# This module converts XML objects into Unicode strings and
# intelligently includes namespaces only when necessary to
# keep the output readable.
# Part of Slixmpp: The Slick XMPP Library
# :copyright: (c) 2011 Nathanael C. Fritz
# :license: MIT, see LICENSE for more details
from __future__ import annotations

from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

if TYPE_CHECKING:
    from slixmpp.xmlstream import XMLStream

XML_NS = "http://www.w3.org/XML/1998/namespace"


def tostring(
    xml: Element | None = None,
    xmlns: str = "",
    stream: XMLStream | None = None,
    outbuffer: str = "",
    top_level: bool = False,
    open_only: bool = False,
    namespaces: set[str] | None = None,
) -> str:
    """Serialize an XML object to a Unicode string.

    If an outer xmlns is provided using ``xmlns``, then the current element's
    namespace will not be included if it matches the outer namespace. An
    exception is made for elements that have an attached stream, and appear
    at the stream root.

    :param XML xml: The XML object to serialize.
    :param string xmlns: Optional namespace of an element wrapping the XML
                         object.
    :param stream: The XML stream that generated the XML object.
    :param string outbuffer: Optional buffer for storing serializations
                             during recursive calls.
    :param bool top_level: Indicates that the element is the outermost
                           element.
    :param set namespaces: Track which namespaces are in active use so
                           that new ones can be declared when needed.

    :type xml: :py:class:`~xml.etree.ElementTree.Element`
    :type stream: :class:`~slixmpp.xmlstream.xmlstream.XMLStream`

    :rtype: Unicode string
    """
    if xml is None:
        return ""
    # Add previous results to the start of the output.
    output = [outbuffer]

    # Extract the element's tag name.
    tag_split = xml.tag.split("}", 1)
    tag_name = tag_split[-1]

    # Extract the element's namespace if it is defined.
    tag_xmlns = tag_split[0][1:] if "}" in xml.tag else ""

    default_ns = ""
    stream_ns = ""
    use_cdata = False

    if stream:
        default_ns = stream.default_ns
        stream_ns = stream.stream_ns
        use_cdata = stream.use_cdata

    # Output the tag name and derived namespace of the element.
    namespace = ""
    if (
        tag_xmlns and (top_level and tag_xmlns not in [default_ns, xmlns, stream_ns])
    ) or (not top_level and tag_xmlns != xmlns):
        namespace = f' xmlns="{tag_xmlns}"'
    if stream and tag_xmlns in stream.namespace_map:
        mapped_namespace = stream.namespace_map[tag_xmlns]
        if mapped_namespace:
            tag_name = f"{mapped_namespace}:{tag_name}"
            namespace = f' xmlns="{tag_xmlns}"'
    if stream and tag_xmlns in stream.namespace_map:
        mapped_namespace = stream.namespace_map[tag_xmlns]
        if mapped_namespace:
            tag_name = f"{mapped_namespace}:{tag_name}"
    output.append(f"<{tag_name}")
    output.append(namespace)

    # Output escaped attribute values.
    new_namespaces = set()
    for attrib, value in xml.attrib.items():
        value = escape(value, use_cdata)
        if "}" not in attrib:
            output.append(f' {attrib}="{value}"')
        else:
            attrib_split = attrib.split("}")
            attrib_ns = attrib_split[0][1:]
            attrib = attrib_split[1]
            if attrib_ns == XML_NS:
                output.append(f' xml:{attrib}="{value}"')
            elif stream and attrib_ns in stream.namespace_map:
                mapped_ns = stream.namespace_map[attrib_ns]
                if mapped_ns:
                    if namespaces is None:
                        namespaces = set()
                    if attrib_ns not in namespaces:
                        namespaces.add(attrib_ns)
                        new_namespaces.add(attrib_ns)
                        output.append(f' xmlns:{mapped_ns}="{attrib_ns}"')
                    output.append(f' {mapped_ns}:{attrib}="{value}"')

    if open_only:
        # Only output the opening tag, regardless of content.
        output.append(">")
        return "".join(output)

    if len(xml) or xml.text:
        # If there are additional child elements to serialize.
        output.append(">")
        if xml.text:
            output.append(escape(xml.text, use_cdata))
        if len(xml):
            for child in xml:
                output.append(tostring(child, tag_xmlns, stream, namespaces=namespaces))
        output.append(f"</{tag_name}>")
    elif xml.text:
        # If we only have text content.
        output.append(f">{escape(xml.text, use_cdata)}</{tag_name}>")
    else:
        # Empty element.
        output.append(" />")
    if xml.tail:
        # If there is additional text after the element.
        output.append(escape(xml.tail, use_cdata))
    for ns in new_namespaces:
        # Remove namespaces introduced in this context. This is necessary
        # because the namespaces object continues to be shared with other
        # contexts.
        if namespaces is not None:
            namespaces.remove(ns)
    return "".join(output)


def tostring_fmt(
    xml: Element | None = None,
    xmlns: str = "",
    stream: XMLStream | None = None,
    outbuffer: str = "",
    top_level: bool = False,
    namespaces: set[str] | None = None,
    indent: str = "",
) -> str:
    """Serialize an XML object to a Unicode string, but with extra whitespace
    for readability, and attributes/children sorted lexicographically to make
    diffs more readable.

    Code is duplicated from tostring to avoid making it even more complex than
    it is, as well as to keep the additions away from the hot path.

    If an outer xmlns is provided using ``xmlns``, then the current element's
    namespace will not be included if it matches the outer namespace. An
    exception is made for elements that have an attached stream, and appear
    at the stream root.

    :param XML xml: The XML object to serialize.
    :param string xmlns: Optional namespace of an element wrapping the XML
                         object.
    :param stream: The XML stream that generated the XML object.
    :param string outbuffer: Optional buffer for storing serializations
                             during recursive calls.
    :param bool top_level: Indicates that the element is the outermost
                           element.
    :param set namespaces: Track which namespaces are in active use so
                           that new ones can be declared when needed.
    :param indent: Level of indentation for the current element.

    :type xml: :py:class:`~xml.etree.ElementTree.Element`
    :type stream: :class:`~slixmpp.xmlstream.xmlstream.XMLStream`

    :rtype: Unicode string
    """
    if xml is None:
        return ""
    # Add previous results to the start of the output.
    output = [outbuffer]

    # Extract the element's tag name.
    tag_split = xml.tag.split("}", 1)
    tag_name = tag_split[-1]

    # Extract the element's namespace if it is defined.
    tag_xmlns = tag_split[0][1:] if "}" in xml.tag else ""

    default_ns = ""
    stream_ns = ""
    use_cdata = False

    if stream:
        default_ns = stream.default_ns
        stream_ns = stream.stream_ns
        use_cdata = stream.use_cdata

    # Output the tag name and derived namespace of the element.
    namespace = ""
    if (
        tag_xmlns and (top_level and tag_xmlns not in [default_ns, xmlns, stream_ns])
    ) or (not top_level and tag_xmlns != xmlns):
        namespace = f' xmlns="{tag_xmlns}"'
    if stream and tag_xmlns in stream.namespace_map:
        mapped_namespace = stream.namespace_map[tag_xmlns]
        if mapped_namespace:
            tag_name = f"{mapped_namespace}:{tag_name}"
    if indent:
        output.append(indent)
    output.append(f"<{tag_name}")
    output.append(namespace)

    # Output escaped attribute values (sorted lexicographically).
    new_namespaces = set()
    for attrib, value in sorted(xml.attrib.items()):
        value = escape(value, use_cdata)
        if "}" not in attrib:
            output.append(f' {attrib}="{value}"')
        else:
            attrib_split = attrib.split("}")
            attrib_ns = attrib_split[0][1:]
            attrib = attrib_split[1]
            if attrib_ns == XML_NS:
                output.append(f' xml:{attrib}="{value}"')
            elif stream and attrib_ns in stream.namespace_map:
                mapped_ns = stream.namespace_map[attrib_ns]
                if mapped_ns:
                    if namespaces is None:
                        namespaces = set()
                    if attrib_ns not in namespaces:
                        namespaces.add(attrib_ns)
                        new_namespaces.add(attrib_ns)
                        output.append(f' xmlns:{mapped_ns}="{attrib_ns}"')
                    output.append(f' {mapped_ns}:{attrib}="{value}"')
    child_indent = indent

    if len(xml) or (xml.text and xml.text.strip()):
        child_indent += "  "
        # If there are additional child elements to serialize.
        output.append(">")
        if xml.text:
            output.append(escape(xml.text.strip(), use_cdata))
        if len(xml):
            output.append("\n")
            # Sort child elements lexicographically by tag name
            for child in sorted(xml, key=lambda e: e.tag):
                output.append(
                    tostring_fmt(
                        child,
                        tag_xmlns,
                        stream,
                        namespaces=namespaces,
                        indent=child_indent,
                    )
                )
            output.append(indent)
        output.append(f"</{tag_name}>")
    elif xml.text:
        # If we only have text content.
        output.append(f">{escape(xml.text, use_cdata)}</{tag_name}>")
    else:
        # Empty element.
        output.append(" />")
    output.append("\n")
    if xml.tail and xml.tail.strip():
        # If there is additional text after the element.
        output.append(escape(xml.tail.strip(), use_cdata))
    for ns in new_namespaces:
        # Remove namespaces introduced in this context. This is necessary
        # because the namespaces object continues to be shared with other
        # contexts.
        if namespaces is not None:
            namespaces.remove(ns)
    return "".join(output)


def escape(text: str, use_cdata: bool = False) -> str:
    """Convert special characters in XML to escape sequences.

    :param string text: The XML text to convert.
    :rtype: Unicode string
    """
    escapes = {"&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&apos;", '"': "&quot;"}

    if not use_cdata:
        return "".join(escapes.get(c, c) for c in text)
    else:
        escape_needed = False
        for c in text:
            if c in escapes:
                escape_needed = True
                break
        if escape_needed:
            escaped = map(lambda x: f"<![CDATA[{x}]]>", text.split("]]>"))
            return "<![CDATA[]]]><![CDATA[]>]]>".join(escaped)
        return text


def _get_highlight():  # noqa
    try:
        from pygments import highlight
        from pygments.formatters import Terminal256Formatter
        from pygments.lexers import get_lexer_by_name

        LEXER = get_lexer_by_name("xml")
        FORMATTER = Terminal256Formatter()

        class Highlighter:
            __slots__ = ["string"]

            def __init__(self, string: str) -> None:
                self.string = string

            def __str__(self) -> str:
                return highlight(str(self.string), LEXER, FORMATTER).strip()

        return Highlighter
    except ImportError:
        return lambda x: x


highlight = _get_highlight()
