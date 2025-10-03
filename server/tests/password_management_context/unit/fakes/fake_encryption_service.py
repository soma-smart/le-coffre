from shared_kernel.encryption import EncryptionService


class FakeEncryptionService(EncryptionService):
    def encrypt(self, plaintext: str) -> str:
        return f"encrypted({plaintext})"

    def decrypt(self, ciphertext: str) -> str:
        return ciphertext.replace("encrypted(", "").replace(")", "")
