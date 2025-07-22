import pytest
from unittest.mock import Mock
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.testclient import TestClient
from dependency_injector import containers, providers

from src.infra.api.router import setup_route
from src.domain.setup_info import SetupInfo


@pytest.fixture
def mock_usecase():
    mock_setup_lecoffre_usecase = Mock()

    class Container(containers.DeclarativeContainer):
        setup_lecoffre_usecase = providers.Factory(
            lambda: mock_setup_lecoffre_usecase,
        )

    container = Container()
    container.wire(modules=[setup_route])
    return mock_setup_lecoffre_usecase


@pytest.fixture
def client(mock_usecase):
    return TestClient(setup_route.router)


def test_setup_route_exists(client):
    with pytest.raises(RequestValidationError):
        client.post("/setup")


@pytest.mark.parametrize("args", ["nb_shared=2", "threshold=1"])
def test_given_missing_param_when_setup_route_called_then_fails(client, args):
    with pytest.raises(RequestValidationError):
        client.post("/setup?" + args)


@pytest.mark.parametrize("args", [[], ["1"], ["1", "2", "3", "4"]])
def test_given_use_case_succeeding_when_setup_route_called_then_returns_setup_info(
    client, mock_usecase, args
):
    mock_usecase.execute.return_value = SetupInfo(args)

    response = client.post("/setup?nb_shared=2&threshold=1")

    assert response.status_code == 200
    assert response.json() == {"shares": args}
    mock_usecase.execute.assert_called_once_with(2, 1)


def test_given_use_case_failing_when_setup_route_called_then_returns_400(
    client, mock_usecase
):
    mock_usecase.execute.side_effect = Exception("Test")

    with pytest.raises(HTTPException) as e:
        client.post("/setup?nb_shared=2&threshold=1")

    assert e.value.status_code == 400
    assert e.value.detail == "Test"
