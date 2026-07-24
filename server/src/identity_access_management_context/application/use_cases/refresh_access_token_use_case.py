from datetime import timedelta

from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.application.gateways import (
    REVOCATION_REASON_REFRESH_TOKEN_ROTATED,
    AuthSessionRepository,
    RevokedTokenRepository,
    TokenGateway,
    UserRepository,
)
from identity_access_management_context.application.responses import (
    RefreshAccessTokenResponse,
)
from identity_access_management_context.domain.exceptions import (
    InvalidRefreshTokenException,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class RefreshAccessTokenUseCase(TracedUseCase):
    def __init__(
        self,
        token_gateway: TokenGateway,
        user_repository: UserRepository,
        auth_session_repository: AuthSessionRepository,
        revoked_token_repository: RevokedTokenRepository,
        time_provider: TimeGateway,
        session_max_lifetime_seconds: int,
    ):
        self.token_gateway = token_gateway
        self.user_repository = user_repository
        self.auth_session_repository = auth_session_repository
        self.revoked_token_repository = revoked_token_repository
        self.time_provider = time_provider
        self.session_max_lifetime_seconds = session_max_lifetime_seconds

    def execute(self, command: RefreshAccessTokenCommand) -> RefreshAccessTokenResponse:
        token_data = self.token_gateway.validate_refresh_token(command.refresh_token)

        if token_data is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        user = self.user_repository.get_by_id(token_data.user_id)
        if user is None:
            raise InvalidRefreshTokenException("User no longer exists")

        if token_data.jti is None or token_data.issued_at is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        now = self.time_provider.get_current_time()
        self.revoked_token_repository.purge_expired(now)
        refresh_ttl = timedelta(seconds=self.token_gateway.get_refresh_token_expiration_seconds())
        self.auth_session_repository.purge_dead(now - refresh_ttl)

        revocation = self.revoked_token_repository.get_active_revocation(token_data.jti, now)
        if revocation is not None:
            if revocation.reason == REVOCATION_REASON_REFRESH_TOKEN_ROTATED:
                # Replaying an already-rotated refresh token is strong evidence of
                # theft (RFC 9700 §4.14.2): kill every session of the user so the
                # thief's rotated-forward chain dies too. Other reasons (logout)
                # are benign in-flight replays and must not escalate.
                # The cutoff is deliberately NOT truncated to the second (unlike
                # the password-update flow): JWT iat has second precision, so a
                # truncated cutoff would let the thief's same-second access token
                # satisfy `iat < cutoff` and survive.
                self.auth_session_repository.invalidate_all_for_user(token_data.user_id, now)
                user.session_invalid_before = now
                self.user_repository.update(user)
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        if user.session_invalid_before is not None:
            session_cutoff = user.session_invalid_before
            if token_data.issued_at < session_cutoff:
                raise InvalidRefreshTokenException("Invalid or expired refresh token")

        session = self.auth_session_repository.get_active_by_user_id_and_refresh_jti(
            user_id=token_data.user_id,
            refresh_token_jti=token_data.jti,
        )
        if session is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        # Absolute session lifetime: rotation makes the refresh window sliding,
        # so without this cap an active session (or a stolen, undetected refresh
        # chain) could self-renew forever. Past the cap, force a re-login.
        if now - session.created_at >= timedelta(seconds=self.session_max_lifetime_seconds):
            self.auth_session_repository.invalidate_by_user_id_and_refresh_jti(
                user_id=token_data.user_id,
                refresh_token_jti=token_data.jti,
                invalidated_at=now,
            )
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        new_access_token = self.token_gateway.generate_token(
            user_id=token_data.user_id,
            email=token_data.email,
            roles=user.roles,
        )
        new_refresh_token = self.token_gateway.generate_refresh_token(
            user_id=token_data.user_id,
            email=token_data.email,
            roles=user.roles,
        )
        if new_refresh_token.jti is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        # Rotate before revoking: if we crash between the two commits, the old
        # token is unusable anyway (the session moved on, the lookup above fails)
        # and the client's retry hits a plain rejection instead of being
        # mistaken for token theft. The compare-and-swap loses against a
        # concurrent rotation of the same token — reject without revoking, the
        # winner already did.
        rotated = self.auth_session_repository.rotate_refresh_token_jti(
            session_id=session.id,
            expected_refresh_token_jti=token_data.jti,
            new_refresh_token_jti=new_refresh_token.jti,
            rotated_at=now,
        )
        if not rotated:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        self.revoked_token_repository.revoke(token_data, REVOCATION_REASON_REFRESH_TOKEN_ROTATED, now)

        return RefreshAccessTokenResponse(
            access_token=new_access_token.value,
            refresh_token=new_refresh_token.value,
            user_id=token_data.user_id,
        )
