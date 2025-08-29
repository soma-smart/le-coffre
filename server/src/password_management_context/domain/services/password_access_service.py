from uuid import UUID

from password_management_context.domain.entities import Password
from shared_kernel.access_control import AccessController, AccessDeniedError


class PasswordAccessService:
    """Domain service that encapsulates password access control logic"""

    @staticmethod
    def ensure_access(
        access_controller: AccessController, user_id: UUID, password_id: UUID
    ) -> None:
        """
        Domain logic: Ensure user has access to password
        Raises AccessDeniedError if access is denied.
        """
        if not access_controller.check_access(user_id, password_id):
            raise AccessDeniedError(user_id, password_id)
