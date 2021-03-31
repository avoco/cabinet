import difflib
import importlib
import inspect
from typing import Any, Dict, List, Set, Tuple

from cabinet import FilterBase, StorageContainer, StorageHandlerBase
from cabinet.exceptions import CabinetConfigError


def try_import(default_module: str, model: str):
    """
    Attempt to import a given name.

    :param: default_module: The module to import
    :type: default_module: str

    :param: model: The object to import
    :type: model: str

    :return: The imported object
    :rtype: object
    """
    module_name, _, cls_name = model.rpartition(".")
    module_name = module_name or default_module
    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, cls_name)
    except (ImportError):
        raise ValueError("module not installed")
    except AttributeError:
        raise ValueError("bad class name")

    return cls


def get_init_properties(cls, to_class=object) -> Set[str]:
    """
    Given a class, determine the properties that class needs.
    Assumes that each sub-class will call super with **kwargs. (Which is not a
    good general assumption, but should work well enough for Handlers.)

    :param: cls: The class to check
    :type: cls: object

    :param: to_class: The final parent class to check
    :type: to_class: object

    :return: Set of all parameters found
    :rtype: set
    """
    result = set()
    init = getattr(cls, "__init__", None)

    if init is not None:
        for param in inspect.signature(init).parameters.values():
            if param.kind == param.VAR_KEYWORD:
                # Ignore any **kwargs
                continue
            if param.name == "self":
                continue

            result.add(param.name)

    if issubclass(cls.mro()[1], to_class):
        result |= get_init_properties(cls.mro()[1], to_class)

    return result


def setup_from_settings(
    settings: Dict[str, str],
    store: StorageContainer,
    key_prefix: str = "store",
) -> bool:
    """
    Setup the provided store with the settings dictionary.
    Will only pay attention to keys that start with the key_prefix.

    The config will not be finalized.

    :param: settings: The dictionary of settings to use
    :type: settings: dict

    :param: store: The storage container to setup
    :type: store: StorageContainer

    :param: key_prefix: The prefix of the keys to use in setup
    :type: key_prefix: str

    :return: Whether or not the setup was successful
    :rtype: bool
    """
    # Convert the flat dict to a nested dict where the same delimiters are
    # grouped together.
    settings_dict = get_keys_from(key_prefix, settings)

    # If there's configuration to be had, setup the store with it.
    if settings_dict:
        setup_store(store, key_prefix, "", settings_dict)
        return True
    else:
        # Otherwise, assume that the store isn't going to be used now
        store.handler = None
        return False


def setup_store(
    store: StorageContainer, key_prefix: str, name: str, settings_dict: Dict
) -> None:
    """
    Setup a specific store to the given name in the settings_dict.
    key_prefix denotes where this name came from (for good error messages).

    :param: store: The StorageContainer instance to setup
    :type: store: StorageContainer

    :param: key_prefix: The prefix of the keys to use in setup
    :type: key_prefix: str

    :param: name: The name of the store to setup
    :type: name: str

    :settings_dict: The dictionary of settings to apply to the store
    :type: settings_dict: dict

    :return: None
    :rtype: None
    """
    name = name or ""
    try:
        handler_class_name = settings_dict["handler"][None]
    except KeyError:
        raise CabinetConfigError(
            "Pyramid settings has no key for {}{}.handler".format(key_prefix, name)
        )
    if handler_class_name.lower() == "none":
        handler = None
    else:
        handler = get_handler(key_prefix + name, settings_dict["handler"])

    settings_dict.pop("handler")

    store.handler = handler

    # Setup any sub-store configuration
    for key, sub_config in settings_dict.items():
        if key.startswith("[") and key.endswith("]"):
            sub_store = key.lstrip("[").rstrip("]").strip('"').strip("'")
            setup_store(
                store=store[sub_store],
                key_prefix=key_prefix + key,
                name=key,
                settings_dict=sub_config,
            )
        else:
            raise CabinetConfigError(
                "Pyramid settings unknown key {}.{}".format(key_prefix, key)
            )


def get_handler(key_prefix: str, settings_dict: Dict) -> StorageHandlerBase:
    """
    Retrieves handler from settings

    :param: key_prefix: The key prefix for the handler
    :type: key_prefix: str

    :param: settings_dict: The settings to extract handler from
    :type: settings_dict: dict

    :return: The StorageHandler from settings
    :rtype: StorageHandlerBase
    """
    name = "{}.handler".format(key_prefix)
    handler_name = settings_dict.pop(None)
    try:
        handler_cls = try_import("cabinet.handlers", handler_name)
    except ValueError:
        raise CabinetConfigError("Pyramid settings bad value for {}".format(name))

    valid_args = get_init_properties(handler_cls, StorageHandlerBase)

    kwargs = {}
    for key, value in settings_dict.items():
        if key not in valid_args:
            maybe = difflib.get_close_matches(key, valid_args, 1)
            maybe_txt = ""
            if maybe:
                maybe_txt = ' Did you mean "{}.{}"?'.format(name, maybe[0])
            raise CabinetConfigError(
                'Pyramid invalid setting "{}.{}". {}'.format(name, key, maybe_txt)
            )
        if key == "filters":
            kwargs["filters"] = get_all_filters(name, value)
        else:
            kwargs[key] = decode_kwarg(value)

    try:
        return handler_cls(**kwargs)
    except Exception as err:
        raise CabinetConfigError(
            "Pyramid settings bad args for {}: {}".format(name, err)
        )


def get_all_filters(key_prefix: str, settings_dict: Dict) -> List[FilterBase]:
    """
    Get all the filters from within the settings_dict

    :param: key_prefix: The key prefix for the handler
    :type: key_prefix: str

    :param: settings_dict: The settings to extract handler from
    :type: settings_dict: dict

    :return: List of filters
    :rtype: list
    """
    filters: List[Tuple[int, FilterBase]] = []
    for filter_ref, filter_dict in settings_dict.items():
        filter_prefix = "{}.filters{}".format(key_prefix, filter_ref)
        try:
            filter_id = int(filter_ref.lstrip("[").rstrip("]"))
        except Exception as err:
            raise CabinetConfigError(
                "Pyramid settings bad key {}{}: {}".format(key_prefix, filter_ref, err)
            )
        filters.append((filter_id, get_filter(filter_prefix, filter_dict)))

    filters.sort()
    return [filter for ref, filter in filters]


def get_filter(key_prefix: str, settings_dict: Dict) -> FilterBase:
    """
    Get a single filter from within the settings_dict

    :param: key_prefix: The key prefix for the handler
    :type: key_prefix: str

    :param: settings_dict: The settings to extract handler from
    :type: settings_dict: dict

    :return: Specified filter
    :rtype: FilterBase
    """
    filter_name = settings_dict.pop(None)
    try:
        filter_cls = try_import("cabinet.filters", filter_name)
    except ValueError:
        raise CabinetConfigError("Pyramid settings bad value for {}".format(key_prefix))

    kwargs = {key: decode_kwarg(value) for key, value in settings_dict.items()}
    try:
        return filter_cls(**kwargs)
    except Exception as err:
        raise CabinetConfigError(
            "Pyramid settings bad args for {}: {}".format(key_prefix, err)
        )


def unquote(value: str) -> str:
    """
    Removes the prefix and suffix if they are identical quotes

    :param: value: the value to unquote
    :type: value: str

    :return: The unquoted string
    :rtype: str
    """
    if value[0] in {'"', "'"} and value[0] == value[-1]:
        return value[1:-1]
    return value


def decode_kwarg(value: Any) -> Any:
    """
    Tries to determine what the kwarg should be. Decode lists, dicts, sets
    and integers.

    :param: value: The value to decode
    :type: value: Any

    :return: The decoded value
    :rtype: Any
    """
    if isinstance(value, dict):
        try:
            value = value.pop(None)
        except KeyError:
            raise ValueError("decode_kwarg got an invalid dict: {}".format(value))
        return decode_kwarg(value)

    if not isinstance(value, str):
        raise ValueError("decode_kwarg expected a str, got: {}".format(value))
    if (value.startswith("[") and value.endswith("]")) or (
        value.startswith("{") and value.endswith("}")
    ):
        # handle lists, sets and dicts
        try:
            return eval(value, {}, {})
        except Exception as err:
            raise CabinetConfigError(
                "Pyramid settings bad value {}: {}".format(value, err)
            )

    if value.isdigit():
        return int(value)

    return unquote(value)


def get_keys_from(prefix: str, settings: Dict) -> Dict:
    """
    Get nested dicts from a dictionary of . separated keys

    :param: prefix: The prefix to filter by
    :type: prefix: str

    :param: settings: The settings to look in
    :type: settings: dict

    :return: The settings containing the prefix
    :rtype: dict
    """
    result: Dict = {}
    for key, value in settings.items():
        if key.startswith("{}.".format(prefix)) or key.startswith("{}[".format(prefix)):
            set_nested_value(key, value, result)

    return result.get(prefix, {})


def set_nested_value(key: str, value: str, result: Dict) -> Dict:
    """
    Modify the provided result dict in-place with the value at the key

    :param: key: The key in the dict to get value
    :type: key: str

    :param: value: The value to add to the key
    :type: value: str

    :param: result: The dictionary to preform on
    :type: dict

    :return: dictionary containing nested value
    :rtype: dict
    """
    sub = result
    # Add a . to each [ to make the parsing delimiter consistent:
    # 'foo[0][1]' to 'foo.[0].[1]'
    key = key.replace("[", ".[")
    for part in key.split("."):
        sub = sub.setdefault(part, {})
    sub[None] = value.strip()
    return result
