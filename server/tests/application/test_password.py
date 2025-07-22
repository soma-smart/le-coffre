import pytest

from src.application.usecase.generate_password import GeneratePasswordUseCase


@pytest.mark.parametrize("length", [1, 2, 3, 4, 5, 6, 7, 8])
def test_generate_password_too_short_raises_value_error(length):
    with pytest.raises(ValueError):
        GeneratePasswordUseCase().execute(length)


@pytest.mark.parametrize("length", [12, 20, 100])
def test_generate_password_with_given_length(length):
    password = GeneratePasswordUseCase().execute(length)
    assert isinstance(password, str)
    assert len(password) == length
