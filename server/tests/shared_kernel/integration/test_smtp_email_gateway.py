import pytest

from shared_kernel.adapters.secondary import SmtpEmailGateway
from shared_kernel.domain.exceptions import EmailDeliveryError


def test_given_smtp_server_without_auth_when_send_should_deliver_message_to_recipient(
    smtp_server, recording_smtp_handler
):
    # Arrange
    gateway = SmtpEmailGateway(host="127.0.0.1", port=smtp_server.port, from_address="noreply@le-coffre.local")

    # Act
    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    # Assert
    assert len(recording_smtp_handler.messages) == 1
    message = recording_smtp_handler.messages[0]
    assert message["mail_from"] == "noreply@le-coffre.local"
    assert message["rcpt_tos"] == ["alice@example.com"]
    assert "Hello Alice" in message["content"]
    assert "Subject: Welcome" in message["content"]


def test_given_smtp_server_unreachable_when_send_should_raise_email_delivery_error(unreachable_smtp_port):
    # Arrange
    gateway = SmtpEmailGateway(host="127.0.0.1", port=unreachable_smtp_port, from_address="noreply@le-coffre.local")

    # Act & Assert
    with pytest.raises(EmailDeliveryError):
        gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")


def test_given_smtp_server_with_tls_when_send_should_deliver_message_to_recipient(
    smtp_server_with_tls, recording_smtp_handler, self_signed_certificate
):
    # Arrange
    _, client_ssl_context = self_signed_certificate
    gateway = SmtpEmailGateway(
        host="127.0.0.1",
        port=smtp_server_with_tls.port,
        from_address="noreply@le-coffre.local",
        use_tls=True,
        ssl_context=client_ssl_context,
    )

    # Act
    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    # Assert
    assert len(recording_smtp_handler.messages) == 1


def test_given_smtp_server_requiring_auth_when_send_with_correct_credentials_should_deliver_message(
    smtp_server_requiring_auth, recording_smtp_handler
):
    # Arrange
    gateway = SmtpEmailGateway(
        host="127.0.0.1",
        port=smtp_server_requiring_auth.port,
        from_address="noreply@le-coffre.local",
        username="smtp-user",
        password="smtp-password",
    )

    # Act
    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    # Assert
    assert len(recording_smtp_handler.messages) == 1


def test_given_smtp_server_requiring_auth_when_send_with_wrong_credentials_should_raise_email_delivery_error(
    smtp_server_requiring_auth,
):
    # Arrange
    gateway = SmtpEmailGateway(
        host="127.0.0.1",
        port=smtp_server_requiring_auth.port,
        from_address="noreply@le-coffre.local",
        username="smtp-user",
        password="wrong-password",
    )

    # Act & Assert
    with pytest.raises(EmailDeliveryError):
        gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")
