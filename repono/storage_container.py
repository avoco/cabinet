from asyncio import get_event_loop, iscoroutine, isfuture
from typing import Awaitable, Dict, Optional, Union, cast

from .exceptions import ReponoConfigError
from .handler_base import AsyncStorageHandlerBase, Folder, StorageHandlerBase


class StorageContainer(Folder):
    """
    A class for handling storage configuration and retrieval.

    This is intended to be a singleton and contains global storage
    configurations that are lazily populated.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        parent: Optional["StorageContainer"] = None,
    ) -> None:
        # Init the folder superclass
        super().__init__(store=self, path=tuple())

        self._name: Optional[str] = name
        self._parent = parent
        self._children: Dict[str, "StorageContainer"] = {}
        self._handler: Optional[StorageHandlerBase] = None
        self._do_not_use = False
        self._finalized = False

    @property
    def name(self) -> str:
        """
        Provide a name for this container based on its lineage.

        :return: the name of the StorageContainer
        """
        parent = ""
        if self._parent is not None:
            parent = self._parent.name
        if self._name is None:
            return parent
        return "{}[{}]".format(parent, repr(self._name))

    @property
    def finalized(self) -> bool:
        """
        Determine whether this StorageContainer has been finalized.

        :return: whether this StorageContainer has been finalized or not
        """
        return self._finalized

    @property
    def do_not_use(self) -> bool:
        """
        Whether or not to use the StorageContainer.

        :return: whether or not the StorageContainer is usable
        """
        return self._do_not_use

    @property
    def sync_handler(self) -> StorageHandlerBase:
        """
        The synchronous FileHandler for the StorageContainer.

        :return: the synchronous FileHandler
        """
        handler = self.handler
        if handler is None:
            raise ReponoConfigError("No handler provided for store{}".format(self.name))
        return cast(StorageHandlerBase, handler)

    @property
    def async_handler(self) -> AsyncStorageHandlerBase:
        """
        The asynchronous FileHandler for the StorageContainer.

        :return: the asynchronous FileHandler
        """
        handler = self.handler
        if not isinstance(handler, AsyncStorageHandlerBase):
            raise ReponoConfigError(
                "No async handler provided for store{}".format(self.name)
            )

        return cast(AsyncStorageHandlerBase, handler)

    @property
    def handler(
        self,
    ) -> Union[StorageHandlerBase, AsyncStorageHandlerBase, None]:
        """
        The configured handler for this store.

        :raises ReponoConfigError: If no handler was provided
        """
        if self._do_not_use:
            return None
        if self._handler is None:
            raise ReponoConfigError("No handler provided for store{}".format(self.name))
        return self._handler

    @handler.setter
    def handler(self, handler: Optional[StorageHandlerBase]) -> None:
        """
        Sets the handler for this store

        :raises ReponoConfigError: If setting handler was unsuccessful

        :param handler: the FileHandler to add to the store
        """
        if self._finalized:
            raise ReponoConfigError(
                "Setting store{}.handler: store already finalized!".format(self.name)
            )
        if handler is None:
            self._handler = None
            self._do_not_use = True
            return

        if not isinstance(handler, StorageHandlerBase):
            raise ReponoConfigError(
                "Setting store{}.handler: ".format(self.name)
                + "'{}' is not a StorageHandler".format(handler)
            )
        self._do_not_use = False
        # Inject the handler name
        handler.handler_name = self._name
        self._handler = handler

    async def async_finalize_config(self) -> None:
        """
        Validate the config and prevent any further config changes.

        :raises ReponoConfigError: If setting handler was unsuccessful
        """
        if self._finalized:
            return

        if self._do_not_use:
            return

        if self._handler is None:
            raise ReponoConfigError("No handler provided for store{}".format(self.name))

        result = self._handler.validate()
        if iscoroutine(result) or isfuture(result):
            await cast(Awaitable, result)

        self._finalized = True

        for child in self._children.values():
            await child.async_finalize_config()

    def finalize_config(self) -> None:
        event_loop = get_event_loop()
        if event_loop.is_running():
            raise ReponoConfigError(
                "Async event loop is already running. "
                "Must await store.async_finalize_config() instead."
            )
        event_loop.run_until_complete(self.async_finalize_config())

    def __getitem__(self, key: str) -> "StorageContainer":
        """
        Get or create a storage container as a lookup.
        The provided container will be lazily configured.

        :param key: the storage to create or get

        :return: the created or retrieved StorageContainer
        """
        if self._finalized and key not in self._children:
            raise ReponoConfigError(
                "Getting store{}['{}']: store already finalized!".format(self.name, key)
            )
        return self._children.setdefault(key, StorageContainer(name=key, parent=self))
