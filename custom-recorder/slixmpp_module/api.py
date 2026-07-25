from typing import Any, Callable
from asyncio import Future
from inspect import iscoroutinefunction
from slixmpp.xmlstream import JID

APIHandler = Callable[
    [JID | None, str | None, JID | None, Any],
    Any
]

class APIWrapper(object):
    """Slixmpp API wrapper.

    This class provide a shortened binding to access ``self.api`` from
    plugins without having to specify the plugin name or the global
    :class:`~.APIRegistry`.
    """

    def __init__(self, api: "APIRegistry", name: str) -> None:
        self.api = api
        self.name = name
        if name not in self.api.settings:
            self.api.settings[name] = {}

    @property
    def settings(self) -> dict:
        return self.api.settings[self.name]

    def register(
        self,
        handler: APIHandler | None,
        op: str,
        jid: JID | None = None,
        node: str | None = None,
        default: bool = False,
    ) -> None:
        return self.api.register(handler, self.name, op, jid, node, default)

    def register_default(
        self,
        handler: APIHandler | None,
        op: str,
        jid: JID | None = None,
        node: str | None = None,
    ) -> None:
        return self.api.register_default(handler, self.name, op)

    def run(
        self,
        op: str,
        jid: JID | None = None,
        node: str | None = None,
        ifrom: JID | None = None,
        args: Any = None,
    ) -> Future:
        return self.api.run(self.name, op, jid, node, ifrom, args)

    def restore_default(
        self,
        op: str,
        jid: JID | None = None,
        node: str | None = None,
    ) -> None:
        return self.api.restore_default(self.name, op, jid, node)

    def unregister(
        self,
        op: str,
        jid: JID | None = None,
        node: str | None = None,
    ) -> None:
        return self.api.unregister(self.name, op, jid, node)

    def __getitem__(self, op: str) -> APIHandler:
        def partial(jid=None, node=None, ifrom=None, args=None) -> Future:
            return self.api.run(self.name, op, jid, node, ifrom, args)
        return partial


class APIRegistry(object):
    """API Registry.

    This class is the global Slixmpp API registry, on which any handler will
    be registered.
    """

    def __init__(self, xmpp):
        self._handlers = {}
        self._handler_defaults = {}
        self.xmpp = xmpp
        self.settings = {}

    def _setup(self, ctype: str, op: str):
        """Initialize the API callback dictionaries.

        :param ctype: The name of the API to initialize.
        :param op: The API operation to initialize.
        """
        if ctype not in self.settings:
            self.settings[ctype] = {}
        if ctype not in self._handler_defaults:
            self._handler_defaults[ctype] = {}
        if ctype not in self._handlers:
            self._handlers[ctype] = {}
        if op not in self._handlers[ctype]:
            self._handlers[ctype][op] = {'global': None,
                                         'jid': {},
                                         'node': {}}

    def wrap(self, ctype: str) -> APIWrapper:
        """Return a wrapper object that targets a specific API."""
        return APIWrapper(self, ctype)

    def purge(self, ctype: str) -> None:
        """Remove all information for a given API."""
        del self.settings[ctype]
        del self._handler_defaults[ctype]
        del self._handlers[ctype]

    def run(self, ctype: str, op: str, jid: JID | None = None,
            node: str | None = None, ifrom: JID | None = None,
            args: Any = None) -> Future:
        """Execute an API callback, based on specificity.

        The API callback that is executed is chosen based on the combination
        of the provided JID and node:

        ====== ======= ===================
        JID     node    Handler
        ====== ======= ===================
        Given   Given   Node + JID handler
        Given   None    JID handler
        None    Given   Node handler
        None    None    Global handler
        ====== ======= ===================

        A node handler is responsible for servicing a single node at a single
        JID, while a JID handler may respond for any node at a given JID, and
        the global handler will answer to any JID+node combination.

        Handlers should check that the JID ``ifrom`` is authorized to perform
        the desired action.

        .. versionchanged:: 1.8.0
            ``run()`` always returns a future, if the handler is a coroutine
            the future should be awaited on.

        :param ctype: The name of the API to use.
        :param op: The API operation to perform.
        :param jid: Optionally provide specific JID.
        :param node: Optionally provide specific node.
        :param ifrom: Optionally provide the requesting JID.
        :param args: Optional arguments to the handler.
        """
        self._setup(ctype, op)

        if not jid:
            jid = self.xmpp.boundjid
        elif jid and not isinstance(jid, JID):
            jid = JID(jid)
        elif jid == JID(''):
            jid = self.xmpp.boundjid
        assert jid is not None

        if node is None:
            node = ''

        if self.xmpp.is_component:
            if self.settings[ctype].get('component_bare', False):
                jid_str = jid.bare
            else:
                jid_str = jid.full
        else:
            if self.settings[ctype].get('client_bare', False):
                jid_str = jid.bare
            else:
                jid_str = jid.full

        jid = JID(jid_str)

        handler = self._handlers[ctype][op]['node'].get((jid, node), None)
        if handler is None:
            handler = self._handlers[ctype][op]['jid'].get(jid, None)
        if handler is None:
            handler = self._handlers[ctype][op].get('global', None)

        if handler:
            try:
                if iscoroutinefunction(handler):
                    return self.xmpp.wrap(handler(jid, node, ifrom, args))
                else:
                    future: Future = Future(loop=self.xmpp.loop)
                    result = handler(jid, node, ifrom, args)
                    future.set_result(result)
                    return future
            except TypeError:
                # To preserve backward compatibility, drop the ifrom
                # parameter for existing handlers that don't understand it.
                return handler(jid, node, args)
        future = Future(loop=self.xmpp.loop)
        future.set_result(None)
        return future

    def register(self, handler: APIHandler | None, ctype: str, op: str,
                 jid: JID | None = None, node: str | None = None,
                 default: bool = False):
        """Register an API callback, with JID+node specificity.

        The API callback can later be executed based on the
        specificity of the provided JID+node combination.

        See :meth:`~.APIRegistry.run` for more details.

        :param ctype: The name of the API to use.
        :param op: The API operation to perform.
        :param jid: Optionally provide specific JID.
        :param node: Optionally provide specific node.
        """
        self._setup(ctype, op)
        if jid is None and node is None:
            if handler is None:
                handler = self._handler_defaults[op]
            self._handlers[ctype][op]['global'] = handler
        elif jid is not None and node is None:
            self._handlers[ctype][op]['jid'][jid] = handler
        else:
            self._handlers[ctype][op]['node'][(jid, node)] = handler

        if default:
            self.register_default(handler, ctype, op)

    def register_default(self, handler, ctype: str, op: str):
        """Register a default, global handler for an operation.

        :param handler: The default, global handler for the operation.
        :param ctype: The name of the API to modify.
        :param op: The API operation to use.
        """
        self._setup(ctype, op)
        self._handler_defaults[ctype][op] = handler

    def unregister(self, ctype: str, op: str, jid: JID | None = None,
                   node: str | None = None):
        """Remove an API callback.

        The API callback chosen for removal is based on the
        specificity of the provided JID+node combination.

        See :meth:`~ApiRegistry.run` for more details.

        :param ctype: The name of the API to use.
        :param op: The API operation to perform.
        :param jid: Optionally provide specific JID.
        :param node: Optionally provide specific node.
        """
        self._setup(ctype, op)
        self.register(None, ctype, op, jid, node)

    def restore_default(self, ctype: str, op: str, jid: JID | None = None,
                        node: str | None = None):
        """Reset an API callback to use a default handler.

        :param ctype: The name of the API to use.
        :param op: The API operation to perform.
        :param jid: Optionally provide specific JID.
        :param node: Optionally provide specific node.
        """
        self.unregister(ctype, op, jid, node)
        self.register(self._handler_defaults[ctype][op], ctype, op, jid, node)
