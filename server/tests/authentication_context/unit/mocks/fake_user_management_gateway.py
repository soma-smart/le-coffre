from uuid import UUID


class FakeUserManagementGateway:
    def __init__(self):
        self._admin_exists = False
        self._created_admins = []

    async def create_admin(self, user_id: UUID, email: str, display_name: str) -> None:
        if self._admin_exists:
            raise Exception("Admin already exists")
        self._admin_exists = True
        self._created_admins.append(
            {
                "user_id": user_id,
                "email": email,
                "display_name": display_name,
            }
        )

    async def can_create_admin(self) -> bool:
        return not self._admin_exists

    def set_admin_exists(self, exists: bool) -> None:
        """Test helper to simulate admin existence"""
        self._admin_exists = exists

    def get_created_admins(self) -> list:
        """Test helper to verify admin creation"""
        return self._created_admins
