# Design: `notification_context` — group-owner-promotion email

Date: 2026-09-24
Status: approved, ready for implementation planning
Stacks on: `feat/shared-kernel-email-gateway` (PR #399)

## Motivation

PR #399 added a generic `EmailGateway` (SMTP) to `shared_kernel` but has no
consumer yet. This slice adds the first one, and in doing so stands up the
**reactive/event-driven** notification path that the email roadmap called out
as a separate, not-yet-built architectural piece (see
`project_email_notification_roadmap` memory): a new `notification_context`
bounded context whose job is to react to domain events published by other
contexts and turn them into notifications, decoupled from the context that
raised the event.

The concrete trigger for this first slice: **when an existing group member is
promoted to owner, send them an email.** This applies uniformly to
password-login and SSO users — both are plain `User` rows with `email`
always populated locally (SSO's extra identity data lives in a separate
`SsoUser` row; `User.email` is set at first login either way), so no
branching is needed anywhere in this design.

## Scope

**In scope:**
- New `notification_context` bounded context (domain/application/adapters).
- A new IAM primary adapter exposing group-ownership info to other contexts.
- Wiring `DomainEventPublisher.subscribe()` for the first time.
- One reactive use case: compose and send the "you're now an owner" email.
- Unit, integration, and a thin E2E check.

**Explicitly out of scope (future work, not this PR):**
- Any other reactive trigger (password-changed, vault-locked opt-in,
  one-time-link-read). Those are separate slices per the roadmap and may
  need their own design pass (e.g. vault-locked is opt-in; this one is not).
- Sending a notification when a group is *created* (creator becomes owner
  automatically) — confirmed explicitly not a trigger for this feature.
- HTML email bodies, i18n, retry/resend logic.

## Architecture

### Trigger: reuse the existing event, unchanged

`AddOwnerToGroupUseCase` (`identity_access_management_context/application/use_cases/add_owner_to_group_use_case.py`)
already publishes `OwnerAddedToGroupEvent(group_id, user_id, added_by_user_id)`
exactly at ownership-transfer time — group creation never goes through this
path. **No changes to this use case, its event, or its tests.** The only new
thing is a second subscriber on the same event.

### IAM side: a new primary adapter, framed in IAM's own vocabulary

IAM must not know `notification_context` exists. It exposes a fact about
its own domain — "who owns what" — with no reference to emails or
notifications anywhere in its naming:

`identity_access_management_context/adapters/primary/private_api/group_ownership_info.py`
```python
@dataclass
class GroupOwnerInfo:
    email: str
    display_name: str
    group_name: str


class GroupOwnershipInfoApi:
    """Primary API for querying group ownership details."""

    def __init__(self, session_maker: Callable[[], Session]):
        self._session_maker = session_maker

    def get_owner_info(self, user_id: UUID, group_id: UUID) -> GroupOwnerInfo | None:
        with self._session_maker() as session:
            try:
                user = GetUserUseCase(SqlUserRepository(session)).execute(
                    GetUserCommand(user_id=user_id)
                )
                group = GetGroupUseCase(
                    SqlGroupRepository(session), SqlGroupMemberRepository(session)
                ).execute(GetGroupCommand(group_id=group_id)).group
            except (UserNotFoundError, GroupNotFoundException):
                return None
            return GroupOwnerInfo(
                email=user.email, display_name=user.name, group_name=group.name,
            )
```

This is a **standalone** adapter — it does not wrap or reuse the existing
`UserInfoApi` (which is tied to the FastAPI `Depends()` request-scoped
session lifecycle for its existing HTTP consumer in password_management_context).
`GroupOwnershipInfoApi` manages its own session per call via a
`session_maker` given at construction, which means it behaves as a stateless
singleton from the caller's point of view — buildable once at startup, no
per-event session plumbing needed.

### notification_context: its own vocabulary, pulling what it needs

```
notification_context/
├── domain/
│   └── value_objects/
│       └── owner_promotion_notification.py
│           # OwnerPromotionNotification(email, display_name, group_name) — plain dataclass, notification_context's own type
├── application/
│   ├── commands/
│   │   └── notify_group_owner_promoted_command.py
│   │       # NotifyGroupOwnerPromotedCommand(group_id, user_id, added_by_user_id)
│   ├── gateways/
│   │   └── group_ownership_gateway.py
│   │       # GroupOwnershipGateway(Protocol): get_owner_promotion_details(user_id, group_id) -> OwnerPromotionNotification | None
│   └── use_cases/
│       └── notify_group_owner_promoted_use_case.py
│           # NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
└── adapters/
    ├── primary/
    │   └── events/
    │       └── group_owner_promoted_event_subscriber.py
    │           # GroupOwnerPromotedEventSubscriber(notify_use_case).handle(event) -> builds command, calls use case
    └── secondary/
        └── private_api/
            └── private_api_group_ownership_gateway.py
                # PrivateApiGroupOwnershipGateway(group_ownership_info_api) — wraps IAM's GroupOwnershipInfoApi,
                # maps GroupOwnerInfo -> OwnerPromotionNotification (the only place either type is known to the other)
```

`notify_group_owner_promoted_use_case.py` logic:
1. Ask the gateway for `get_owner_promotion_details(command.user_id, command.group_id)`.
2. If `None` (defensive — should not normally happen since `AddOwnerToGroupUseCase`
   already validated both exist moments earlier in the same request): log and return.
3. Compose subject/body (see "Email content" below) and call
   `email_gateway.send(to=details.email, subject=..., body=...)`.
4. Catch `EmailDeliveryError`: log and swallow — this is a reactive/courtesy
   send per the established failure policy (the triggering action already
   succeeded independently; a failed notification must never surface as an
   error on the promotion request).

### Wiring (`server/src/main.py`, lifespan)

Built once, after `email_gateway` and `domain_event_publisher` already exist:
```python
group_ownership_info_api = GroupOwnershipInfoApi(session_maker=SessionLocal)
group_ownership_gateway = PrivateApiGroupOwnershipGateway(group_ownership_info_api)
notify_owner_promoted_use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
subscriber = GroupOwnerPromotedEventSubscriber(notify_owner_promoted_use_case)
domain_event_publisher.subscribe(OwnerAddedToGroupEvent, subscriber.handle)
```

This is the first real use of `DomainEventPublisher.subscribe()` (previously
defined on the Protocol and implemented by `InMemoryDomainEventPublisher`,
but never called).

## Email content

Plain text, no HTML, no i18n — kept minimal for this first case:
- Subject: `You're now an owner of "{group_name}"`
- Body: `Hi {display_name}, you've been made an owner of the group "{group_name}".`

Wording can be refined freely later; the structural decisions (plain text,
single send, no retry) are what matters here.

## Testing plan

- **Unit** — `tests/notification_context/unit/use_cases/test_notify_group_owner_promoted_use_case.py`:
  `FakeGroupOwnershipGateway` + `FakeEmailGateway` (new fakes, first consumer
  of `EmailGateway` in the whole codebase), given-when-then style. Cases:
  happy path (email sent with correct recipient/content), gateway returns
  `None` (no send, no crash), `EmailDeliveryError` raised by the fake (caught
  and swallowed, logged).
- **Integration**:
  - `tests/identity_access_management_context/integration/test_group_ownership_info_api.py` —
    `GroupOwnershipInfoApi` against real in-memory SQLite (existing pattern).
  - `tests/notification_context/integration/test_group_owner_promoted_event_subscriber.py` —
    the full chain (subscriber → use case → `PrivateApiGroupOwnershipGateway` →
    real `GroupOwnershipInfoApi` on in-memory SQLite → real `SmtpEmailGateway`
    against `smtpdfix`), proving actual wiring end to end.
- **E2E** — extend the existing group workflow file with a phase that
  promotes an existing member to owner via the HTTP route and asserts the
  promotion still succeeds (201, `is_owner=True`). Email delivery itself is
  proven at the integration tier, not asserted here — SMTP is reachable in
  CI already since it's mandatory config, but this phase doesn't depend on
  that.

## Branching

New branch stacked on the open PR, per existing project convention: base off
`feat/shared-kernel-email-gateway`, not `main`. Suggested name:
`feat/notification-context-owner-promoted`.

## Rejected alternative: enrich the event instead of pulling via private API

Considered adding `email`/`display_name`/`group_name` directly onto
`OwnerAddedToGroupEvent` to avoid the extra DB round-trip and the new IAM
adapter entirely. Rejected: it would shape IAM's event around one
downstream consumer's presentation needs (this consumer wants those three
fields; the next reactive trigger will want different ones), re-coupling
IAM to notification_context's concerns — the same coupling the private-API
design exists to avoid. The extra round-trip is negligible at this volume
and is not worth trading away that decoupling.
