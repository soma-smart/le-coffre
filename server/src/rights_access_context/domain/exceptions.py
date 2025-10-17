from uuid import UUID


class RightAccessDomainError(Exception):
    pass


class PermissionDeniedError(RightAccessDomainError):
    def __init__(self, user_id: UUID, resource_id: UUID):
        super().__init__(
            f"User {user_id} does not have permission to share resource {resource_id}."
        )


class CannotUnshareWithOwnerError(RightAccessDomainError):
    def __init__(self, target_user_id: UUID, resource_id: UUID):
        super().__init__(
            f"Cannot unshare resource {resource_id}: user {target_user_id} is an owner."
        )


class UserNotFoundError(RightAccessDomainError):
    def __init__(self, user_id: UUID):
        super().__init__(
            f"User {user_id} does not exist."
        )
