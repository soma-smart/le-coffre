from dependency_injector import containers, providers

from src.infra.repo.inmemory.fake_setup_state_repo import FakeSetupStateRepo
from src.application.usecase.setup_lecoffre import SetupLecoffreUseCase


class Container(containers.DeclarativeContainer):
    setup_state_store = providers.Singleton(FakeSetupStateRepo)
    setup_lecoffre_usecase = providers.Factory(
        SetupLecoffreUseCase,
        store=setup_state_store,
    )
