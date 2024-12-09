class SteamKeyNotAvailable(Exception):
    """
    The Steam Key could not be found.
    """
    pass


class SteamResourceNotAvailable(Exception):
    """
    The requested Steam resource was not available or was not found.
    """
    pass


class DatabaseDeletionError(Exception):
    """
    There was a problem deleting entries from the Database.
    """
    pass


class DatabaseUpdateError(Exception):
    """
    There was a problem updating the entries from the Database.,
    """

    pass


class WrongScriptInput(Exception):
    """
    The script received the wrong input.
    """

    pass
