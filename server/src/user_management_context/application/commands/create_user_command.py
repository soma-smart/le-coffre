from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class CreateUserCommand:
    id: UUID
    username: str
    email: str
    password: str

    @staticmethod
    def from_dict(data: dict) -> "CreateUserCommand":
        return CreateUserCommand(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            username=data["username"],
            email=data["email"],
            password=data["password"],
        )
