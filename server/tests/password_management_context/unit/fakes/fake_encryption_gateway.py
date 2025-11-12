from shared_kernel.application.gateways import EncryptionGateway


class FakeEncryptionGateway(EncryptionGateway):
    def encrypt(self, plaintext: str) -> str:
        return f"encrypted({plaintext})"

    def decrypt(self, ciphertext: str) -> str:
        return ciphertext.replace("encrypted(", "").replace(")", "")
