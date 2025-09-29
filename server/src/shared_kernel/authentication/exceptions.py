class AuthenticationError(Exception):
    """Base authentication error"""

    pass


class InvalidTokenError(AuthenticationError):
    """Token is invalid or expired"""

    pass


class InsufficientPermissionsError(AuthenticationError):
    """User does not have required permissions"""

    pass


class MissingTokenError(AuthenticationError):
    """No authentication token provided"""

    pass


class NotAdminError(InsufficientPermissionsError):
    """User is not an admin"""

    pass


class MissingRoleError(InsufficientPermissionsError):
    """User does not have required role"""

    pass
