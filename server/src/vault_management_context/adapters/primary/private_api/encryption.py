from vault_management_context.application.commands import DecryptCommand, EncryptCommand
from vault_management_context.application.use_cases import (
    DecryptUseCase,
    EncryptUseCase,
)


class EncryptionApi:
    def __init__(self, encrypt_use_case: EncryptUseCase, decrypt_use_case: DecryptUseCase):
        self.encrypt_use_case = encrypt_use_case
        self.decrypt_use_case = decrypt_use_case

    def encrypt(self, plaintext: str) -> str:
        command = EncryptCommand(decrypted_data=plaintext)
        return self.encrypt_use_case.execute(command)

    def decrypt(self, ciphertext: str) -> str:
        command = DecryptCommand(encrypted_data=ciphertext)
        return self.decrypt_use_case.execute(command)
