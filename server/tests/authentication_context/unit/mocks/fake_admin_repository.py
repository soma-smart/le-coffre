from typing import Dict, Optional
from uuid import UUID

from authentication_context.domain.entities import AdminAccount


class FakeAdminRepository:
    def __init__(self):
        self._admins: Dict[UUID, AdminAccount] = {}

    def save(self, admin: AdminAccount) -> None:
        self._admins[admin.id] = admin

    def get_by_id(self, admin_id: UUID) -> Optional[AdminAccount]:
        return self._admins.get(admin_id)

    def get_by_email(self, email: str) -> Optional[AdminAccount]:
        for admin in self._admins.values():
            if admin.email == email:
                return admin
        return None

    def exists_any(self) -> bool:
        return len(self._admins) > 0
