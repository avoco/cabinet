class CabinetError(RuntimeError):
    """
    Base class for all errors in this library
    """

    pass


class FileNotAllowed(CabinetError):
    """
    The provided file is not allowed.
    """

    pass


class FileExtensionNotAllowed(CabinetError):
    """
    The provided file extension is not allowed.
    """

    pass


class CabinetConfigError(CabinetError):
    """
    Error in the configuration.
    """

    pass
