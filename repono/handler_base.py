import inspect
from abc import ABC, abstractmethod
from asyncio import gather, iscoroutine, isfuture
from datetime import datetime
from io import BytesIO
from typing import (
    TYPE_CHECKING,
    Awaitable,
    BinaryIO,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)
from urllib.parse import urljoin

from . import utils
from .exceptions import ReponoConfigError
from .file_item import FileItem
from .filter_base import FilterBase


if TYPE_CHECKING:
    import cgi

    from .storage_container import StorageContainer


class StorageHandlerBase(ABC):
    """
    Base class for all storage handlers.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        filters: Optional[List[FilterBase]] = None,
        path: Union[Tuple[str, ...], List[str], str, None] = None,
    ) -> None:
        self.handler_name: Optional[str] = None
        self._base_url = base_url
        self._filters = filters or []

        # Allow the library users to provide a path in a couple of different ways.
        self._path: Tuple[str, ...]
        if isinstance(path, str):
            self._path = (path,)
        elif path:
            self._path = tuple(path)
        else:
            self._path = tuple()

    @property
    def base_url(self) -> str:
        """
        The base url for any saved file.

        :return: the base url
        """
        return self._base_url or ""

    @property
    def path(self) -> Tuple[str, ...]:
        """
        The path within the store for any saved file.

        :return: the path
        """
        return self._path

    @property
    def filters(self) -> List[FilterBase]:
        """
        List of filters to apply, in order, when saving any file through this handler.

        :return: the list, in order, of filters to apply.
        """
        return self._filters

    def __str__(self):
        return f'<{self.__class__.__name__}("{self.handler_name}")>'

    def validate(self) -> Optional[Awaitable]:
        """
        Validate that the configuration is set up properly and the necessary
        libraries are available.

        :raises: ReponoConfigError: Error in the configuration

        :return: list of coroutines or None depending on if filter is asynchronous
        """
        coroutines: List[Awaitable] = []
        # Verify that any provided filters are valid.
        for filter_ in self._filters:
            if inspect.isclass(filter_):
                filter_name: str = filter_.__name__  # type: ignore
                raise ReponoConfigError(
                    "Filter {} is a class, not an instance. ".format(filter_name)
                    + 'Did you mean to use "filters=[{}()]" instead?'.format(
                        filter_name
                    )
                )
            result = filter_.validate()
            if iscoroutine(result) or isfuture(result):
                coroutines.append(cast(Awaitable, result))

        result = self._validate()
        if iscoroutine(result) or isfuture(result):
            coroutines.append(cast(Awaitable, result))

        if not coroutines:
            return None
        return gather(*coroutines)

    def _validate(self) -> Optional[Awaitable]:
        """
        Validate any subclass.
        """
        pass

    def get_item(
        self,
        filename: str,
        subpath: Optional[Tuple[str, ...]] = None,
        data: Optional[BinaryIO] = None,
    ) -> FileItem:
        """
        Returns FileItem object for further manipulation.

        :param filename: the filename for the file

        :param subpath: the subpath for the file

        :param data: the data to write to the file

        :return: the FileItem
        """
        path = self._path
        if subpath is not None:
            path = path + subpath

        return FileItem(filename=filename, path=path, data=data)

    def get_url(self, filename: str) -> str:
        """
        Return the URL of a given filename in this storage container.

        :param filename: the filename to retrieve the url for

        :return: the url of the filename
        """
        item = self.get_item(filename)
        return urljoin(self.base_url, item.url_path)

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Perform a quick pass to sanitize the filename

        :param filename: the filename to sanitize

        :return: the sanitized filename
        """
        # Strip out any . prefix - which should eliminate attempts to write
        # special Unix files
        filename = filename.lstrip(".")

        # Strip out any non-alpha, . or _ characters.
        def clean_char(c: str) -> str:
            if c.isalnum() or c in (".", "_"):
                return c
            return "_"

        filename = "".join(clean_char(c) for c in filename)

        return filename

    def exists(self, filename: str) -> bool:
        """
        Determine if the given path/filename exists in the storage container.

        :param filename: the filename with path to determine existence for

        :return: whether the filename exists in the storage container or not
        """
        item = self.get_item(filename)
        return cast(bool, self._exists(item))

    @abstractmethod
    def _exists(self, item: FileItem) -> bool:
        """
        Determine if the given path/filename exists in the storage container.

        :param item: the FileItem to determine existence for

        :return: whether the filename exists in the storage container or not
        """
        pass

    def get_size(self, filename: str) -> int:
        """
        Retrieve file size for file in storage container given filename.

        :param filename: the filename to retrieve size for

        :return: the size, in bytes, of the file in the storage container.
        """
        item = self.get_item(filename)
        return self._get_size(item)

    @abstractmethod
    def _get_size(self, item: FileItem) -> int:
        """
        Retrieve file size for file in storage container given filename.

        :param item: the FileItem to retrieve size for

        :return: the size, in bytes, of the file in the storage container.
        """
        pass

    def get_accessed_time(self, filename: str) -> datetime:
        """
        Retrieve time of last access for file in storage container.

        :param filename: the filename to retrieve access time for

        :return: the time of last access for the given filename
        """
        item = self.get_item(filename)
        return self._get_accessed_time(item)

    @abstractmethod
    def _get_accessed_time(self, item: FileItem) -> datetime:
        """
        Retrieve time of last access for file in storage container.

        :param item: the FileItem to retrieve access time for

        :return: the time of last access for the given filename
        """
        pass

    def get_created_time(self, filename: str) -> datetime:
        """
        Retrieve creation time for file in storage container given filename.

        NOTE: On Unix systems this is the time of last metadata change and on
              others, such as Windows, is the creation time.

        :param filename: the filename to retrieve time of creation for

        :return: the time of creation for the given filename
        """
        item = self.get_item(filename)
        return self._get_created_time(item)

    @abstractmethod
    def _get_created_time(self, item: FileItem) -> datetime:
        """
        Retrieve creation time for file in storage container given filename.

        NOTE: On Unix systems this is the time of last metadata change and on
              others, such as Windows, is the creation time.

        :param item: the FileItem to retrieve time of creation for

        :return: the time of creation for the given filename
        """
        pass

    def get_modified_time(self, filename: str) -> datetime:
        """
        Retrieve time of last modification for file in storage container given filename.

        :param filename: the filename to retrieve time of last modification for

        :return: the time of last modification for the given filename
        """
        item = self.get_item(filename)
        return self._get_modified_time(item)

    @abstractmethod
    def _get_modified_time(self, item: FileItem) -> datetime:
        """
        Retrieve time of last modification for file in storage container given filename.

        :param item: the FileItem to retrieve time of last modification for

        :return: the time of last modification for the given filename
        """
        pass

    def delete(self, filename: str) -> None:
        """
        Delete the given filename from the storage container, whether or not
        it exists.

        :param filename: the filename to delete
        """
        item = self.get_item(filename)
        return self._delete(item)

    @abstractmethod
    def _delete(self, item: FileItem) -> None:
        """
        Delete the given filename from the storage container, whether or not it exists.

        :param item: the FileItem to delete
        """
        pass

    @abstractmethod
    def _save(self, item: FileItem) -> str:
        """
        Save the provided file to the given filename in the storage container.

        :param item: the FileItem to be saved

        :return: the name of the saved file
        """
        pass

    def save_file(self, filename: str, data: BinaryIO) -> str:
        """
        Verifies that the provided filename is legitimate and saves it to the storage
        container.

        :param filename: the name of the file to be saved

        :param data: the data to write to the file

        :return: the name of the saved file
        """
        filename = self.sanitize_filename(filename)
        item = self.get_item(filename, data=data)

        for filter_ in self.filters:
            item = filter_.call(item)

        return self._save(item)

    def save_field(self, field: "cgi.FieldStorage") -> str:
        """
        Save a file stored in a CGI field.

        :param field: the CGI field to save

        :return: the name of the saved file
        """
        if not field.file:
            raise RuntimeError("No file data in the field")

        return self.save_file(field.filename or "file", cast(BinaryIO, field.file))

    def save_data(self, filename: str, data: bytes) -> str:
        """
        Save a file from the byte data provided.

        :param filename: the filename to save

        :data: the data to write to the file

        :return: the name of the saved file
        """
        fileio = BytesIO(data)
        return self.save_file(filename, fileio)


class AsyncStorageHandlerBase(StorageHandlerBase, ABC):
    """
    Base class for all asynchronous storage handlers.
    """

    def __init__(self, allow_sync_methods=True, **kwargs) -> None:
        self.allow_sync_methods = allow_sync_methods
        super().__init__(**kwargs)

    def validate(self) -> Optional[Awaitable]:
        """
        Validate that the configuration is set up properly and the necessary
        libraries are available.

        :raises: ReponoConfigError: Error in the configuration

        :return: list of coroutines or None depending on if filter is asynchronous
        """
        # Verify that any provided filters are ok to use.
        for filter_ in self.filters:
            if not filter_.async_ok:
                raise ReponoConfigError(
                    "Filter {} cannot be used in ".format(filter_)
                    + "asynchronous storage handler {}".format(self)
                )
        return super().validate()

    async def async_exists(self, filename: str) -> bool:
        """
        Determine if the given path/filename exists in the storage container.

        :param filename: the filename with path to determine existence

        :return: whether the filename exists in the storage container or not
        """
        item = self.get_item(filename)
        return await self._async_exists(item)

    def _exists(self, item: FileItem) -> bool:
        if not self.allow_sync_methods:
            raise RuntimeError("Sync exists method not allowed")
        return utils.async_to_sync(self._async_exists)(item)

    @abstractmethod
    async def _async_exists(self, item: FileItem) -> bool:
        """
        Determine if the given path/filename exists in the storage container.

        :param item: the FileItem to determine existence of

        :return: whether the filename exists in the storage container or not
        """
        pass

    async def async_get_size(self, filename: str) -> int:
        """
        Retrieve file size for file in storage container given filename.

        :param filename: the filename to retrieve size of

        :return: the size, in bytes, of the file in the storage container.
        """
        item = self.get_item(filename)
        return await self._async_get_size(item)

    def _get_size(self, item: FileItem) -> int:
        if not self.allow_sync_methods:
            raise RuntimeError("Sync get_size method not allowed")
        return utils.async_to_sync(self._async_get_size)(item)

    @abstractmethod
    async def _async_get_size(self, item: FileItem) -> int:
        """
        Retrieve file size for file in storage container given filename.

        :param item: the FileItem to retrieve size of

        :return: the size, in bytes, of the file in the storage container.
        """
        pass

    async def async_get_accessed_time(self, filename: str) -> datetime:
        """
        Retrieve time of last access for file in storage container.

        :param filename: the filename to retrieve access time

        :return: the time of last access for the given filename
        """
        item = self.get_item(filename)
        return await self._async_get_accessed_time(item)

    def _get_accessed_time(self, item: FileItem) -> datetime:
        if not self.allow_sync_methods:
            raise RuntimeError("Sync get_accessed_time method not allowed")
        return utils.async_to_sync(self._async_get_accessed_time)(item)

    @abstractmethod
    async def _async_get_accessed_time(self, item: FileItem) -> datetime:
        """
        Retrieve time of last access for file in storage container.

        :param item: the FileItem to retrieve access time

        :return: the time of last access for the given filename
        """
        pass

    async def async_get_created_time(self, filename: str) -> datetime:
        """
        Retrieve creation time for file in storage container given filename.

        NOTE: On Unix systems this is the time of last metadata change and on
              others, such as Windows, is the creation time.

        :param filename: the filename to retrieve time of creation for

        :return: the time of creation for the given filename
        """
        item = self.get_item(filename)
        return await self._async_get_created_time(item)

    def _get_created_time(self, item: FileItem) -> datetime:
        if not self.allow_sync_methods:
            raise RuntimeError("Sync get_created_time method not allowed")
        return utils.async_to_sync(self._async_get_created_time)(item)

    @abstractmethod
    async def _async_get_created_time(self, item: FileItem) -> datetime:
        """
        Retrieve creation time for file in storage container given filename.

        NOTE: On Unix systems this is the time of last metadata change and on
              others, such as Windows, is the creation time.

        :param item: the FileItem to retrieve time of creation for

        :return: the time of creation for the given filename
        """
        pass

    async def async_get_modified_time(self, filename: str) -> datetime:
        """
        Retrieve time of last modification for file in storage container given filename.

        :param filename: the filename to retrieve time of last modification for

        :return: the time of last modification for the given filename
        """
        item = self.get_item(filename)
        return await self._async_get_modified_time(item)

    def _get_modified_time(self, item: FileItem) -> datetime:
        if not self.allow_sync_methods:
            raise RuntimeError("Sync get_modified_time method not allowed")
        return utils.async_to_sync(self._async_get_modified_time)(item)

    @abstractmethod
    async def _async_get_modified_time(self, item: FileItem) -> datetime:
        """
        Retrieve time of last modification for file in storage container given filename.

        :param item: the FileItem to retrieve time of last modification for

        :return: the time of last modification for the given filename
        """
        pass

    async def async_delete(self, filename: str) -> None:
        """
        Delete the given filename from the storage container, whether or not
        it exists.

        :param filename: the filename to delete
        """
        item = self.get_item(filename)
        await self._async_delete(item)

    def _delete(self, item: FileItem) -> None:
        if not self.allow_sync_methods:
            raise RuntimeError("Sync delete method not allowed")
        utils.async_to_sync(self._async_delete)(item)

    @abstractmethod
    async def _async_delete(self, item: FileItem) -> None:
        """
        Delete the given filename from the storage container, whether or not
        it exists.

        :param item: the FileItem to delete
        """
        pass

    def _save(self, item: FileItem) -> str:
        if not self.allow_sync_methods:
            raise RuntimeError("Sync save method not allowed")
        return utils.async_to_sync(self._async_save)(item)

    @abstractmethod
    async def _async_save(self, item: FileItem) -> str:
        """
        Save the provided file to the given filename in the storage container.

        :param item: the FileItem to be saved

        :return: the name of the saved file
        """
        pass

    async def async_save_file(self, filename: str, data: BinaryIO) -> str:
        """
        Save the provided file to the given filename in the storage container.

        :param filename: the name of the file to be saved

        :parma data: the data to write to the file

        :return: the name of the saved file
        """
        filename = self.sanitize_filename(filename)
        item = self.get_item(filename, data=data)
        for filter_ in self.filters:
            item = await filter_.async_call(item)

        new_filename = await self._async_save(item)
        if new_filename is not None:
            filename = new_filename
        return filename

    async def async_save_field(self, field: "cgi.FieldStorage") -> str:
        """
        Save a file stored in a CGI field.

        :param field: the CGI field to save

        :return: the name of the saved file
        """
        if not field.file:
            raise RuntimeError("No file data in the field")

        return await self.async_save_file(
            field.filename or "file", cast(BinaryIO, field.file)
        )

    async def async_save_data(self, filename: str, data: bytes) -> str:
        """
        Save a file from the byte data provided.

        :param filename: the filename to save

        :data: the data to write to the file

        :return: the name of the saved file
        """
        fileio = BytesIO(data)
        return await self.async_save_file(filename, fileio)


class Folder(AsyncStorageHandlerBase):
    """
    A handler for a sub-folder of a container.

    NOTE: This does not carry any config and depends on the
          StorageContainer to provide the handler when needed.
    """

    @property
    def async_ok(self) -> bool:
        """
        Determines if this handler can be used asynchronously.

        :return: whether or not it's okay to use asynchronous methods with this handler
        """
        return isinstance(self._store.handler, AsyncStorageHandlerBase)

    @property
    def filters(self) -> List[FilterBase]:
        """
        List of filters to apply, in order, when saving any file through this handler.

        :return: the list, in order, of filters to apply.
        """
        return self._store.sync_handler.filters

    @property
    def base_url(self) -> str:
        """
        The base url for any saved file.

        :return: the base url
        """
        return self._store.sync_handler.base_url

    def __init__(self, store: "StorageContainer", path: Tuple[str, ...]) -> None:
        super().__init__(path=path)
        self._store = store

    def subfolder(self, folder_name: str) -> "Folder":
        """
        Get a sub-folder for this folder

        :param folder_name: the folder name to retrieve sub-folder for

        :return: the sub-folder
        """
        return Folder(store=self._store, path=self._path + (folder_name,))

    def __eq__(self, other) -> bool:
        """
        Allows equality testing with folders.

        :return: whether or not the folder is itself
        """
        return (
            isinstance(other, Folder)
            and (self._store is other._store)
            and (self._path == other._path)
        )

    def __truediv__(self, other: str) -> "Folder":
        """
        Get a new sub-folder when using the divide operator.

        Allows building a path with path-looking code:
            new_store = store / 'folder' / 'sub-folder'

        :param other: the folder names to create sub-folder

        :return: a new sub-folder with the specified path
        """
        return self.subfolder(other)

    def _get_subfolder_file_item(self, item: FileItem) -> FileItem:
        """
        Returns a FileItem from within folder.

        :param item: the FileItem to retrieve

        :return: the specified FileItem
        """
        new_path = self._store.sync_handler.path + self._path
        return FileItem(filename=item.filename, path=new_path, data=item.data)

    # Pass through any exists methods

    def _exists(self, item: FileItem) -> bool:
        """
        Return the handler's _exists method from this folder

        :param item: the FileItem to determine existence for

        :return: whether the filename exists in the storage container or not
        """
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._exists(item)

    async def _async_exists(self, item: FileItem) -> bool:
        """
        Return the handler's _async_exists method from this folder

        :param item: the FileItem to determine existence for

        :return: whether the filename exists in the storage container or not
        """
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_exists(item)

    # Pass through any get_size methods

    def _get_size(self, item: FileItem) -> int:
        """
        Return the handler's _get_size from this folder
        """
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._get_size(item)

    async def _async_get_size(self, item: FileItem) -> int:
        """
        Return the handler's _async_get_size from this folder
        """
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_get_size(item)

    # Pass through any get_accessed_time methods

    def _get_accessed_time(self, item: FileItem) -> datetime:
        """
        Return the handler's _get_accessed_time from this folder

        :param item: the FileItem to retrieve access time for

        :return: the time of last access for the given filename
        """
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._get_accessed_time(item)

    async def _async_get_accessed_time(self, item: FileItem) -> datetime:
        """
        Return the handler's _async_get_accessed_time from this folder

        :param item: the FileItem to retrieve access time for

        :return: the time of last access for the given filename
        """
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_get_accessed_time(item)

    # Pass through any get_created_time methods

    def _get_created_time(self, item: FileItem) -> datetime:
        """
        Return the handler's _size from this folder

        :param item: the FileItem to retrieve time of creation for

        :return: the time of creation for the given filename
        """
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._get_created_time(item)

    async def _async_get_created_time(self, item: FileItem) -> datetime:
        """
        Return the handler's _async_size from this folder

        :param item: the FileItem to retrieve time of creation for

        :return: the time of creation for the given filename
        """
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_get_created_time(item)

    # Pass through any get_modified_time methods

    def _get_modified_time(self, item: FileItem) -> datetime:
        """
        Return the handler's _get_modified_time from this folder

        :param item: the FileItem to retrieve time of last modification for

        :return: the time of last modification for the given filename
        """
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._get_modified_time(item)

    async def _async_get_modified_time(self, item: FileItem) -> datetime:
        """
        Return the handler's _async_get_modified_time from this folder

        :param item: the FileItem to retrieve time of last modification for

        :return: the time of last modification for the given filename
        """
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_get_modified_time(item)

    # Pass through any delete methods

    def _delete(self, item: FileItem) -> None:
        """
        Return the handler's _delete method from this folder

        :param item: the FileItem to delete
        """
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._delete(item)

    async def _async_delete(self, item: FileItem) -> None:
        """
        Return the handler's _async_delete method from this folder

        :param item: the FileItem to delete
        """
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_delete(item)

    # Pass through any save methods

    def _save(self, item: FileItem) -> str:
        """
        Return the handler's _save from this folder

        :param item: the FileItem to be saved

        :return: the name of the saved file
        """
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._save(item)

    async def _async_save(self, item: FileItem) -> str:
        """
        Return the handler's _async_save from this folder

        :param item: the FileItem to be saved

        :return: the name of the saved file
        """
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_save(item)
