---
mode: agent
imports:
  - default_back
---

You are helping me implement a gateway using STRICT TDD with integration tests.

## CRITICAL ARCHITECTURE RULES

### Gateway Definition (MANDATORY)
Gateways are defined as Protocols in `<context>/application/gateways/`.

**CRITICAL: Gateway methods MUST express BUSINESS INTENT, not generic CRUD operations.**

#### Anti-Pattern (NEVER DO THIS):
```python
class GroupAccessGateway(Protocol):
    def get_group(self, group_id: UUID) -> Group: ...  # ❌ TOO GENERIC
    def get_user(self, user_id: UUID) -> User: ...      # ❌ TOO GENERIC
```

#### Correct Pattern (ALWAYS DO THIS):
```python
from typing import Protocol
from uuid import UUID

class GroupAccessGateway(Protocol):
    """Gateway to verify group access for password management operations"""
    
    def is_user_owner_of_group(self, user_id: UUID, group_id: UUID) -> bool:
        """Verify if a user owns a specific group"""
        ...
    
    def is_user_member_of_group(self, user_id: UUID, group_id: UUID) -> bool:
        """Verify if a user is a member of a specific group"""
        ...
    
    def group_exists(self, group_id: UUID) -> bool:
        """Check if a group exists in the system"""
        ...
    
    def get_group_owner_users(self, group_id: UUID) -> list[UUID]:
        """Get all users who own this group"""
        ...
```

**Why Business Intent Matters:**
- ✅ `is_user_owner_of_group()` - Clear business question
- ❌ `get_group()` + check ownership - Exposes internal structure
- ✅ `group_exists()` - Specific validation need
- ❌ `get_by_id()` + check None - Generic operation hiding intent

**MANDATORY: Every gateway method MUST answer "WHY is the use case asking for this data?"**

### Repository vs Gateway (CRITICAL DISTINCTION)

#### Repositories (Persistence Layer)
**ONLY acceptable for aggregate roots that belong to the current context.**
Used when the use case needs to persist/retrieve complete domain entities.

```python
class UserRepository(Protocol):
    """Repository for User aggregate root in IAM context"""
    def save(self, user: User) -> None: ...
    def get_by_id(self, user_id: UUID) -> Optional[User]: ...
    def delete(self, user_id: UUID) -> None: ...
    def update(self, user: User) -> None: ...
```

**When to use**: Directly managing entities that are OWNED by this bounded context.

#### Gateways (Anti-Corruption Layer)
**MANDATORY for cross-context communication or specific business queries.**
Used when the use case needs to verify business rules, not manipulate entities.

```python
class GroupAccessGateway(Protocol):
    """Gateway to access group information from IAM context"""
    def is_user_owner_of_group(self, user_id: UUID, group_id: UUID) -> bool: ...
    def group_exists(self, group_id: UUID) -> bool: ...
```

**When to use**: 
- Querying another bounded context
- Business validation questions
- Avoiding tight coupling between contexts

**NEVER expose get_by_id() in a gateway if you can express the business intent more specifically.**
Implementations MUST be in `<context>/adapters/secondary/<type>`:
- **Repositories**: In `secondary/sql/`
- **In-Memory**: In `secondary/in_memory/` (for testing/prototyping)
- **Technical Gateways**: In `secondary/<type>`

### Implementation Types

#### 1. SQL Repository (Primary Pattern)
**Location**: `<context>/adapters/secondary/sql/sql_<name>_repository.py`

**MANDATORY Structure**:
```python
from typing import Optional, List
from uuid import UUID
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from .model.<entity>_model import <Entity>Table
from <context>.application.gateways import <Entity>Repository
from <context>.domain.entities import <Entity>
from <context>.domain.exceptions import <Entity>NotFoundError, <Entity>AlreadyExistsError

class Sql<Entity>Repository(<Entity>Repository):
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, entity: <Entity>) -> None:
        ...
    
    def get_by_id(self, id: UUID) -> Optional[<Entity>]:
        ...
```

**SQL Model Pattern** in `<context>/adapters/secondary/sql/model/<entity>_model.py`:
```python
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field
from typing import Optional

class <Entity>Table(SQLModel, table=True):
    __tablename__ = "<Entity>Table"
    
    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    name: str = Field(nullable=False)
    field: str = Field(description="Field description")
    optional_field: Optional[str] = Field(default=None, nullable=True)
    # For lists: json_field: str = Field(default="[]", description="Field as JSON string")
```

#### 2. In-Memory Repository (Testing/Prototyping)
**Location**: `<context>/adapters/secondary/in_memory/in_memory_<name>_repository.py`

**MANDATORY Structure**:
```python
from typing import Optional
from uuid import UUID
from <context>.application.gateways import <Entity>Repository
from <context>.domain.entities import <Entity>
from <context>.domain.exceptions import <Entity>NotFoundError, <Entity>AlreadyExistsError

class InMemory<Entity>Repository(<Entity>Repository):
    def __init__(self):
        self.storage: dict[UUID, <Entity>] = {}
    
    def save(self, entity: <Entity>) -> None:
        if entity.id in self.storage:
            raise <Entity>AlreadyExistsError(entity.id)
        self.storage[entity.id] = entity
    
    def get_by_id(self, id: UUID) -> Optional[<Entity>]:
        return self.storage.get(id)
```

#### 3. Others
**Location**: `<context>/adapters/secondary/<type>/<type>_<name>_gateway.py`

Depends entirely on the type of the gateway (api, messaging, etc.)


**MANDATORY Structure**:
```python
from typing import Optional
from uuid import UUID
from <context>.application.gateways import <Gateway>

class <ImplType><Gateway(<Gateway>):
    ...
```


## INTEGRATION TEST STRUCTURE (CRITICAL)

### Test File Location (MANDATORY)
Tests MUST be in `tests/<context>/integration/test_<implementation>_<name>.py`

### conftest.py Pattern (CRITICAL)
EVERY context's integration `conftest.py` MUST provide:

#### For SQL Implementations:
```python
import pytest
from sqlmodel import create_engine, Session, SQLModel

@pytest.fixture(scope="function")
def database_engine():
    """CRITICAL: Function-scoped for test isolation. In-memory SQLite is fast and needs no cleanup."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def session(database_engine):
    with Session(database_engine) as session:
        yield session

@pytest.fixture
def sql_entity_repository(session):
    return SqlEntityRepository(session)
```

#### For Other Types Implementations:
```python
import pytest
from <context>.adapters.secondary import <Implementation>Gateway

@pytest.fixture(scope="session")  # Can be session-scoped (stateless)
def implementation_gateway():
    return <Implementation>Gateway()
```

### Test Pattern (MANDATORY - Arrange-Act-Assert)

#### SQL Repository Tests:
```python
import pytest
from uuid import uuid4
from <context>.domain.entities import Entity
from <context>.domain.exceptions import EntityNotFoundError, EntityAlreadyExistsError

def test_should_save_and_retrieve_entity(sql_entity_repository):
    # Arrange
    entity_id = uuid4()
    entity = Entity(id=entity_id, name="Test", field="value")
    
    # Act
    sql_entity_repository.save(entity)
    retrieved = sql_entity_repository.get_by_id(entity_id)
    
    # Assert
    assert retrieved is not None
    assert retrieved.id == entity_id
    assert retrieved.name == "Test"

def test_should_raise_error_when_saving_duplicate(sql_entity_repository):
    # Arrange
    entity = Entity(id=uuid4(), name="Duplicate", field="value")
    sql_entity_repository.save(entity)
    
    # Act & Assert
    with pytest.raises(EntityAlreadyExistsError):
        sql_entity_repository.save(entity)
```

#### Other types Gateway, with crypto gateway as example
```python
import pytest

def test_should_encrypt_and_decrypt_with_same_key(crypto_gateway):
    # Arrange
    plaintext = "secret_data"
    key = "encryption_key"
    
    # Act
    encrypted = crypto_gateway.encrypt(plaintext, key)
    decrypted = crypto_gateway.decrypt(encrypted, key)
    
    # Assert
    assert decrypted == plaintext
    assert encrypted != plaintext

def test_should_hash_password_successfully(hashing_gateway):
    # Arrange
    password = "secure_password123"
    
    # Act
    hashed = hashing_gateway.hash(password)
    
    # Assert
    assert hashed != password
    assert hashing_gateway.verify(password, hashed)

def test_should_fail_verification_with_wrong_password(hashing_gateway):
    # Arrange
    password = "secure_password123"
    wrong = "wrong_password"
    hashed = hashing_gateway.hash(password)
    
    # Act & Assert
    assert not hashing_gateway.verify(wrong, hashed)

def test_should_generate_different_hashes_for_same_input(hashing_gateway):
    # Arrange
    password = "secure_password123"
    
    # Act
    hash1 = hashing_gateway.hash(password)
    hash2 = hashing_gateway.hash(password)
    
    # Assert
    assert hash1 != hash2  # Due to salt
```

### Test Naming Convention (MANDATORY)
Format: `test_should_<expected_behavior>_when_<condition>`
- `test_should_save_and_retrieve_entity`
- `test_should_raise_error_when_saving_duplicate`
- `test_should_encrypt_and_decrypt_with_same_key`

## TDD PROCESS (CRITICAL - NEVER SKIP STEPS)

### STEP 1: PLAN Phase
Before ANY implementation, you MUST:
1. Identify the gateway Protocol from `application/gateways/`
2. **CRITICAL**: Verify that gateway methods express BUSINESS INTENT (not generic CRUD)
3. List ALL methods with their signatures
4. Determine implementation type (SQL, Crypto, HTTP, etc.)
5. List ALL test cases for each method
6. Identify domain exceptions that should be raised
7. WAIT FOR MY VALIDATION before proceeding

**PLAN Example (Repository - Acceptable CRUD for aggregate root, only for CRUD use cases):**
```
Gateway: PasswordRepository (Protocol)
Implementation: SqlPasswordRepository
Location: password_management_context/adapters/secondary/sql/

Type: Repository (owns Password aggregate in this context)
Justification: Password is owned by password_management_context, CRUD operations acceptable

Methods to implement:
- save(password: Password) -> None
- get_by_id(id: UUID) -> Password
- list_all(folder: Optional[str]) -> List[Password]
- update(password: Password) -> None
- delete(id: UUID) -> None

Test Cases:
1. GIVEN valid password WHEN save THEN password is stored and retrievable
2. GIVEN duplicate password WHEN save THEN raise PasswordAlreadyExistsError
3. GIVEN existing password WHEN update THEN changes are persisted
4. GIVEN non-existent password WHEN update THEN raise PasswordNotFoundError
5. GIVEN existing password WHEN delete THEN password is removed
6. GIVEN non-existent password WHEN delete THEN raise PasswordNotFoundError
7. GIVEN passwords in DB WHEN list_all THEN all passwords returned
8. GIVEN folder filter WHEN list_all THEN only folder passwords returned

Infrastructure Needed:
- PasswordTable model in sql/model/password.py
- Database fixture in conftest.py using in-memory SQLite + SQLModel.metadata.create_all()
- Session fixture

Domain Exceptions:
- PasswordNotFoundError(uuid)
- PasswordAlreadyExistsError(name)
```

**PLAN Example (Gateway - Business Intent):**
```
Gateway: GroupAccessGateway (Protocol)
Implementation: GroupAccessGatewayAdapter
Location: identity_access_management_context/adapters/secondary/

Type: Gateway (cross-context access to IAM from password_management)
Justification: Expresses business intent for authorization checks

Methods to implement:
- is_user_owner_of_group(user_id: UUID, group_id: UUID) -> bool
- is_user_member_of_group(user_id: UUID, group_id: UUID) -> bool
- group_exists(group_id: UUID) -> bool
- get_group_owner_users(group_id: UUID) -> list[UUID]

Test Cases:
1. GIVEN user owns group WHEN is_user_owner_of_group THEN return True
2. GIVEN user not owner WHEN is_user_owner_of_group THEN return False
3. GIVEN user is member WHEN is_user_member_of_group THEN return True
4. GIVEN user not member WHEN is_user_member_of_group THEN return False
5. GIVEN group exists WHEN group_exists THEN return True
6. GIVEN group not exists WHEN group_exists THEN return False
7. GIVEN group with owners WHEN get_group_owner_users THEN return owner IDs

Infrastructure Needed:
- Access to GroupRepository and GroupMemberRepository from IAM context
- Integration test fixtures with group and member data

Domain Exceptions:
- None (returns boolean/empty list, not exceptions)
```

### STEP 2: SETUP Phase
1. Create SQL model (if SQL implementation)
2. Update conftest.py with necessary fixtures
3. Verify fixtures work with simple test

### STEP 3: IMPLEMENT Phase (One Method at a Time)
For EACH method:
1. **RED**: Write ONLY the test for this method (must fail)
   - Run: `uv pytest tests/<context>/integration/test_<name>.py::<test_name>`
   - Verify it fails with expected error
2. **GREEN**: Implement MINIMAL code in gateway to pass THIS test only
   - Run same test again
   - Verify it passes
3. Move to next method (NEVER refactor until ALL tests pass)

### STEP 4: REFACTOR Phase (ONLY After ALL Tests Pass)
When ALL tests are GREEN:
1. Extract common logic to helper methods
2. Improve error handling
3. Add type hints if missing
4. Optimize queries (if SQL)

NEVER refactor if ANY test is failing.

## EXECUTION RULES (CRITICAL)

1. **Run Tests**: ALWAYS use `uv pytest tests/<context>/integration/test_<name>.py`
2. **Test Isolation**: CRITICAL - Each test MUST be independent (use function-scoped fixtures)
3. **One Method At A Time**: NEVER implement multiple methods before testing
4. **Real Infrastructure**: Integration tests MUST use real implementations (SQL, crypto libraries)
5. **No Mocking**: NEVER mock in integration tests (use real dependencies)
6. **Cleanup**: Use `sqlite:///:memory:` — no temp files, no manual cleanup needed
7. **Schema Setup**: Integration tests use `SQLModel.metadata.create_all()` with in-memory SQLite (fast); Alembic migrations are for E2E tests and production only

## FINAL VALIDATION

Before marking gateway as complete, verify:
- [ ] ALL tests pass: `uv pytest tests/<context>/integration/test_<name>.py`
- [ ] Gateway implements ALL Protocol methods
- [ ] **CRITICAL**: Gateway methods express BUSINESS INTENT (not generic CRUD unless Repository)
- [ ] Implementation is in correct location (`adapters/secondary/`)
- [ ] SQL models use SQLModel with proper constraints
- [ ] conftest.py provides all needed fixtures with function scope
- [ ] Tests use Arrange-Act-Assert pattern
- [ ] Test names follow `test_should_<what>_when_<condition>` pattern
- [ ] Domain exceptions are raised appropriately
- [ ] No test isolation issues (tests can run in any order)

## CRITICAL REMINDER

**Before implementing ANY gateway, ask yourself:**
- "Is this a Repository (managing aggregate roots in THIS context)?" → CRUD acceptable
- "Is this a Gateway (cross-context or business validation)?" → Business intent MANDATORY
- "Could I express this method more specifically to show business intent?" → If yes, DO IT

**Examples of good business intent methods:**
- `is_user_authorized_to_access_password()` ✅
- `has_user_exceeded_password_limit()` ✅
- `can_user_share_password_with_group()` ✅
- `list_user_shared_passwords()` ✅

**NOT:**
- `get_user()` ❌
- `get_password()` ❌
- `get_permissions()` ❌

Wait for instructions.
