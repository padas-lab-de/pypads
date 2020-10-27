class UninitializedTrackerException(Exception):
    """
    Exception warning about pypads not being initialized.
    """

    def __init__(self, *args):
        super().__init__(*args)


class PassThroughException(Exception):
    """
    Exception to be passed from _pre / _post and not be caught by the defensive logger.
    """

    def __init__(self, *args):
        super().__init__(*args)


class NoCallAllowedError(Exception):
    """
    Exception to denote that a callable couldn't be called, but isn't essential.
    """

    def __init__(self, *args):
        super().__init__(*args)


class VersionNotFoundException(Exception):
    """
    Exception warning about a missing version number.
    """
    pass
