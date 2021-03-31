try:
    from pyramid.config import Configurator  # type: ignore
    from pyramid.request import Request  # type: ignore
except ImportError:
    raise ImportError(
        "In order to use cabinet as a pyramid plugin," "you must install pyramid first!"
    )

from cabinet import StorageContainer, store
from cabinet.config_utils import setup_from_settings


def includeme(config: Configurator) -> None:
    """
    Includes cabinet as a pyramid plugin.

    :param: config: The pyramid configuration instance
    :type: config: Configurator

    :raises RuntimeError: Configuration was unsuccessful

    :returns: None if successful
    :rtype: None
    """
    store_prefix = "store"
    # Make a copy of the settings so that each valid key can be consumed and
    # verified, and invalid ones can be complained about.
    settings = {
        key: value
        for (key, value) in config.registry.settings.items()
        if key.startswith(store_prefix)
    }

    # Check if we should be using the global store or a local pyramid_store
    use_global_store = settings.pop("store.use_global", "true")
    if use_global_store.lower() not in ("true", "false", "yes", "no", ""):
        raise RuntimeError(
            'Unknown setting "store.use_global". '
            "Expected true/false/yes/no, but got {}".format(use_global_store)
        )

    pyramid_store = store
    if use_global_store.lower() in ("false", "no"):
        # If not using the global store, make a new store for get_store to use.
        pyramid_store = StorageContainer()

    def get_store(request: Request) -> StorageContainer:
        """
        Gets pyramid store.

        :param: request: The pyramid request
        :type: request: Request

        :return: the pyramid store
        :rtype StorageContainer
        """
        return pyramid_store

    # Add the store object to every request.
    name = settings.pop("{}.request_property".format(store_prefix), "store")
    config.add_request_method(callable=get_store, name=name, property=True)

    if setup_from_settings(settings, pyramid_store):
        # If there were settings, finalize the config
        pyramid_store.finalize_config()
