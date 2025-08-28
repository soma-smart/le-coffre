from uuid import UUID

from password_management_context.domain.entities import Password
from shared_kernel.access_control import AccessController, AccessDeniedError


class PasswordAccessService:
    """Domain service that encapsulates password access control logic"""

    @staticmethod
    def ensure_access_and_get_password(
        access_controller: AccessController, user_id: UUID, password: Password
    ) -> Password:
        """
        Domain logic: Ensure user has access to password and return it.
        Raises AccessDeniedError if access is denied.
        """
        if not access_controller.check_access(user_id, password.id):
            raise AccessDeniedError(user_id, password.id)

        return password
