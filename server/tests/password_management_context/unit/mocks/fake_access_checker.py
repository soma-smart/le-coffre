from uuid import UUID
from shared_kernel.access_control.access_checker import AccessChecker


class FakeAccessChecker(AccessChecker):
    def __init__(self):
        self.allowed_access = {}

    def grant_access(self, user_id: UUID, resource_id: UUID):
        key = f"{user_id}:{resource_id}"
        self.allowed_access[key] = True

    def check_access(self, user_id: UUID, resource_id: UUID) -> bool:
        key = f"{user_id}:{resource_id}"
        return self.allowed_access.get(key, False)
