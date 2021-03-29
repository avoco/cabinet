class vectumError(RuntimeError):
    """Base class for all errors in this library"""

    pass


class FileNotAllowed(vectumError):
    """The provided file is not allowed."""

    pass


class FileExtensionNotAllowed(vectumError):
    """The provided file extension is not allowed."""

    pass


class vectumConfigError(vectumError):
    """Error in the configuration."""

    pass
