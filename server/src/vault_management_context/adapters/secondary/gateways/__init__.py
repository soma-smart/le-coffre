from .crypto.crypto_shamir_gateway import CryptoShamirGateway
from .crypto.aes_encryption_gateway import AesEncryptionGateway

from .in_memory_vault_session_gateway import InMemoryVaultSessionGateway

from .sql.sql_vault_repository import SqlVaultRepository
from .sql.models.vault import create_vault_table


def create_tables(engine):
    create_vault_table(engine)
