class AuthenticationError(Exception):
    """Base authentication error"""

    pass


class InvalidTokenError(AuthenticationError):
    """Token is invalid or expired"""

    pass


class MissingTokenError(AuthenticationError):
    """No authentication token provided"""

    pass
