class cabinetError(RuntimeError):
    """Base class for all errors in this library"""

    pass


class FileNotAllowed(cabinetError):
    """The provided file is not allowed."""

    pass


class FileExtensionNotAllowed(cabinetError):
    """The provided file extension is not allowed."""

    pass


class cabinetConfigError(cabinetError):
    """Error in the configuration."""

    pass
