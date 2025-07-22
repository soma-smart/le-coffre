from dependency_injector import containers, providers

from src.infra.repo.inmemory.in_memory_setup_state_store import InMemorySetupStateStore
from src.application.usecase.setup_lecoffre import SetupLecoffreUseCase


class Container(containers.DeclarativeContainer):
    setup_state_store = providers.Singleton(InMemorySetupStateStore)
    setup_lecoffre_usecase = providers.Factory(
        SetupLecoffreUseCase,
        store=setup_state_store,
    )
