from src.application.setup import setup_master_password


def test_given_a_master_password_when_setup_then_application_is_marked_as_setup():
    password = "SuperSecret123!"
    setup_status = setup_master_password(password)
    assert setup_status == True
