from uuid import UUID
from typing import List, Optional
from sqlmodel import CheckConstraint, SQLModel, Field
import json

class UserTable(SQLModel, table=True):
  __tablename__="UserTable"
  
  id: UUID = Field(default_factory=UUID, nullable=False, primary_key=True, index=True)
  username: str = Field(nullable=False)
  email: str = Field(nullable=False)
  name: str = Field(nullable=False)
  roles: str = Field(default="[]", description="Roles as JSON string")

  @property
  def roles_list(self):
      return json.loads(self.roles)

  @roles_list.setter
  def roles_list(self, value):
      self.roles = json.dumps(value)
