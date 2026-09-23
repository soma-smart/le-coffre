"""How the service account routes answer failures coming out of a use case.

A mapped domain error becomes its HTTP status; anything else is logged and
sanitised into a 500 rather than escaping the handler.
"""

import logging
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_service_accounts_usecase,
)
from identity_access_management_context.adapters.primary.fastapi.routes.service_account.service_account_routes import (
    router as service_account_router,
)
from identity_access_management_context.domain.exceptions import GroupNotFoundException
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

BASE = "/iam/service-accounts"


class _FailingUseCase:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def execute(self, *_args, **_kwargs):
        raise self._error


def _client(error: Exception) -> TestClient:
    app = FastAPI()

    async def current_user_override() -> ValidatedUser:
        return ValidatedUser(
            user_id=UUID("11111111-1111-1111-1111-111111111111"),
            email="owner@example.com",
            display_name="Owner",
            roles=["USER"],
        )

    app.dependency_overrides[get_current_user] = current_user_override
    app.dependency_overrides[get_list_service_accounts_usecase] = lambda: _FailingUseCase(error)
    app.include_router(service_account_router)
    return TestClient(app)


def test_given_a_mapped_domain_error_when_listing_should_return_its_status():
    group_id = uuid4()

    with _client(GroupNotFoundException(group_id)) as client:
        response = client.get(BASE, params={"group_id": str(group_id)})

    assert response.status_code == 404
    assert str(group_id) in response.json()["detail"]


def test_given_an_unmapped_error_when_listing_should_log_it_and_return_a_sanitised_500(
    caplog: pytest.LogCaptureFixture,
):
    with caplog.at_level(logging.ERROR), _client(RuntimeError("connection reset by peer")) as client:
        response = client.get(BASE, params={"group_id": str(uuid4())})

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "connection reset by peer" not in response.text
    assert "Unexpected error in list service accounts" in caplog.text
    assert "connection reset by peer" in caplog.text, "the original failure must reach the logs"
