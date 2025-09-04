from uuid import UUID, uuid4
from datetime import datetime, UTC


class AuthenticationSession:
    def __init__(self, user_id: UUID, jwt_token: str):
        self.id = uuid4()
        self.user_id = user_id
        self.jwt_token = jwt_token
        self.created_at = datetime.now(UTC)
