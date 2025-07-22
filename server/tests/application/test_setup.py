import pytest


from src.application.usecase.setup_lecoffre import SetupLecoffreUseCase


class MockSetupStore:
    def __init__(self):
        self._setup_info = None

    def get_setup(self):
        return self._setup_info

    def mark_setup(self, setup_info):
        self._setup_info = setup_info


@pytest.fixture()
def setup_use_case():
    store = MockSetupStore()
    return SetupLecoffreUseCase(store)


@pytest.mark.parametrize("num_shares, threshold", [(5, 3), (6, 4), (7, 5)])
def test_given_shares_and_threshold_when_setup_then_application_is_marked_as_setup(
    num_shares, threshold, setup_use_case
):
    setup_status = setup_use_case.execute(num_shares, threshold)
    assert len(setup_status.shares) == num_shares


def test_given_setup_already_done_when_setup_called_again_then_should_fail(
    setup_use_case,
):
    num_shares = 5
    threshold = 3
    setup_use_case.execute(num_shares, threshold)
    with pytest.raises(Exception):
        setup_use_case.execute(7, 4)


def test_given_threshold_higher_than_num_shares_when_setup_then_should_fail(
    setup_use_case,
):
    num_shares = 3
    threshold = 5
    with pytest.raises(Exception):
        setup_use_case.execute(num_shares, threshold)


def test_given_num_shares_less_than_2_when_setup_then_should_fail(setup_use_case):
    num_shares = 1
    threshold = 2
    with pytest.raises(Exception):
        setup_use_case.execute(num_shares, threshold)


def test_given_threshold_less_than_2_when_setup_then_should_fail(setup_use_case):
    num_shares = 2
    threshold = 1
    with pytest.raises(Exception):
        setup_use_case.execute(num_shares, threshold)
