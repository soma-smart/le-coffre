from user_management_context.application.interfaces import HashingGateway
from passlib.context import CryptContext

context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptHashingGateway(HashingGateway):
    def hash(self, plain_text: str) -> str:
        return context.hash(plain_text)

    def compare(self, plain_text: str, hashed_text: str) -> bool:
        return context.verify(plain_text, hashed_text)
