from shared_kernel.encryption import EncryptionService

from vault_management_context.application.use_cases import (
    EncryptUseCase,
    DecryptUseCase,
)


class EncryptionApi(EncryptionService):
    def __init__(
        self, encrypt_use_case: EncryptUseCase, decrypt_use_case: DecryptUseCase
    ):
        self.encrypt_use_case = encrypt_use_case
        self.decrypt_use_case = decrypt_use_case

    def encrypt(self, plaintext: str) -> str:
        return self.encrypt_use_case.execute(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        return self.decrypt_use_case.execute(ciphertext)
