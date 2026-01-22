from identity_access_management_context.application.gateways import (
    SsoConfigurationRepository,
)
from identity_access_management_context.domain.entities import SsoConfiguration


class FakeSsoConfigurationRepository(SsoConfigurationRepository):
    def __init__(self):
        self._config: SsoConfiguration | None = None

    def save(self, config: SsoConfiguration) -> None:
        self._config = config

    def get(self) -> SsoConfiguration | None:
        return self._config
