from dependency_injector import containers, providers

from src.infra.repo.inmemory.in_memory_setup_state_store import InMemorySetupStateStore
from src.application.usecase.setup_master_password import SetupMasterPasswordUseCase


class Container(containers.DeclarativeContainer):
    setup_state_store = providers.Singleton(InMemorySetupStateStore)
    setup_master_password_usecase = providers.Factory(
        SetupMasterPasswordUseCase,
        store=setup_state_store,
    )
