from identity_access_management_context.application.gateways import (
    PasswordHashingGateway,
)
import bcrypt


class BcryptHashingGateway(PasswordHashingGateway):
    def hash(self, password: str) -> bytes:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def verify(self, password: str, hashed_password: bytes) -> bool:
        return bcrypt.checkpw(password.encode(), hashed_password)
