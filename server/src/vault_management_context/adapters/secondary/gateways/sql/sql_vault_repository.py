from typing import Optional
from sqlmodel import Session, select

from .models.vault import VaultTable
from vault_management_context.domain.entities import Vault
from vault_management_context.application.gateways.vault_repository import (
    VaultRepository,
)


class SqlVaultRepository(VaultRepository):
    def __init__(self, session: Session):
        self._session = session

    def get(self) -> Optional[Vault]:
        statement = select(VaultTable).where(VaultTable.id == 1)
        vault_row = self._session.exec(statement).first()

        if vault_row is None:
            return None

        return Vault(
            nb_shares=vault_row.nb_shares,
            threshold=vault_row.threshold,
            encrypted_key=vault_row.encrypted_key,
        )

    def save(self, vault: Vault) -> None:
        statement = select(VaultTable).where(VaultTable.id == 1)
        existing_vault = self._session.exec(statement).first()

        if existing_vault:
            self._update(existing_vault, vault)
        else:
            self._create(vault)

        self._session.commit()

    def _update(self, existing_vault: VaultTable, vault: Vault) -> None:
        existing_vault.nb_shares = vault.nb_shares
        existing_vault.threshold = vault.threshold
        existing_vault.encrypted_key = vault.encrypted_key

    def _create(self, vault: Vault) -> None:
        vault_row = VaultTable(
            id=1,
            nb_shares=vault.nb_shares,
            threshold=vault.threshold,
            encrypted_key=vault.encrypted_key,
        )
        self._session.add(vault_row)
