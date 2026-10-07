import hashlib
from datetime import timedelta

from vault_management_context.application.use_cases import PurgeExpiredShareLinksUseCase
from vault_management_context.domain.entities import ShareLink

from ..fakes import FakeShareLinkRepository


def _link(index: int, now) -> ShareLink:
    return ShareLink.create(
        setup_id="setup-1",
        share_index=index,
        lookup_hash=hashlib.sha256(f"token-{index}".encode()).hexdigest(),
        ack_hash=hashlib.sha256(f"ack-{index}".encode()).hexdigest(),
        sealed_share=f"sealed-{index}",
        now=now,
    )


def test_given_expired_and_live_links_when_purging_should_delete_only_the_expired_ones(
    share_link_repository: FakeShareLinkRepository, time_gateway
):
    issued_at = time_gateway.get_current_time()
    share_link_repository.replace_all(
        [_link(1, issued_at - timedelta(hours=49)), _link(2, issued_at - timedelta(hours=47))]
    )

    PurgeExpiredShareLinksUseCase(share_link_repository, time_gateway).execute()

    assert [link.share_index for link in share_link_repository.stored()] == [2]
