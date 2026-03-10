from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects import ADMIN_ROLE


class AdminPermissionChecker:
    """Centralized admin permission checker for the application."""

    ADMIN_ROLE = ADMIN_ROLE

    @classmethod
    def ensure_admin(
        cls,
        requesting_user: AuthenticatedUser,
        operation: str = "perform this operation",
    ) -> None:
        """
        Ensures that the requesting user has admin permissions.

        Args:
            requesting_user: The user making the request
            operation: Description of the operation being performed (for error message)

        Raises:
            NotAdminError: If the user doesn't have admin permissions
        """
        if cls.ADMIN_ROLE not in requesting_user.roles:
            raise NotAdminError(f"Only administrators can {operation}")

    @classmethod
    def is_admin(cls, requesting_user: AuthenticatedUser) -> bool:
        """
        Checks if the requesting user has admin permissions.

        Args:
            requesting_user: The user to check

        Returns:
            True if the user has admin permissions, False otherwise
        """
        return cls.ADMIN_ROLE in requesting_user.roles
