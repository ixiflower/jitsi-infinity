# Copyright © 2025 Mathieu Pasquet
# This file is part of slixmpp
# See the file LICENSE for copying permission.
import json
import logging
from datetime import datetime
from urllib.parse import urlparse

from slixmpp import JID
from slixmpp.plugins import BasePlugin, xep_0082
from dataclasses import dataclass

log = logging.getLogger(__name__)


class AiohttpNotFound(Exception):
    pass


@dataclass
class ExternalStatus:
    planned: bool | None
    beginning: datetime
    expected_end: datetime | None
    message: dict[str, str] | None


class XEP_0455(BasePlugin):
    """
    XEP-0455: Service Outage Status
    """
    name = 'xep_0455'
    description = 'XEP-0455: Service Outage Status'
    dependencies = {'xep_0128', 'xep_0030', 'xep_0082'}
    namespace = 'urn:xmpp:sos:0'

    async def get_external_status_addresses(self, domain: JID | None = None,
                                            **iqkwargs) -> list[str]:
        """Return the list of external status addresses for this domain.

        :param domain: Domain to disco to find a service.
        """
        if domain is None:
            domain = JID(self.xmpp.boundjid.host)

        uris = []
        results = await self.xmpp.plugin['xep_0030'].get_info(jid=domain,
            **iqkwargs
        )

        disco = results.get_plugin('disco_info', check=True)
        if disco is None or 'forms' not in disco:
            return uris
        forms = disco['forms']
        if not forms:
            return uris
        field = 'external-status-addresses'
        for form in forms:
            values = form.get_values()
            if values.get('FORM_TYPE') == [self.namespace]:
                uris.extend(values.get(field, []))
        return uris

    @classmethod
    async def fetch_status(cls, addresses: str | list[str]) -> dict:
        """
        Get the external status from a list of addresses.
        Only works with http/https for now and stops on the first status
        fetched successfully.

        :param addresses: address or list of addresses to fetch the status from.
        """
        try:
            from aiohttp import ClientSession
        except ImportError:
            raise AiohttpNotFound("aiohttp was not found, unable to download statuses")

        if not isinstance(addresses, list):
            addresses = [addresses]

        async with ClientSession(headers={'User-Agent': 'slixmpp'}) as session:
            for address in addresses:
                scheme, *_ = urlparse(address)
                if scheme not in ('http', 'https'):
                    continue
                response = await session.get(address, timeout=60)
                if response.status >= 400:
                    log.debug(f'Server "{address}" answered with code {response.status}')
                    continue
                text = await response.text()
                status = cls._parse_status(text)
                if status is not None:
                    return status

    @staticmethod
    def _parse_status(raw: str) -> ExternalStatus | None:
        """
        Parse a status json payload. Return None if the required (beginning)
        field is not found or not parseable.

        Returns a dataclass with the fields.
        """
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            log.error('Unable to parse the external status: {text}')
            return None
        if not payload:
            return None
        beginning_raw = payload.get('beginning')
        try:
            beginning = xep_0082.parse(beginning_raw)
        except (ValueError, TypeError):
            log.error(f'Bad value for beginning: "{beginning_raw}"')
            return None

        expected_end_raw = payload.get('expected_end')
        expected_end = None
        try:
            expected_end = xep_0082.parse(expected_end_raw)
        except (ValueError, TypeError):
            log.error(f'Bad value for expected end: "{expected_end_raw}"')

        planned_raw = payload.get('planned')
        planned = planned_raw if isinstance(planned_raw, bool) else None

        message_raw = payload.get('message')
        message = None
        if isinstance(message_raw, dict):
            message = {}
            for key, value in message_raw.items():
                if isinstance(key, str) and isinstance(value, str):
                    message[key] = value
        return ExternalStatus(planned, beginning, expected_end, message)
