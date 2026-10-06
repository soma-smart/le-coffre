import logging
import os
import smtplib
import ssl

import pytest

from shared_kernel.adapters.secondary import SmtpEmailGateway
from shared_kernel.adapters.secondary.smtp_email_gateway import SmtpTlsMode
from shared_kernel.domain.exceptions import EmailDeliveryError
from shared_kernel.domain.value_objects import OutgoingEmail


def _trusting_ssl_context() -> ssl.SSLContext:
    """A client SSLContext trusting smtpdfix's auto-generated server certificate."""
    return ssl.create_default_context(cafile=os.environ["SMTPD_SSL_CERTIFICATE_FILE"])


def _count_smtp_connections(monkeypatch) -> list[int]:
    """Counts real TCP connections opened by smtplib, via the method __init__ always
    calls to establish one — the same hook works for both SMTP and its SMTP_SSL
    subclass. Returns a single-element list so the caller can read the live count."""
    count = [0]
    original_connect = smtplib.SMTP.connect

    def counting_connect(self, *args, **kwargs):
        count[0] += 1
        return original_connect(self, *args, **kwargs)

    monkeypatch.setattr(smtplib.SMTP, "connect", counting_connect)
    return count


def _count_smtp_closes(monkeypatch) -> list[int]:
    """Counts real socket closes, via the method both SMTP and SMTP_SSL route
    through. Returns a single-element list so the caller can read the live count."""
    count = [0]
    original_close = smtplib.SMTP.close

    def counting_close(self, *args, **kwargs):
        count[0] += 1
        return original_close(self, *args, **kwargs)

    monkeypatch.setattr(smtplib.SMTP, "close", counting_close)
    return count


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


def test_given_wrong_credentials_when_send_should_still_close_the_socket(smtpd, monkeypatch):
    # Regression: a failed login() happens after the TCP/TLS connection is already
    # up. Unlike `with smtplib.SMTP(...) as client:`, a plain _open_connection()
    # call has no __exit__ to fall back on if it raises before returning — an
    # earlier version of this fix leaked that socket, open, until garbage
    # collection, which was observed to stall smtpd's own test-fixture teardown.
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
    closes = _count_smtp_closes(monkeypatch)

    with pytest.raises(EmailDeliveryError):
        gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")

    assert closes == [1]


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


def test_given_several_recipients_when_send_bulk_should_reuse_one_connection(smtpd, monkeypatch):
    # Regression: send() used to open one connection per recipient; a broadcast to
    # many opted-in users must not open that many SMTP connections in series.
    connections = _count_smtp_connections(monkeypatch)
    gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")
    emails = [
        OutgoingEmail(to="alice@example.com", subject="Welcome", body="Hello Alice"),
        OutgoingEmail(to="bob@example.com", subject="Welcome", body="Hello Bob"),
        OutgoingEmail(to="carol@example.com", subject="Welcome", body="Hello Carol"),
    ]

    failures = gateway.send_bulk(emails)

    assert failures == []
    assert connections == [1]
    assert [m["To"] for m in smtpd.messages] == ["alice@example.com", "bob@example.com", "carol@example.com"]


def test_given_empty_list_when_send_bulk_should_not_connect(smtpd, monkeypatch):
    connections = _count_smtp_connections(monkeypatch)
    gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")

    assert gateway.send_bulk([]) == []
    assert connections == [0]


def test_given_one_bad_recipient_when_send_bulk_should_still_deliver_the_others(smtpd):
    gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")
    emails = [
        OutgoingEmail(to="alice@example.com", subject="Welcome", body="Hello Alice"),
        OutgoingEmail(to="alice@example.com, bob@example.com", subject="Welcome", body="not a single address"),
        OutgoingEmail(to="carol@example.com", subject="Welcome", body="Hello Carol"),
    ]

    failures = gateway.send_bulk(emails)

    assert [to for to, _error in failures] == ["alice@example.com, bob@example.com"]
    assert [m["To"] for m in smtpd.messages] == ["alice@example.com", "carol@example.com"]


def test_given_smtp_server_unreachable_when_send_bulk_should_raise_email_delivery_error(unreachable_smtp_port):
    gateway = SmtpEmailGateway(host="127.0.0.1", port=unreachable_smtp_port, from_address="noreply@le-coffre.local")
    emails = [OutgoingEmail(to="alice@example.com", subject="Welcome", body="Hello Alice")]

    with pytest.raises(EmailDeliveryError):
        gateway.send_bulk(emails)


def test_given_smtp_server_requiring_auth_when_send_bulk_should_authenticate_once(smtpd, monkeypatch):
    smtpd.config.use_starttls = True
    smtpd.config.enforce_auth = True
    connections = _count_smtp_connections(monkeypatch)
    gateway = SmtpEmailGateway(
        host=smtpd.hostname,
        port=smtpd.port,
        from_address="noreply@le-coffre.local",
        username=smtpd.config.login_username,
        password=smtpd.config.login_password,
        tls_mode=SmtpTlsMode.STARTTLS,
        ssl_context=_trusting_ssl_context(),
    )
    emails = [
        OutgoingEmail(to="alice@example.com", subject="Welcome", body="Hello Alice"),
        OutgoingEmail(to="bob@example.com", subject="Welcome", body="Hello Bob"),
    ]

    failures = gateway.send_bulk(emails)

    assert failures == []
    assert connections == [1]
    assert len(smtpd.messages) == 2


def _make_quit_misbehave(monkeypatch) -> None:
    """A relay replying with anything other than 221 to QUIT makes smtplib's own
    quit() raise smtplib.SMTPResponseException — same shape as e.g. a relay that
    drops the connection mid-QUIT or answers with a transient error code."""

    def broken_quit(self):
        raise smtplib.SMTPResponseException(451, b"backing off, try again")

    monkeypatch.setattr(smtplib.SMTP, "quit", broken_quit)


def test_given_relay_misbehaves_on_quit_when_send_bulk_should_still_report_full_delivery(smtpd, monkeypatch):
    # Regression: closing used to go through smtplib's own context-manager __exit__,
    # which sends QUIT and raises if the reply isn't exactly 221. That raise happened
    # after every email in the batch had already been sent, so it turned an already
    # fully delivered batch into a reported EmailDeliveryError and lost `failures`.
    gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")
    emails = [
        OutgoingEmail(to="alice@example.com", subject="Welcome", body="Hello Alice"),
        OutgoingEmail(to="bob@example.com", subject="Welcome", body="Hello Bob"),
    ]
    _make_quit_misbehave(monkeypatch)

    failures = gateway.send_bulk(emails)

    assert failures == []
    assert [m["To"] for m in smtpd.messages] == ["alice@example.com", "bob@example.com"]


def test_given_relay_misbehaves_on_quit_when_send_should_still_report_success(smtpd, monkeypatch):
    gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")
    _make_quit_misbehave(monkeypatch)

    gateway.send(to="alice@example.com", subject="Welcome", body="Hello Alice")  # must not raise

    assert len(smtpd.messages) == 1


def test_given_relay_misbehaves_on_quit_when_send_bulk_should_log_a_warning_not_swallow_silently(
    smtpd, monkeypatch, caplog
):
    gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")
    _make_quit_misbehave(monkeypatch)

    with caplog.at_level(logging.WARNING):
        gateway.send_bulk([OutgoingEmail(to="alice@example.com", subject="Welcome", body="Hello Alice")])

    assert "Failed to cleanly close" in caplog.text
