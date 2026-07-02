from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from password_management_context.adapters.primary.fastapi.routes.password_create_routes import (
    router as create_password_router,
)
from password_management_context.adapters.primary.fastapi.routes.password_update_routes import (
    router as update_password_router,
)
from shared_kernel.domain.entities import ValidatedUser


class _UseCaseShouldNotExecute:
    def execute(self, *_args, **_kwargs):
        raise AssertionError("unsafe payload should be rejected before the use case executes")


def _create_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides.clear()

    async def current_user_override():
        return ValidatedUser(
            user_id=UUID("11111111-1111-1111-1111-111111111111"),
            email="admin@example.com",
            display_name="Admin",
            roles=["ADMIN"],
        )

    def create_usecase_override():
        return _UseCaseShouldNotExecute()

    def update_usecase_override():
        return _UseCaseShouldNotExecute()

    from password_management_context.adapters.primary.fastapi.app_dependencies import (
        get_create_password_usecase,
        get_update_password_usecase,
    )
    from shared_kernel.adapters.primary.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = current_user_override
    app.dependency_overrides[get_create_password_usecase] = create_usecase_override
    app.dependency_overrides[get_update_password_usecase] = update_usecase_override
    app.include_router(create_password_router)
    app.include_router(update_password_router)
    return app


def test_given_javascript_url_when_creating_password_should_return_422():
    with TestClient(_create_app()) as client:
        response = client.post(
            "/passwords/",
            json={
                "name": "malicious",
                "password": "secret",
                "group_id": str(uuid4()),
                "url": "javascript:alert(1)",
            },
        )

    assert response.status_code == 422


def test_given_data_url_when_updating_password_should_return_422():
    with TestClient(_create_app()) as client:
        response = client.put(
            f"/passwords/{uuid4()}",
            json={
                "name": "malicious",
                "url": "data:text/html,<script>alert(1)</script>",
            },
        )

    assert response.status_code == 422
