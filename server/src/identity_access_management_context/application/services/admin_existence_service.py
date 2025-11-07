from identity_access_management_context.application.gateways import UserRepository


class AdminExistenceService:
    """Service to check if an admin user exists in the system."""

    @staticmethod
    def admin_exists(user_repository: UserRepository) -> bool:
        """Check if an admin user exists.

        Args:
            user_repository: The repository to query for admin users.

        Returns:
            True if an admin exists, False otherwise.
        """
        admin = user_repository.get_admin()
        return admin is not None
