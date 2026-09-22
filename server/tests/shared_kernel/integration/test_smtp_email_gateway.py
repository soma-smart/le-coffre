import os
import ssl

import pytest

from shared_kernel.adapters.secondary import SmtpEmailGateway
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


def test_given_smtp_server_with_tls_when_send_should_deliver_message_to_recipient(smtpd):
    # Arrange
    smtpd.config.use_ssl = True
    gateway = SmtpEmailGateway(
        host=smtpd.hostname,
        port=smtpd.port,
        from_address="noreply@le-coffre.local",
        use_tls=True,
        ssl_context=_trusting_ssl_context(),
    )

    # Act
    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    # Assert
    assert len(smtpd.messages) == 1


def test_given_smtp_server_requiring_auth_when_send_with_correct_credentials_should_deliver_message(smtpd):
    # Arrange
    smtpd.config.enforce_auth = True
    smtpd.config.auth_require_tls = False
    gateway = SmtpEmailGateway(
        host=smtpd.hostname,
        port=smtpd.port,
        from_address="noreply@le-coffre.local",
        username=smtpd.config.login_username,
        password=smtpd.config.login_password,
    )

    # Act
    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    # Assert
    assert len(smtpd.messages) == 1


def test_given_smtp_server_requiring_auth_when_send_with_wrong_credentials_should_raise_email_delivery_error(smtpd):
    # Arrange
    smtpd.config.enforce_auth = True
    smtpd.config.auth_require_tls = False
    gateway = SmtpEmailGateway(
        host=smtpd.hostname,
        port=smtpd.port,
        from_address="noreply@le-coffre.local",
        username=smtpd.config.login_username,
        password="wrong-password",
    )

    # Act & Assert
    with pytest.raises(EmailDeliveryError):
        gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")
