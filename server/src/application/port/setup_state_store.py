from typing import Protocol

from src.domain.setup_info import SetupInfo


class SetupStateStore(Protocol):
    def get_setup(self) -> SetupInfo | None: ...
    def mark_setup(self, setup_info: SetupInfo) -> None: ...
