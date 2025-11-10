from uuid import UUID


# Authorization Exceptions


class InsufficientPermissionsError(Exception):
    """User does not have required permissions/roles."""

    pass


class NotAdminError(InsufficientPermissionsError):
    """User is not an admin."""

    def __init__(self, operation: str):
        super().__init__(f"Only administrators can {operation}")


class MissingRoleError(InsufficientPermissionsError):
    """User does not have required role."""

    pass


# Resource Access Exceptions


class AccessDeniedError(Exception):
    """User does not have access to a specific resource."""

    def __init__(self, user_id: UUID, resource_id: UUID):
        super().__init__(f"Access denied for user {user_id} on resource {resource_id}")


# User Exceptions


class UserNotFoundError(Exception):
    """User does not exist."""

    def __init__(self, user_id: UUID):
        super().__init__(f"User {user_id} does not exist")
