# notification_context: group-owner-promotion email — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a new `notification_context` bounded context whose first (and only, for this slice) job is reacting to `OwnerAddedToGroupEvent` and sending the promoted user a plain-text "you're now an owner" email.

**Architecture:** IAM exposes group-ownership facts through a new primary private-API adapter (`GroupOwnershipInfoApi`, session-per-call, buildable once at startup). `notification_context` wraps that API behind its own gateway (`PrivateApiGroupOwnershipGateway`), runs a use case (`NotifyGroupOwnerPromotedUseCase`) that composes and sends the email via the existing `EmailGateway`, and is triggered by a primary adapter (`GroupOwnerPromotedEventSubscriber`) subscribed once in `main.py`'s lifespan to `DomainEventPublisher`. `AddOwnerToGroupUseCase` and `OwnerAddedToGroupEvent` are untouched — this is a second subscriber on an event that already fires.

**Tech Stack:** Python 3.13, FastAPI, SQLModel, `uv`, pytest, `pytest-smtpdfix` (already a dev dependency, used by `tests/shared_kernel/integration/test_smtp_email_gateway.py`).

**Spec:** `docs/superpowers/specs/2026-09-24-notification-context-owner-promoted-design.md`

## Global Constraints

- All backend commands run from `server/`. Run `uv run ruff format . && uv run ruff check .` before every commit — CI checks both, ruff is configured with `select = ["E","F","I","B","S"]`, `line-length = 120` (server/pyproject.toml).
- Test naming: `test_given_<state>_when_<action>_should_<outcome>` for every new test (project convention — see `feedback_test_naming` memory; this is the dominant style in the current suite, e.g. 307 of 424 `test_given_*` functions already use `_should_`).
- Dependency rule is strict: `domain` imports nothing external; `application` imports only `domain`; `adapters` implement Protocols from `application`. Use cases never import from `adapters/`. `notification_context` must never import IAM internals directly, with one unavoidable exception: a primary event-subscriber adapter names the concrete event type it subscribes to (`identity_access_management_context.domain.events.OwnerAddedToGroupEvent`) directly — you cannot `subscribe()` to a type without importing it. Everything else about IAM's group-ownership data flows only through `identity_access_management_context.adapters.primary.private_api`.
- Gateway methods express business intent (`get_owner_promotion_details`, `get_owner_info`), not CRUD.
- No `Any`, no `Optional[X]` — use `X | None`.
- Imports: stdlib / third-party / local groups, alphabetically sorted within each group (ruff `I` rule enforces this — if `ruff check` reports import-order failures after a step, run `uv run ruff check --fix .` and re-verify).
- No comments except non-obvious WHY (a hidden constraint, an invariant, a workaround). Never explain WHAT the code does.
- Every commit leaves `uv run pytest tests/ -q` green (run from `server/`). Conventional Commits (`feat(notification): ...`, `feat(iam): ...`). No `--no-verify`. Create new commits, never amend.
- New tests do not use a mocking library or `assert_called_with` — this codebase's Fakes are plain in-memory stores (dict/list) with test-only seeding helpers (e.g. `set_owner_promotion_details`, `fail_next_send`), asserted on directly.

---

## Task 1: `notification_context` — `NotifyGroupOwnerPromotedUseCase` (domain + application, TDD)

**Files:**
- Create: `server/src/notification_context/domain/value_objects/owner_promotion_notification.py`
- Create: `server/src/notification_context/domain/value_objects/__init__.py`
- Create: `server/src/notification_context/application/commands/notify_group_owner_promoted_command.py`
- Create: `server/src/notification_context/application/commands/__init__.py`
- Create: `server/src/notification_context/application/gateways/group_ownership_gateway.py`
- Create: `server/src/notification_context/application/gateways/__init__.py`
- Create: `server/src/notification_context/application/use_cases/notify_group_owner_promoted_use_case.py`
- Create: `server/src/notification_context/application/use_cases/__init__.py`
- Create: `server/tests/notification_context/__init__.py` (empty)
- Create: `server/tests/notification_context/unit/__init__.py` (empty)
- Create: `server/tests/notification_context/unit/use_cases/__init__.py` (empty)
- Create: `server/tests/notification_context/unit/fakes/__init__.py`
- Create: `server/tests/notification_context/unit/fakes/fake_group_ownership_gateway.py`
- Create: `server/tests/shared_kernel/fakes/fake_email_gateway.py`
- Modify: `server/tests/shared_kernel/fakes/__init__.py`
- Create: `server/tests/notification_context/unit/conftest.py`
- Create: `server/tests/notification_context/unit/use_cases/test_notify_group_owner_promoted_use_case.py`

**Interfaces:**
- Produces: `OwnerPromotionNotification(email: str, display_name: str, group_name: str)` (`notification_context.domain.value_objects`)
- Produces: `NotifyGroupOwnerPromotedCommand(group_id: UUID, user_id: UUID, added_by_user_id: UUID)` (`notification_context.application.commands`)
- Produces: `GroupOwnershipGateway.get_owner_promotion_details(self, user_id: UUID, group_id: UUID) -> OwnerPromotionNotification | None` (`notification_context.application.gateways`) — Task 3's `PrivateApiGroupOwnershipGateway` implements this.
- Produces: `NotifyGroupOwnerPromotedUseCase(group_ownership_gateway: GroupOwnershipGateway, email_gateway: EmailGateway).execute(command: NotifyGroupOwnerPromotedCommand) -> None` (`notification_context.application.use_cases`) — Task 3's `GroupOwnerPromotedEventSubscriber` calls this.
- Produces: `FakeEmailGateway` (`tests.shared_kernel.fakes`) — general-purpose fake for the shared-kernel `EmailGateway` Protocol; the first consumer, but placed in `tests/shared_kernel/fakes/` (not `tests/notification_context/`) because `EmailGateway` itself lives in `shared_kernel`, matching how `FakeTimeGateway` sits alongside `TimeGateway`. Future email consumers (2FA, invites) reuse it from there.
- Consumes: `EmailGateway.send(self, to: str, subject: str, body: str) -> None` and `EmailDeliveryError(reason: str)` (both already exist in `shared_kernel`, unchanged).

- [ ] **Step 1: Create the value object**

`server/src/notification_context/domain/value_objects/owner_promotion_notification.py`:
```python
from dataclasses import dataclass


@dataclass
class OwnerPromotionNotification:
    email: str
    display_name: str
    group_name: str
```

`server/src/notification_context/domain/value_objects/__init__.py`:
```python
from .owner_promotion_notification import OwnerPromotionNotification

__all__ = ["OwnerPromotionNotification"]
```

- [ ] **Step 2: Create the command**

`server/src/notification_context/application/commands/notify_group_owner_promoted_command.py`:
```python
from dataclasses import dataclass
from uuid import UUID


@dataclass
class NotifyGroupOwnerPromotedCommand:
    group_id: UUID
    user_id: UUID
    added_by_user_id: UUID
```

`server/src/notification_context/application/commands/__init__.py`:
```python
from .notify_group_owner_promoted_command import NotifyGroupOwnerPromotedCommand

__all__ = ["NotifyGroupOwnerPromotedCommand"]
```

- [ ] **Step 3: Declare the gateway Protocol**

`server/src/notification_context/application/gateways/group_ownership_gateway.py`:
```python
from typing import Protocol
from uuid import UUID

from notification_context.domain.value_objects import OwnerPromotionNotification


class GroupOwnershipGateway(Protocol):
    def get_owner_promotion_details(self, user_id: UUID, group_id: UUID) -> OwnerPromotionNotification | None: ...
```

`server/src/notification_context/application/gateways/__init__.py`:
```python
from .group_ownership_gateway import GroupOwnershipGateway

__all__ = ["GroupOwnershipGateway"]
```

- [ ] **Step 4: Write the Fakes**

`server/tests/notification_context/unit/fakes/fake_group_ownership_gateway.py`:
```python
from uuid import UUID

from notification_context.domain.value_objects import OwnerPromotionNotification


class FakeGroupOwnershipGateway:
    def __init__(self):
        self._details: dict[tuple[UUID, UUID], OwnerPromotionNotification] = {}

    def set_owner_promotion_details(self, user_id: UUID, group_id: UUID, details: OwnerPromotionNotification) -> None:
        self._details[(user_id, group_id)] = details

    def get_owner_promotion_details(self, user_id: UUID, group_id: UUID) -> OwnerPromotionNotification | None:
        return self._details.get((user_id, group_id))
```

`server/tests/notification_context/unit/fakes/__init__.py`:
```python
from .fake_group_ownership_gateway import FakeGroupOwnershipGateway

__all__ = ["FakeGroupOwnershipGateway"]
```

`server/tests/shared_kernel/fakes/fake_email_gateway.py`:
```python
from shared_kernel.domain.exceptions import EmailDeliveryError


class FakeEmailGateway:
    def __init__(self):
        self.sent_emails: list[dict[str, str]] = []
        self._should_fail = False

    def send(self, to: str, subject: str, body: str) -> None:
        if self._should_fail:
            raise EmailDeliveryError("simulated SMTP failure")
        self.sent_emails.append({"to": to, "subject": subject, "body": body})

    def fail_next_send(self) -> None:
        self._should_fail = True
```

Modify `server/tests/shared_kernel/fakes/__init__.py` — current contents are:
```python
from .fake_event_publisher import FakeEventPublisher
from .fake_time_gateway import FakeTimeGateway

__all__ = ["FakeEventPublisher", "FakeTimeGateway"]
```
Replace with:
```python
from .fake_email_gateway import FakeEmailGateway
from .fake_event_publisher import FakeEventPublisher
from .fake_time_gateway import FakeTimeGateway

__all__ = ["FakeEmailGateway", "FakeEventPublisher", "FakeTimeGateway"]
```

- [ ] **Step 5: Create test package scaffolding and conftest**

Create empty files: `server/tests/notification_context/__init__.py`, `server/tests/notification_context/unit/__init__.py`, `server/tests/notification_context/unit/use_cases/__init__.py`.

`server/tests/notification_context/unit/conftest.py`:
```python
import pytest

from tests.shared_kernel.fakes import FakeEmailGateway

from .fakes import FakeGroupOwnershipGateway


@pytest.fixture
def group_ownership_gateway():
    return FakeGroupOwnershipGateway()


@pytest.fixture
def email_gateway():
    return FakeEmailGateway()
```

- [ ] **Step 6: Write the first failing test — happy path**

`server/tests/notification_context/unit/use_cases/test_notify_group_owner_promoted_use_case.py`:
```python
from uuid import UUID

import pytest

from notification_context.application.commands import NotifyGroupOwnerPromotedCommand
from notification_context.application.use_cases import NotifyGroupOwnerPromotedUseCase
from notification_context.domain.value_objects import OwnerPromotionNotification


def test_given_promoted_user_when_notifying_should_send_email_to_new_owner(
    group_ownership_gateway,
    email_gateway,
):
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    added_by_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    group_ownership_gateway.set_owner_promotion_details(
        user_id,
        group_id,
        OwnerPromotionNotification(email="alice@example.com", display_name="Alice", group_name="Development Team"),
    )
    use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    command = NotifyGroupOwnerPromotedCommand(group_id=group_id, user_id=user_id, added_by_user_id=added_by_user_id)

    use_case.execute(command)

    assert len(email_gateway.sent_emails) == 1
    sent = email_gateway.sent_emails[0]
    assert sent["to"] == "alice@example.com"
    assert sent["subject"] == 'You\'re now an owner of "Development Team"'
    assert sent["body"] == 'Hi Alice, you\'ve been made an owner of the group "Development Team".'
```

- [ ] **Step 7: Run it, watch it fail**

Run: `cd server && uv run pytest tests/notification_context/unit/use_cases/test_notify_group_owner_promoted_use_case.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'notification_context.application.use_cases'` (the use case doesn't exist yet).

- [ ] **Step 8: Implement the minimal use case to go green**

`server/src/notification_context/application/use_cases/notify_group_owner_promoted_use_case.py`:
```python
import logging

from notification_context.application.commands import NotifyGroupOwnerPromotedCommand
from notification_context.application.gateways import GroupOwnershipGateway
from shared_kernel.application.gateways import EmailGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)


class NotifyGroupOwnerPromotedUseCase(TracedUseCase):
    def __init__(self, group_ownership_gateway: GroupOwnershipGateway, email_gateway: EmailGateway):
        self._group_ownership_gateway = group_ownership_gateway
        self._email_gateway = email_gateway

    def execute(self, command: NotifyGroupOwnerPromotedCommand) -> None:
        details = self._group_ownership_gateway.get_owner_promotion_details(command.user_id, command.group_id)
        if details is None:
            logger.warning(
                "No owner-promotion details found for user=%s group=%s; skipping notification email",
                command.user_id,
                command.group_id,
            )
            return

        subject = f'You\'re now an owner of "{details.group_name}"'
        body = f'Hi {details.display_name}, you\'ve been made an owner of the group "{details.group_name}".'

        try:
            self._email_gateway.send(to=details.email, subject=subject, body=body)
        except EmailDeliveryError:
            logger.error(
                "Failed to send owner-promotion email to %s for group %s",
                details.email,
                details.group_name,
                exc_info=True,
            )
```

`server/src/notification_context/application/use_cases/__init__.py`:
```python
from .notify_group_owner_promoted_use_case import NotifyGroupOwnerPromotedUseCase

__all__ = ["NotifyGroupOwnerPromotedUseCase"]
```

- [ ] **Step 9: Run test, verify it passes**

Run: `cd server && uv run pytest tests/notification_context/unit/use_cases/test_notify_group_owner_promoted_use_case.py -v`
Expected: PASS (1 passed).

- [ ] **Step 10: Add the second test — gateway returns `None`**

Append to `server/tests/notification_context/unit/use_cases/test_notify_group_owner_promoted_use_case.py`:
```python


def test_given_gateway_returns_no_details_when_notifying_should_not_send_email(
    group_ownership_gateway,
    email_gateway,
):
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    added_by_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    command = NotifyGroupOwnerPromotedCommand(group_id=group_id, user_id=user_id, added_by_user_id=added_by_user_id)

    use_case.execute(command)

    assert email_gateway.sent_emails == []
```

Run: `cd server && uv run pytest tests/notification_context/unit/use_cases/test_notify_group_owner_promoted_use_case.py -v`
Expected: PASS (2 passed) — the `None`-guard was already written in Step 8, this test just proves it.

- [ ] **Step 11: Add the third test — `EmailDeliveryError` is swallowed and logged**

Append to the same test file (no new imports needed — `caplog` is an injected pytest fixture):
```python


def test_given_email_delivery_fails_when_notifying_should_swallow_error_and_log(
    group_ownership_gateway,
    email_gateway,
    caplog: pytest.LogCaptureFixture,
):
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    added_by_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    group_ownership_gateway.set_owner_promotion_details(
        user_id,
        group_id,
        OwnerPromotionNotification(email="alice@example.com", display_name="Alice", group_name="Development Team"),
    )
    email_gateway.fail_next_send()
    use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    command = NotifyGroupOwnerPromotedCommand(group_id=group_id, user_id=user_id, added_by_user_id=added_by_user_id)

    with caplog.at_level("ERROR", logger="notification_context.application.use_cases.notify_group_owner_promoted_use_case"):
        use_case.execute(command)  # must not raise

    errors = [rec for rec in caplog.records if rec.levelname == "ERROR" and "alice@example.com" in rec.getMessage()]
    assert errors, "EmailDeliveryError must be logged at ERROR so operators can see the delivery failure"
    assert errors[0].exc_info is not None
```

Run: `cd server && uv run pytest tests/notification_context/unit/use_cases/test_notify_group_owner_promoted_use_case.py -v`
Expected: PASS (3 passed) — the `except EmailDeliveryError` branch was already written in Step 8, this test proves it swallows and logs.

- [ ] **Step 12: Format, lint, full-suite check**

Run: `cd server && uv run ruff format . && uv run ruff check .`
Expected: no changes needed / no errors. Fix any import-order or line-length issues reported.

Run: `cd server && uv run pytest tests/ -q`
Expected: all pass (this task only adds new files, nothing existing changes behavior).

- [ ] **Step 13: Commit**

```bash
cd server
git add src/notification_context tests/notification_context tests/shared_kernel/fakes
git commit -m "feat(notification): add NotifyGroupOwnerPromotedUseCase with fakes"
```

---

## Task 2: IAM — `GroupOwnershipInfoApi` private API (TDD, integration tier)

**Files:**
- Create: `server/src/identity_access_management_context/adapters/primary/private_api/group_ownership_info.py`
- Modify: `server/src/identity_access_management_context/adapters/primary/private_api/__init__.py`
- Create: `server/tests/identity_access_management_context/integration/test_group_ownership_info_api.py`

**Interfaces:**
- Consumes: `GetUserUseCase(user_repository).execute(GetUserCommand(user_id=...)) -> User` raising `UserNotFoundError` (alias of `UserNotFoundException`); `GetGroupUseCase(group_repository, group_member_repository).execute(GetGroupCommand(group_id=...)) -> GetGroupResponse` (`.group: Group`) raising `GroupNotFoundException`; `SqlUserRepository(session)`, `SqlGroupRepository(session)`, `SqlGroupMemberRepository(session)` — all pre-existing, unchanged.
- Produces: `GroupOwnerInfo(email: str, display_name: str, group_name: str)` and `GroupOwnershipInfoApi(session_maker: Callable[[], Session]).get_owner_info(self, user_id: UUID, group_id: UUID) -> GroupOwnerInfo | None` (`identity_access_management_context.adapters.primary.private_api`) — Task 3's `PrivateApiGroupOwnershipGateway` wraps this.

- [ ] **Step 1: Write the failing integration test**

`server/tests/identity_access_management_context/integration/test_group_ownership_info_api.py`:
```python
from uuid import uuid4

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from identity_access_management_context.adapters.primary.private_api import (
    GroupOwnershipInfoApi,
)
from identity_access_management_context.domain.entities import Group, User


def _build_api(database_engine) -> GroupOwnershipInfoApi:
    session_factory = sessionmaker(bind=database_engine, class_=Session, expire_on_commit=False)
    return GroupOwnershipInfoApi(session_maker=session_factory)


def test_given_existing_user_and_group_when_getting_owner_info_should_return_details(
    database_engine, sql_user_repository, sql_group_repository
):
    user_id = uuid4()
    group_id = uuid4()
    sql_user_repository.save(User(id=user_id, username="alice", email="alice@example.com", name="Alice"))
    sql_group_repository.save_group(Group(id=group_id, name="Development Team", is_personal=False))

    api = _build_api(database_engine)
    info = api.get_owner_info(user_id, group_id)

    assert info is not None
    assert info.email == "alice@example.com"
    assert info.display_name == "Alice"
    assert info.group_name == "Development Team"


def test_given_nonexistent_user_when_getting_owner_info_should_return_none(database_engine, sql_group_repository):
    group_id = uuid4()
    sql_group_repository.save_group(Group(id=group_id, name="Development Team", is_personal=False))

    api = _build_api(database_engine)
    info = api.get_owner_info(uuid4(), group_id)

    assert info is None


def test_given_nonexistent_group_when_getting_owner_info_should_return_none(database_engine, sql_user_repository):
    user_id = uuid4()
    sql_user_repository.save(User(id=user_id, username="alice", email="alice@example.com", name="Alice"))

    api = _build_api(database_engine)
    info = api.get_owner_info(user_id, uuid4())

    assert info is None
```

This reuses the `database_engine`, `sql_user_repository`, and `sql_group_repository` fixtures already defined in `server/tests/identity_access_management_context/integration/conftest.py` — no conftest changes needed. `database_engine` is a `sqlite:///:memory:` engine; SQLAlchemy's default pooling for in-memory SQLite keeps one connection alive per thread, so a second `sessionmaker` bound to the same `database_engine` sees data committed through the `session` fixture's repositories.

- [ ] **Step 2: Run it, watch it fail**

Run: `cd server && uv run pytest tests/identity_access_management_context/integration/test_group_ownership_info_api.py -v`
Expected: FAIL — `ImportError: cannot import name 'GroupOwnershipInfoApi'`.

- [ ] **Step 3: Implement `GroupOwnershipInfoApi`**

`server/src/identity_access_management_context/adapters/primary/private_api/group_ownership_info.py`:
```python
from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from sqlmodel import Session

from identity_access_management_context.adapters.secondary.sql import (
    SqlGroupMemberRepository,
    SqlGroupRepository,
    SqlUserRepository,
)
from identity_access_management_context.application.commands import (
    GetGroupCommand,
    GetUserCommand,
)
from identity_access_management_context.application.use_cases import (
    GetGroupUseCase,
    GetUserUseCase,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotFoundError,
)


@dataclass
class GroupOwnerInfo:
    email: str
    display_name: str
    group_name: str


class GroupOwnershipInfoApi:
    """Private API for other bounded contexts to query group ownership details.

    Unlike UserInfoApi, this manages its own DB session per call via a session_maker
    given at construction, so it can be built once at startup for a non-request-scoped
    caller (an event subscriber) instead of wired per-request through FastAPI Depends.
    """

    def __init__(self, session_maker: Callable[[], Session]):
        self._session_maker = session_maker

    def get_owner_info(self, user_id: UUID, group_id: UUID) -> GroupOwnerInfo | None:
        with self._session_maker() as session:
            try:
                user = GetUserUseCase(SqlUserRepository(session)).execute(GetUserCommand(user_id=user_id))
                group_response = GetGroupUseCase(
                    SqlGroupRepository(session), SqlGroupMemberRepository(session)
                ).execute(GetGroupCommand(group_id=group_id))
            except (UserNotFoundError, GroupNotFoundException):
                return None
            return GroupOwnerInfo(email=user.email, display_name=user.name, group_name=group_response.group.name)
```

Modify `server/src/identity_access_management_context/adapters/primary/private_api/__init__.py` — current contents are:
```python
from .user_info import UserInfoApi

__all__ = ["UserInfoApi"]
```
Replace with:
```python
from .group_ownership_info import GroupOwnerInfo, GroupOwnershipInfoApi
from .user_info import UserInfoApi

__all__ = ["GroupOwnerInfo", "GroupOwnershipInfoApi", "UserInfoApi"]
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `cd server && uv run pytest tests/identity_access_management_context/integration/test_group_ownership_info_api.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Format, lint, full-suite check**

Run: `cd server && uv run ruff format . && uv run ruff check .`
Run: `cd server && uv run pytest tests/ -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
cd server
git add src/identity_access_management_context/adapters/primary/private_api tests/identity_access_management_context/integration/test_group_ownership_info_api.py
git commit -m "feat(iam): add GroupOwnershipInfoApi private API for group-ownership queries"
```

---

## Task 3: `notification_context` adapters — gateway wrapper + event subscriber (TDD, integration tier)

**Files:**
- Create: `server/src/notification_context/adapters/secondary/private_api/private_api_group_ownership_gateway.py`
- Create: `server/src/notification_context/adapters/secondary/private_api/__init__.py`
- Create: `server/src/notification_context/adapters/secondary/__init__.py`
- Create: `server/src/notification_context/adapters/primary/events/group_owner_promoted_event_subscriber.py`
- Create: `server/src/notification_context/adapters/primary/events/__init__.py`
- Create: `server/tests/notification_context/integration/__init__.py` (empty)
- Create: `server/tests/notification_context/integration/conftest.py`
- Create: `server/tests/notification_context/integration/test_group_owner_promoted_event_subscriber.py`

**Interfaces:**
- Consumes: `GroupOwnershipInfoApi.get_owner_info(user_id, group_id) -> GroupOwnerInfo | None` (Task 2); `GroupOwnershipGateway`, `NotifyGroupOwnerPromotedUseCase`, `OwnerPromotionNotification` (Task 1); `OwnerAddedToGroupEvent(group_id, user_id, added_by_user_id, event_id=None, occurred_on=None)` (`identity_access_management_context.domain.events`, pre-existing, unchanged).
- Produces: `PrivateApiGroupOwnershipGateway(group_ownership_info_api: GroupOwnershipInfoApi)` implementing `GroupOwnershipGateway` (`notification_context.adapters.secondary` and `notification_context.adapters.secondary.private_api`).
- Produces: `GroupOwnerPromotedEventSubscriber(notify_use_case: NotifyGroupOwnerPromotedUseCase).handle(self, event: OwnerAddedToGroupEvent) -> None` (`notification_context.adapters.primary.events`) — Task 4 subscribes this to `OwnerAddedToGroupEvent` in `main.py`.

- [ ] **Step 1: Write the failing integration test**

`server/tests/notification_context/integration/conftest.py`:
```python
import pytest
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture(scope="function")
def database_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def session(database_engine):
    with Session(database_engine) as session:
        yield session


@pytest.fixture(scope="function")
def session_maker(database_engine):
    return sessionmaker(bind=database_engine, class_=Session, expire_on_commit=False)
```

`server/tests/notification_context/integration/test_group_owner_promoted_event_subscriber.py`:
```python
from uuid import uuid4

from identity_access_management_context.adapters.primary.private_api import (
    GroupOwnershipInfoApi,
)
from identity_access_management_context.adapters.secondary.sql import (
    SqlGroupRepository,
    SqlUserRepository,
)
from identity_access_management_context.domain.entities import Group, User
from identity_access_management_context.domain.events import OwnerAddedToGroupEvent
from notification_context.adapters.primary.events import GroupOwnerPromotedEventSubscriber
from notification_context.adapters.secondary.private_api import (
    PrivateApiGroupOwnershipGateway,
)
from notification_context.application.use_cases import NotifyGroupOwnerPromotedUseCase
from shared_kernel.adapters.secondary import SmtpEmailGateway


def test_given_promotion_event_when_handled_should_send_owner_promotion_email_end_to_end(
    session, session_maker, smtpd
):
    user_id = uuid4()
    group_id = uuid4()
    added_by_user_id = uuid4()
    SqlUserRepository(session).save(User(id=user_id, username="alice", email="alice@example.com", name="Alice"))
    SqlGroupRepository(session).save_group(Group(id=group_id, name="Development Team", is_personal=False))

    group_ownership_info_api = GroupOwnershipInfoApi(session_maker=session_maker)
    group_ownership_gateway = PrivateApiGroupOwnershipGateway(group_ownership_info_api)
    email_gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")
    notify_use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    subscriber = GroupOwnerPromotedEventSubscriber(notify_use_case)

    event = OwnerAddedToGroupEvent(group_id=group_id, user_id=user_id, added_by_user_id=added_by_user_id)
    subscriber.handle(event)

    assert len(smtpd.messages) == 1
    message = smtpd.messages[0]
    assert message["To"] == "alice@example.com"
    assert message["Subject"] == 'You\'re now an owner of "Development Team"'
    assert "Alice" in message.get_payload()
    assert "Development Team" in message.get_payload()
```

`smtpd` is the `pytest-smtpdfix` fixture, already used the same way (no extra setup) in `tests/shared_kernel/integration/test_smtp_email_gateway.py`.

Create empty `server/tests/notification_context/integration/__init__.py`.

- [ ] **Step 2: Run it, watch it fail**

Run: `cd server && uv run pytest tests/notification_context/integration/test_group_owner_promoted_event_subscriber.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'notification_context.adapters.primary.events'`.

- [ ] **Step 3: Implement the secondary gateway wrapper**

`server/src/notification_context/adapters/secondary/private_api/private_api_group_ownership_gateway.py`:
```python
from uuid import UUID

from identity_access_management_context.adapters.primary.private_api import (
    GroupOwnershipInfoApi,
)
from notification_context.application.gateways import GroupOwnershipGateway
from notification_context.domain.value_objects import OwnerPromotionNotification


class PrivateApiGroupOwnershipGateway(GroupOwnershipGateway):
    """Gateway that wraps IAM's GroupOwnershipInfoApi for the notification context."""

    def __init__(self, group_ownership_info_api: GroupOwnershipInfoApi):
        self._group_ownership_info_api = group_ownership_info_api

    def get_owner_promotion_details(self, user_id: UUID, group_id: UUID) -> OwnerPromotionNotification | None:
        info = self._group_ownership_info_api.get_owner_info(user_id, group_id)
        if info is None:
            return None
        return OwnerPromotionNotification(
            email=info.email, display_name=info.display_name, group_name=info.group_name
        )
```

`server/src/notification_context/adapters/secondary/private_api/__init__.py`:
```python
from .private_api_group_ownership_gateway import PrivateApiGroupOwnershipGateway

__all__ = ["PrivateApiGroupOwnershipGateway"]
```

`server/src/notification_context/adapters/secondary/__init__.py`:
```python
from .private_api.private_api_group_ownership_gateway import (
    PrivateApiGroupOwnershipGateway,
)

__all__ = ["PrivateApiGroupOwnershipGateway"]
```
(This top-level re-export mirrors `password_management_context/adapters/secondary/__init__.py` and `vault_management_context/adapters/secondary/__init__.py` — `main.py` imports secondary adapters from the context's `adapters.secondary` package, not the nested subpackage.)

- [ ] **Step 4: Implement the event subscriber**

`server/src/notification_context/adapters/primary/events/group_owner_promoted_event_subscriber.py`:
```python
from identity_access_management_context.domain.events import OwnerAddedToGroupEvent
from notification_context.application.commands import NotifyGroupOwnerPromotedCommand
from notification_context.application.use_cases import NotifyGroupOwnerPromotedUseCase


class GroupOwnerPromotedEventSubscriber:
    """Primary adapter subscribing to OwnerAddedToGroupEvent to trigger the owner-promotion email."""

    def __init__(self, notify_use_case: NotifyGroupOwnerPromotedUseCase):
        self._notify_use_case = notify_use_case

    def handle(self, event: OwnerAddedToGroupEvent) -> None:
        command = NotifyGroupOwnerPromotedCommand(
            group_id=event.group_id,
            user_id=event.user_id,
            added_by_user_id=event.added_by_user_id,
        )
        self._notify_use_case.execute(command)
```

`server/src/notification_context/adapters/primary/events/__init__.py`:
```python
from .group_owner_promoted_event_subscriber import GroupOwnerPromotedEventSubscriber

__all__ = ["GroupOwnerPromotedEventSubscriber"]
```

- [ ] **Step 5: Run test, verify it passes**

Run: `cd server && uv run pytest tests/notification_context/integration/test_group_owner_promoted_event_subscriber.py -v`
Expected: PASS (1 passed).

- [ ] **Step 6: Format, lint, full-suite check**

Run: `cd server && uv run ruff format . && uv run ruff check .`
Run: `cd server && uv run pytest tests/ -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
cd server
git add src/notification_context/adapters tests/notification_context/integration
git commit -m "feat(notification): wire group-ownership gateway and event subscriber adapters"
```

---

## Task 4: Wire the subscriber in `main.py`; verify end-to-end

**Files:**
- Modify: `server/src/main.py`
- Modify: `server/tests/e2e/test_complete_groups_workflow.py`

**Interfaces:**
- Consumes: everything produced in Tasks 1-3 — `GroupOwnershipInfoApi`, `PrivateApiGroupOwnershipGateway`, `NotifyGroupOwnerPromotedUseCase`, `GroupOwnerPromotedEventSubscriber`, `OwnerAddedToGroupEvent`; and the pre-existing `domain_event_publisher.subscribe(event_type, handler)`, `SessionLocal` (the `sessionmaker` built at `main.py:150`), `email_gateway` (built at `main.py:208-216`).

- [ ] **Step 1: Add imports to `main.py`**

In `server/src/main.py`, the import block currently reads (lines 50-63):
```python
from identity_access_management_context.adapters.primary.fastapi.routes import (
    get_admin_management_router,
    get_authentication_router,
    get_group_management_router,
    get_user_management_router,
)
from identity_access_management_context.adapters.secondary import (
    BcryptHashingGateway,
    InMemoryLoginLockoutGateway,
    JwtTokenGateway,
    OAuth2SsoGateway,
    PrivateApiSsoEncryptionGateway,
    SsoUrlValidator,
)
```
Replace with:
```python
from identity_access_management_context.adapters.primary.fastapi.routes import (
    get_admin_management_router,
    get_authentication_router,
    get_group_management_router,
    get_user_management_router,
)
from identity_access_management_context.adapters.primary.private_api import GroupOwnershipInfoApi
from identity_access_management_context.adapters.secondary import (
    BcryptHashingGateway,
    InMemoryLoginLockoutGateway,
    JwtTokenGateway,
    OAuth2SsoGateway,
    PrivateApiSsoEncryptionGateway,
    SsoUrlValidator,
)
from identity_access_management_context.domain.events import OwnerAddedToGroupEvent
```

The import block currently reads (lines 64-70):
```python
from monitoring import setup_logging, setup_monitoring
from password_management_context.adapters.primary.fastapi.routes import (
    get_password_management_router,
)
```
Replace with:
```python
from monitoring import setup_logging, setup_monitoring
from notification_context.adapters.primary.events import GroupOwnerPromotedEventSubscriber
from notification_context.adapters.secondary import PrivateApiGroupOwnershipGateway
from notification_context.application.use_cases import NotifyGroupOwnerPromotedUseCase
from password_management_context.adapters.primary.fastapi.routes import (
    get_password_management_router,
)
```

- [ ] **Step 2: Subscribe the handler in `lifespan`**

In `server/src/main.py`, the lifespan currently reads (lines 207-218):
```python
    # Email gateway (stateless)
    email_gateway = SmtpEmailGateway(
        host=get_smtp_host(),
        port=get_smtp_port(),
        from_address=get_smtp_from_address(),
        username=get_smtp_username(),
        password=get_smtp_password(),
        tls_mode=SmtpTlsMode(get_smtp_tls_mode()),
    )
    app.state.email_gateway = email_gateway

    # Rate limiter (in-memory sliding window)
```
Replace with:
```python
    # Email gateway (stateless)
    email_gateway = SmtpEmailGateway(
        host=get_smtp_host(),
        port=get_smtp_port(),
        from_address=get_smtp_from_address(),
        username=get_smtp_username(),
        password=get_smtp_password(),
        tls_mode=SmtpTlsMode(get_smtp_tls_mode()),
    )
    app.state.email_gateway = email_gateway

    # Notification: group-owner-promotion email (reactive, subscribes to OwnerAddedToGroupEvent)
    group_ownership_info_api = GroupOwnershipInfoApi(session_maker=SessionLocal)
    group_ownership_gateway = PrivateApiGroupOwnershipGateway(group_ownership_info_api)
    notify_owner_promoted_use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    owner_promoted_subscriber = GroupOwnerPromotedEventSubscriber(notify_owner_promoted_use_case)
    domain_event_publisher.subscribe(OwnerAddedToGroupEvent, owner_promoted_subscriber.handle)

    # Rate limiter (in-memory sliding window)
```

- [ ] **Step 3: Add a one-line clarifying comment to the existing E2E owner-promotion phase**

`tests/e2e/test_complete_groups_workflow.py` already has a `PHASE 6: OWNER PROMOTION` block (pre-existing, from prior group-management work) that promotes a member via `POST /api/groups/{group_id}/owners` and asserts `201` + membership in `owners`. That assertion is exactly the regression check this feature needs: once the subscriber is wired, this same HTTP call synchronously triggers `NotifyGroupOwnerPromotedUseCase`, and since CI's `SMTP_HOST` (`tests/conftest.py`) is `smtp.test.invalid` (unreachable), the send will fail and must be swallowed — a broken swallow would turn this into a 500 and fail this pre-existing phase. No new phase is needed; add one comment so a future reader knows why this assertion also covers the notification path.

In `server/tests/e2e/test_complete_groups_workflow.py`, find:
```python
    # Step 6.4: Promote owner_user to owner
    add_owner_response = authenticated_admin_client.post(
        f"/api/groups/{ownership_group_id}/owners", json={"user_id": owner_user_id}
    )
```
Replace with:
```python
    # Step 6.4: Promote owner_user to owner. This also fires a reactive, swallow-on-failure
    # owner-promotion email via OwnerAddedToGroupEvent — a broken swallow would turn this 201
    # into a 500, so this assertion doubles as that regression check.
    add_owner_response = authenticated_admin_client.post(
        f"/api/groups/{ownership_group_id}/owners", json={"user_id": owner_user_id}
    )
```

- [ ] **Step 4: Full-suite verification**

Run: `cd server && uv run ruff format . && uv run ruff check .`
Expected: no errors.

Run: `cd server && uv run pytest tests/ -q`
Expected: all pass, including `tests/e2e/test_complete_groups_workflow.py` (proves the app boots with the subscriber wired and PHASE 6 still returns 201 after a swallowed SMTP failure) and every test from Tasks 1-3.

- [ ] **Step 5: Commit**

```bash
cd server
git add src/main.py tests/e2e/test_complete_groups_workflow.py
git commit -m "feat(notification): subscribe owner-promotion email handler to OwnerAddedToGroupEvent"
```

---

## Out of scope (per design doc — do not implement here)

- Any other reactive trigger (password-changed, vault-locked opt-in, one-time-link-read).
- A notification on group *creation*.
- HTML email bodies, i18n, retry/resend logic.
- Frontend changes — this feature has no client-visible surface.
