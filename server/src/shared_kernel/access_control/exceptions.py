from uuid import UUID


class AccessDeniedError(Exception):
    def __init__(self, user_id: UUID, resource_id: UUID):
        super().__init__(f"Access denied for user {user_id} on resource {resource_id}")
