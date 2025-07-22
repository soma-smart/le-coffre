import pytest
from fastapi.testclient import TestClient

from src.infra.api.router.setup_route import router


@pytest.fixture
def client():
    return TestClient(router)


def test_setup_route_exists(client):
    response = client.get("/setup")
    assert response.status_code != 404
