import hashlib

import bcrypt

from identity_access_management_context.application.gateways import (
    PasswordHashingGateway,
)


class BcryptHashingGateway(PasswordHashingGateway):
    def hash(self, password: str) -> bytes:
        return bcrypt.hashpw(hashlib.sha256(password.encode()).digest(), bcrypt.gensalt())

    def verify(self, password: str, hashed_password: bytes) -> bool:
        return bcrypt.checkpw(hashlib.sha256(password.encode()).digest(), hashed_password)
