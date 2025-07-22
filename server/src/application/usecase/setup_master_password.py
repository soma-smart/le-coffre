from typing import Optional

from src.application.port.setup_state_store import SetupStateStore

from src.domain.vault_setup import setup_master_password
from src.domain.setup_info import SetupInfo


class SetupMasterPasswordUseCase:
    def __init__(self, store: SetupStateStore):
        self.store = store

    def execute(self, nb_shared: int, threshold: int) -> SetupInfo:
        setup_info: Optional[SetupInfo] = self.store.get_setup()

        new_setup_info = setup_master_password(setup_info, nb_shared, threshold)

        self.store.mark_setup(new_setup_info)

        return new_setup_info
