import os
import ssl

import pytest

from shared_kernel.adapters.secondary import SmtpEmailGateway
from shared_kernel.adapters.secondary.smtp_email_gateway import SmtpTlsMode
from shared_kernel.domain.exceptions import EmailDeliveryError


def _trusting_ssl_context() -> ssl.SSLContext:
    """A client SSLContext trusting smtpdfix's auto-generated server certificate."""
    return ssl.create_default_context(cafile=os.environ["SMTPD_SSL_CERTIFICATE_FILE"])


def test_given_smtp_server_without_auth_when_send_should_deliver_message_to_recipient(smtpd):
    # Arrange
    gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")

    # Act
    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    # Assert
    assert len(smtpd.messages) == 1
    message = smtpd.messages[0]
    assert message["From"] == "noreply@le-coffre.local"
    assert message["To"] == "alice@example.com"
    assert message["Subject"] == "Welcome"
    assert "Hello Alice" in message.get_payload()


def test_given_smtp_server_unreachable_when_send_should_raise_email_delivery_error(unreachable_smtp_port):
    # Arrange
    gateway = SmtpEmailGateway(host="127.0.0.1", port=unreachable_smtp_port, from_address="noreply@le-coffre.local")

    # Act & Assert
    with pytest.raises(EmailDeliveryError):
        gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")


def test_given_subject_with_embedded_newline_when_send_should_raise_email_delivery_error(smtpd):
    # Arrange
    gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")

    # Act & Assert
    with pytest.raises(EmailDeliveryError):
        gateway.send(to="alice@example.com", subject="Welcome\nBcc: attacker@evil.com", body="Hello Alice")


@pytest.mark.parametrize(
    "to",
    ["alice@example.com, bob@example.com", "undisclosed-recipients:;"],
    ids=["address-list", "no-address"],
)
def test_given_recipient_not_a_single_address_when_send_should_raise_email_delivery_error_without_delivering(smtpd, to):
    # Arrange
    gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")

    # Act & Assert
    with pytest.raises(EmailDeliveryError):
        gateway.send(to=to, subject="Welcome", body="Hello Alice")
    assert smtpd.messages == []


def test_given_smtp_server_with_implicit_tls_when_send_should_deliver_message_to_recipient(smtpd):
    # Arrange
    smtpd.config.use_ssl = True
    gateway = SmtpEmailGateway(
        host=smtpd.hostname,
        port=smtpd.port,
        from_address="noreply@le-coffre.local",
        tls_mode=SmtpTlsMode.IMPLICIT,
        ssl_context=_trusting_ssl_context(),
    )

    # Act
    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    # Assert
    assert len(smtpd.messages) == 1


def test_given_smtp_server_with_starttls_when_send_should_deliver_message_to_recipient(smtpd):
    # Arrange
    smtpd.config.use_starttls = True
    gateway = SmtpEmailGateway(
        host=smtpd.hostname,
        port=smtpd.port,
        from_address="noreply@le-coffre.local",
        tls_mode=SmtpTlsMode.STARTTLS,
        ssl_context=_trusting_ssl_context(),
    )

    # Act
    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    # Assert
    assert len(smtpd.messages) == 1


def test_given_smtp_server_requiring_auth_when_send_with_correct_credentials_over_starttls_should_deliver_message(
    smtpd,
):
    # Arrange
    smtpd.config.use_starttls = True
    smtpd.config.enforce_auth = True
    gateway = SmtpEmailGateway(
        host=smtpd.hostname,
        port=smtpd.port,
        from_address="noreply@le-coffre.local",
        username=smtpd.config.login_username,
        password=smtpd.config.login_password,
        tls_mode=SmtpTlsMode.STARTTLS,
        ssl_context=_trusting_ssl_context(),
    )

    # Act
    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    # Assert
    assert len(smtpd.messages) == 1


def test_given_smtp_server_requiring_auth_when_send_with_wrong_credentials_over_starttls_should_raise_email_delivery_error(
    smtpd,
):
    # Arrange
    smtpd.config.use_starttls = True
    smtpd.config.enforce_auth = True
    gateway = SmtpEmailGateway(
        host=smtpd.hostname,
        port=smtpd.port,
        from_address="noreply@le-coffre.local",
        username=smtpd.config.login_username,
        password="wrong-password",
        tls_mode=SmtpTlsMode.STARTTLS,
        ssl_context=_trusting_ssl_context(),
    )

    # Act & Assert
    with pytest.raises(EmailDeliveryError):
        gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")


def test_given_credentials_configured_without_tls_when_constructing_gateway_should_raise_value_error():
    # Act & Assert
    with pytest.raises(ValueError, match="TLS"):
        SmtpEmailGateway(
            host="127.0.0.1",
            port=25,
            from_address="noreply@le-coffre.local",
            username="smtp-user",
            password="smtp-password",
            tls_mode=SmtpTlsMode.NONE,
        )


@pytest.mark.parametrize(
    ("username", "password"),
    [("smtp-user", None), (None, "smtp-password")],
    ids=["username-without-password", "password-without-username"],
)
def test_given_incomplete_credentials_when_constructing_gateway_should_raise_value_error(username, password):
    # Act & Assert
    with pytest.raises(ValueError, match="username and password"):
        SmtpEmailGateway(
            host="127.0.0.1",
            port=587,
            from_address="noreply@le-coffre.local",
            username=username,
            password=password,
            tls_mode=SmtpTlsMode.STARTTLS,
        )
