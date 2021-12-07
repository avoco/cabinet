import mimetypes
import os
from typing import BinaryIO, NamedTuple, Optional, Tuple

from . import utils


class SyncReader:
    """
    Synchronous file reader
    """

    def __init__(self, item: "FileItem"):
        self.data = item.data
        self.filename = item.filename
        if self.data is not None:
            self._reader = utils.any_to_sync(self.data.read)
            self._seeker = utils.any_to_sync(self.data.seek)

    def seek(self, offset: int, whence: int = 0) -> int:
        if self.data is None:
            return -1
        return self._seeker(offset)

    def read(self, size: int = -1) -> bytes:
        if self.data is None:
            return b""
        return self._reader(size)

    closed = False


class AsyncReader:
    """
    Asynchronous file reader
    """

    def __init__(self, item: "FileItem"):
        self.data = item.data
        self.filename = item.filename
        if self.data is not None:
            self._reader = utils.any_to_async(self.data.read)
            self._seeker = utils.any_to_async(self.data.seek)

    async def seek(self, offset: int, whence: int = 0) -> int:
        if self.data is None:
            return -1
        return await self._seeker(offset)

    async def read(self, size: int = -1) -> bytes:
        if self.data is None:
            return b""
        return await self._reader(size)

    closed = False


class FileItem(NamedTuple):
    """
    Base file object used by repono
    """

    filename: str
    path: Tuple[str, ...] = tuple()
    data: Optional[BinaryIO] = None
    media_type: Optional[str] = None  # Formerly known as MIME-type

    def copy(self, **kwargs) -> "FileItem":
        """
        Creates a copy of a given FileItem.

        :return: the copied FileItem
        """
        filename = kwargs.get("filename", self.filename)
        path = kwargs.get("path", self.path)
        data = kwargs.get("data", self.data)
        media_type = kwargs.get("media_type", self.media_type)

        return FileItem(filename=filename, path=path, data=data, media_type=media_type)

    def __repr__(self) -> str:
        has_data = "no data" if self.data is None else "with data"
        return "<FileItem filename:{} ".format(self.filename) + "path:{} {}>".format(
            self.path, has_data
        )

    @property
    def has_data(self) -> bool:
        """
        Property to check whether or not the FileItem has data or not.

        :return: whether or not the FileItem has data
        """
        return self.data is not None

    @property
    def url_path(self) -> str:
        """
        A relative URL path string for this path/filename.

        :return: the relative url path for the FileItem
        """
        return "/".join(self.path + (self.filename,))

    @property
    def fs_path(self) -> str:
        """
        A relative file system path string for this path/filename.

        :return: the relative file system path for the FileItem
        """
        return os.path.join(*self.path, self.filename)

    @property
    def content_type(self) -> Optional[str]:
        """
        The inferred content type of the FileItem.

        :return: the content type
        """
        if self.media_type is not None:
            return self.media_type
        return mimetypes.guess_type(self.filename)[0]

    def __enter__(self):
        reader = SyncReader(self)
        reader.seek(0)
        return reader

    def __exit__(*args, **kwargs):
        pass

    async def __aenter__(self):
        reader = AsyncReader(self)
        await reader.seek(0)
        return reader

    async def __aexit__(*args, **kwargs):
        pass
