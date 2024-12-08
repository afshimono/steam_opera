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
