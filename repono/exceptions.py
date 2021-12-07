class ReponoError(RuntimeError):
    """
    Base class for all errors in this library
    """

    pass


class FileNotAllowed(ReponoError):
    """
    The provided file is not allowed.
    """

    pass


class FileExtensionNotAllowed(ReponoError):
    """
    The provided file extension is not allowed.
    """

    pass


class ReponoConfigError(ReponoError):
    """
    Error in the configuration.
    """

    pass
