from typing import ClassVar, cast

from slixmpp.plugins.xep_0428.stanza import Fallback
from slixmpp.stanza import Message
from slixmpp.xmlstream import ElementBase, register_stanza_plugin

NS = "urn:xmpp:reply:0"


class Reply(ElementBase):
    namespace = NS
    name = "reply"
    plugin_attrib = "reply"
    interfaces: ClassVar[set[str]] = {"id", "to"}

    def add_quoted_fallback(self, fallback: str, nickname: str | None = None) -> None:
        r"""
        Add plain text fallback for clients not implementing XEP-0461.


        ``msg["reply"].add_quoted_fallback("Some text", "Bob")`` will
        prepend ``> Bob:\n> Some text\n`` to the body of the message, and set the
        fallback_body attributes accordingly, so that clients implementing
        XEP-0461 can hide the fallback text.

        :param fallback: Body of the quoted message.
        :param nickname: Optional, nickname of the quoted participant.
        """
        msg = cast(Message, self.parent())  # type:ignore[misc]  # ty:ignore[call-non-callable]
        quoted = "\n".join("> " + x.strip() for x in fallback.split("\n")) + "\n"
        if nickname:
            quoted = "> " + nickname + ":\n" + quoted
        msg["body"] = quoted + msg["body"]
        fallback_elem = Fallback()
        fallback_elem["for"] = NS
        fallback_elem["body"]["start"] = 0
        fallback_elem["body"]["end"] = len(quoted)
        msg.append(fallback_elem)

    def get_fallback_body(self) -> str:
        """
        Get the string containing the fallback body from the parent.
        """
        msg = cast(Message, self.parent())  # type:ignore[misc]  # ty:ignore[call-non-callable]
        for fallback in msg["fallbacks"]:
            if fallback["for"] == NS:
                break
        else:
            return ""
        start = fallback["body"]["start"]
        end = fallback["body"]["end"]
        body = msg["body"]
        if start <= end:
            return body[start:end]
        else:
            return ""

    def strip_fallback_content(self) -> str:
        """
        Remove the fallback contents from the parent body.
        """
        msg = cast(Message, self.parent())  # type:ignore[misc]  # ty:ignore[call-non-callable]
        for fallback in msg["fallbacks"]:
            if fallback["for"] == NS:
                break
        else:
            return msg["body"]

        start = fallback["body"]["start"]
        end = fallback["body"]["end"]
        body = msg["body"]

        if 0 <= start < end <= len(body):
            return body[:start] + body[end:]
        else:
            return body


def register_plugins() -> None:
    register_stanza_plugin(Message, Reply)
