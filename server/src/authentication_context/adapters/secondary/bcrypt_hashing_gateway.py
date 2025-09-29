from authentication_context.application.gateways import PasswordHashingGateway
from passlib.context import CryptContext

context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptHashingGateway(PasswordHashingGateway):
    def hash(self, password: str) -> str:
        return context.hash(password)

    def verify(self, password: str, hashed_password: str) -> bool:
        return context.verify(password, hashed_password)
