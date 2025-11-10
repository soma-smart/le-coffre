from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.exceptions import NotAdminError
from shared_kernel.domain.value_objects import ADMIN_ROLE


class AdminPermissionService:
    @staticmethod
    def is_admin(user: AuthenticatedUser) -> bool:
        return ADMIN_ROLE in user.roles

    @staticmethod
    def ensure_admin(
        user: AuthenticatedUser, operation: str = "perform this operation"
    ) -> None:
        if not AdminPermissionService.is_admin(user):
            raise NotAdminError(operation)
