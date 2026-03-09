"""
Application Service for user management operations.
This service contains business logic that can be reused across multiple use cases.
"""

from uuid import UUID

from identity_access_management_context.application.gateways import (
    PasswordHashingGateway,
    UserRepository,
)
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import (
    AdminAlreadyExistsError,
)
from shared_kernel.domain.value_objects.constants import ADMIN_ROLE


class UserManagementService:
    """
    Application service that orchestrates user creation operations.
    Can be used by multiple use cases without coupling them together.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_hashing_gateway: PasswordHashingGateway,
    ):
        self._user_repository = user_repository
        self._password_hashing_gateway = password_hashing_gateway

    def create_admin(
        self,
        user_id: UUID,
        email: str,
        username: str,
        name: str,
    ) -> User:
        """
        Create an admin user with the admin role.
        Checks that no admin exists before creating.

        Args:
            user_id: The unique identifier for the user
            email: User's email address
            username: User's username
            name: User's display name
            password: Optional password (will be hashed if provided)

        Returns:
            The created User entity

        Raises:
            AdminAlreadyExistsError: If an admin already exists
        """
        # Check if an admin already exists
        existing_admin = self._user_repository.get_admin()
        if existing_admin is not None:
            raise AdminAlreadyExistsError()

        # Create user with admin role
        admin = User(id=user_id, email=email, username=username, name=name, roles=[ADMIN_ROLE])

        self._user_repository.save(admin)
        return admin

    def create_user(
        self,
        user_id: UUID,
        email: str,
        username: str,
        name: str,
        roles: list[str] | None = None,
    ) -> User:
        """
        Create a regular user (non-admin).

        Args:
            user_id: The unique identifier for the user
            email: User's email address
            username: User's username
            name: User's display name
            password: Optional password (will be hashed if provided)
            roles: Optional list of roles (defaults to empty list)

        Returns:
            The created User entity
        """
        # Create user with specified roles (or empty list)
        user = User(
            id=user_id,
            email=email,
            username=username,
            name=name,
            roles=roles or [],
        )

        self._user_repository.save(user)
        return user

    def can_create_admin(self) -> bool:
        """
        Check if an admin can be created (i.e., no admin exists yet).

        Returns:
            True if no admin exists, False otherwise
        """
        existing_admin = self._user_repository.get_admin()
        return existing_admin is None
