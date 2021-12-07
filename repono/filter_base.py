from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction
from typing import Awaitable, Optional, Union, cast

from . import utils
from .exceptions import ReponoConfigError
from .file_item import FileItem


class FilterBase(ABC):
    """
    The base filter class used by all filters
    """

    async_ok = False

    def validate(self) -> Optional[Awaitable]:
        """
        Validates the filter configuration
        """
        return self._validate()

    # For consistency with the storage handlers, use a _ method
    def _validate(self) -> Optional[Awaitable]:
        """
        Validates the filter configuration
        """
        pass

    def call(self, item: FileItem) -> FileItem:
        """
        Apply the filter synchronously

        :param item: the item to apply filter to.

        :return: FileItem that filter has been applied to or an awaitable
        """
        return utils.any_to_sync(self._apply)(item)

    async def async_call(self, item: FileItem) -> FileItem:
        """
        Apply the filter asynchronously

        :param item: the item to apply filter to.

        :return: FileItem that filter has been applied to or an awaitable
        """
        if not self.async_ok:
            raise ReponoConfigError(
                "The {} filter cannot be used "
                "asynchronously".format(self.__class__.__name__)
            )

        if iscoroutinefunction(self._apply):
            return await cast(utils.AsyncCallable, self._apply)(item)
        return cast(utils.SyncCallable, self._apply)(item)

    @abstractmethod
    def _apply(self, item: FileItem) -> Union[Awaitable[FileItem], FileItem]:
        """
        Applies the filter.

        :param item: the item to apply filter to.

        :return: FileItem that filter has been applied to or an awaitable
        """
        return item


class AsyncFilterBase(FilterBase, ABC):
    """
    The base asynchronous filter class used by all asynchronous filters.
    """

    async_ok = True

    @abstractmethod
    async def _apply(self, item: FileItem) -> FileItem:
        return item
