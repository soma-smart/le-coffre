from vault_management_context.application.commands import GetVaultStatusCommand
from vault_management_context.application.responses import VaultStatus
from vault_management_context.application.use_cases import GetVaultStatusUseCase
from vault_management_context.domain.exceptions import VaultIsLockedError


class VaultStatusApi:
    def __init__(self, get_vault_status_use_case: GetVaultStatusUseCase):
        self._get_vault_status_use_case = get_vault_status_use_case

    def ensure_vault_is_unlocked(self) -> None:
        status = self._get_vault_status_use_case.execute(GetVaultStatusCommand())
        if status is not VaultStatus.UNLOCKED:
            raise VaultIsLockedError()
