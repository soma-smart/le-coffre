from src.application.port.setup_state_store import SetupStateStore
from src.domain.setup_info import SetupInfo


class InMemorySetupStateStore(SetupStateStore):
    def __init__(self):
        self._setup = None

    def get_setup(self) -> SetupInfo | None:
        return self._setup

    def mark_setup(self, setup_info: SetupInfo) -> None:
        self._setup = setup_info
