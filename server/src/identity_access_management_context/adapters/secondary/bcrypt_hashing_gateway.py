from identity_access_management_context.application.gateways import (
    PasswordHashingGateway,
)
import bcrypt
import hashlib


class BcryptHashingGateway(PasswordHashingGateway):
    def hash(self, password: str) -> str:
        password_hash_bytes = bcrypt.hashpw(
            hashlib.sha256(password.encode()).digest(), bcrypt.gensalt()
        )
        # Decode bytes to string for database storage
        return password_hash_bytes.decode("utf-8")

    def verify(self, password: str, hashed_password: str) -> bool:
        # Encode string back to bytes for bcrypt verification
        return bcrypt.checkpw(
            hashlib.sha256(password.encode()).digest(), hashed_password.encode("utf-8")
        )
