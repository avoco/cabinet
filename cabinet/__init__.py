import pkg_resources

from .file_item import FileItem
from .filter_base import AsyncFilterBase, FilterBase
from .handler_base import AsyncStorageHandlerBase, StorageHandlerBase
from .storage_container import StorageContainer


def _read() -> str:
    return pkg_resources.get_distribution("cabinet").version


__version__ = _read()

# Instantiate the store singleton
store = StorageContainer()


__all__ = [
    "store",
    "StorageContainer",
    "StorageHandlerBase",
    "AsyncStorageHandlerBase",
    "FileItem",
    "FilterBase",
    "AsyncFilterBase",
    "exceptions",
    "handlers",
    "filters",
    "config_utils",
]
