from typing import Protocol


class StateGenerationGateway(Protocol):
    def generate_state(self) -> str: ...
