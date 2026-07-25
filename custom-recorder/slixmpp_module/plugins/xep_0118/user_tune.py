# Slixmpp: The Slick XMPP Library
# Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

import logging

from asyncio import Future
from slixmpp.plugins.base import BasePlugin
from slixmpp.plugins.xep_0118 import stanza, UserTune


log = logging.getLogger(__name__)


class XEP_0118(BasePlugin):

    """
    XEP-0118: User Tune
    """

    name = 'xep_0118'
    description = 'XEP-0118: User Tune'
    dependencies = {'xep_0163'}
    stanza = stanza

    def plugin_end(self):
        self.xmpp.plugin['xep_0030'].del_feature(feature=UserTune.namespace)
        self.xmpp.plugin['xep_0163'].remove_interest(UserTune.namespace)

    def session_bind(self, jid):
        self.xmpp.plugin['xep_0163'].register_pep('user_tune', UserTune)

    def publish_tune(self, *, artist: str | None = None,
                     length: int | None =None, rating: int | None = None,
                     source: str | None = None, title: str | None = None,
                     track: str | None = None, uri: str | None = None,
                     **pubsubkwargs) -> Future:
        """
        Publish the user's current tune.

        :param artist: The artist or performer of the song.
        :param length: The length of the song in seconds.
        :param rating: The user's rating of the song (from 1 to 10)
        :param source: The album name, website, or other source of the song.
        :param title: The title of the song.
        :param track: The song's track number, or other unique identifier.
        :param uri: A URL to more information about the song.
        """
        tune = UserTune()
        tune['artist'] = artist
        tune['length'] = length
        tune['rating'] = rating
        tune['source'] = source
        tune['title'] = title
        tune['track'] = track
        tune['uri'] = uri
        return self.xmpp.plugin['xep_0163'].publish(
            tune,
            node=UserTune.namespace,
            **pubsubkwargs
        )

    def stop(self, **pubsubkwargs) -> Future:
        """
        Clear existing user tune information to stop notifications.
        """
        tune = UserTune()
        return self.xmpp.plugin['xep_0163'].publish(
            tune,
            node=UserTune.namespace,
            **pubsubkwargs
        )
