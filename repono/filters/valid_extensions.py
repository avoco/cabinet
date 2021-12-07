import os
from typing import List

from repono import FileItem, FilterBase
from repono.exceptions import FileExtensionNotAllowed


class ValidateExtension(FilterBase):
    """
    Ensure that the file extension is valid.
    Raises FileExtensionNotAllowed if check fails.
    """

    async_ok = True

    def __init__(self, extensions: List[str]) -> None:
        self.extensions = set(ext.lower().strip(os.path.extsep) for ext in extensions)

    def extension_allowed(self, ext: str) -> bool:
        """
        Determine if the provided file extension is allowed.

        :param ext: the extension to check

        :return: whether or not the extension is allowed
        """
        if not self.extensions:
            return True
        return ext.lower() in self.extensions

    def filename_allowed(self, filename: str) -> bool:
        """
        Indicate if the provided filename is allowed.
        Judgement is based on its extension.

        :param filename: the filename to check

        :return: whether or not the filename is allowed
        """
        ext = os.path.splitext(filename)[1].strip(os.path.extsep)
        return self.extension_allowed(ext)

    def _apply(self, item: FileItem) -> FileItem:
        if not self.filename_allowed(item.filename):
            raise FileExtensionNotAllowed(item.filename)

        return item
