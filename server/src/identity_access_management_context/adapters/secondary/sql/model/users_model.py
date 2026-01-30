from uuid import UUID, uuid4
from typing import Optional
from sqlmodel import SQLModel, Field
import json


class UserTable(SQLModel, table=True):
    __tablename__ = "UserTable"

    id: UUID = Field(
        default_factory=uuid4, nullable=False, primary_key=True, index=True
    )
    username: str = Field(nullable=False)
    email: str = Field(nullable=False)
    name: str = Field(nullable=False)
    roles: str = Field(default="[]", description="Roles as JSON string")
    password_hash: Optional[str] = Field(nullable=True)

    @property
    def roles_list(self):
        return json.loads(self.roles)

    @roles_list.setter
    def roles_list(self, value):
        self.roles = json.dumps(value)
