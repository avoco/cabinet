import os
from typing import Callable
from uuid import uuid4

from repono import FileItem, FilterBase


def random_string_generator(filename: str) -> str:
    """
    Returns a unique identifier using uuid4

    :param filename: the original filename of the file

    :return: a unique identifier
    """
    return str(uuid4())


class RandomizeFilename(FilterBase):
    """
    Randomize the name for every file
    """

    async_ok = True

    def __init__(
        self,
        name_generator: Callable[[str], str] = random_string_generator,
    ) -> None:
        self.name_generator = name_generator

    def _apply(self, item: FileItem) -> FileItem:
        name, ext = os.path.splitext(item.filename)
        randomized_name = self.name_generator(name) + ext.lower()

        return item.copy(filename=randomized_name)
