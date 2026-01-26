---
mode: agent
imports:
  - default_back
---

You are helping me create or update a use case using STRICT TDD (Red, Green, Refactor).

## CRITICAL ARCHITECTURE RULES

### Bounded Contexts Structure
This project follows DDD with these bounded contexts:
- `identity_access_management_context/` - Users, groups, authentication, SSO
- `password_management_context/` - Password CRUD, permissions, folders
- `vault_management_context/` - Vault setup, unlock/lock, encryption keys
- `audit_logging_context/` - Audit logs tracking
- `shared_kernel/` - Shared utilities (authentication, encryption, time, access_control, pubsub)

### Use Case Structure (MANDATORY)
EVERY use case MUST follow this EXACT structure:
```python
from <context>.application.commands import <UseCaseName>Command
from <context>.application.gateways import Gateway1, Gateway2
from <context>.domain.entities import Entity1
from <context>.domain.exceptions import CustomError
from shared_kernel.authentication import AdminPermissionChecker  # if needed

class <UseCaseName>UseCase:
    def __init__(
        self,
        gateway1: Gateway1,
        gateway2: Gateway2,
    ):
        self.gateway1 = gateway1
        self.gateway2 = gateway2

    def execute(self, command: <UseCaseName>Command) -> ReturnType:
        # Permission checks first (if needed)
        # Business logic validation
        # Domain entity creation/manipulation
        # Gateway calls for persistence/external services
        return result
```

### Import Rules (CRITICAL - NEVER VIOLATE)
- Use cases MUST ONLY import from:
  - `<context>/application/` (commands, gateways, responses, services)
  - `<context>/domain/` (entities, exceptions, value_objects, events)
  - `shared_kernel/` (authentication, encryption, time, access_control, pubsub)
- NEVER import from `adapters/` or any infrastructure layer
- NEVER import from other contexts (use gateways for cross-context communication)

### Command Pattern (MANDATORY)
Commands are dataclasses in `application/commands/`:
```python
from dataclasses import dataclass
from uuid import UUID
from shared_kernel.authentication import AuthenticatedUser  # if permission check needed

@dataclass
class CreateSomethingCommand:
    requesting_user: AuthenticatedUser  # for permission checks
    id: UUID
    field1: str
    field2: int
    optional_field: str | None = None
```

### Gateway Pattern (MANDATORY)
Gateways are abstract interfaces in `application/gateways/`:
```python
from abc import ABC, abstractmethod
from uuid import UUID
from <context>.domain.entities import Entity

class EntityRepository(ABC):
    @abstractmethod
    def save(self, entity: Entity) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, id: UUID) -> Entity | None:
        pass
```

### Domain Exceptions (MANDATORY)
All business exceptions in `domain/exceptions.py`:
```python
class <Context>DomainError(Exception):
    """Base exception for this context"""
    pass

class SpecificError(<Context>DomainError):
    def __init__(self, param: UUID):
        super().__init__(f"Error message with {param}")
```

## TEST STRUCTURE (CRITICAL)

### Test File Organization
```
tests/<context>/unit/
├── conftest.py          # Fixtures for this context
├── fakes/               # Fake implementations
│   ├── __init__.py
│   ├── fake_<gateway_name>.py
└── use_cases/
    └── test_<use_case_name>.py
```

### conftest.py Pattern (MANDATORY)
EVERY context's `conftest.py` MUST provide fixtures:
```python
import pytest
from <context>.adapters.secondary import InMemory<Entity>Repository
from tests.<context>.unit.fakes import Fake<Gateway>

@pytest.fixture
def entity_repository():
    return InMemory<Entity>Repository()

@pytest.fixture
def custom_gateway():
    return Fake<Gateway>()
```

### Fake Implementations (MANDATORY)
Fakes in `tests/<context>/unit/fakes/fake_<name>.py`:
```python
from <context>.application.gateways import SomeGateway

class FakeSomeGateway(SomeGateway):
    def __init__(self):
        self._data: dict = {}
    
    def some_method(self, param: str) -> str:
        return f"fake_result({param})"
    
    # Test helpers (not in interface)
    def set_test_data(self, key: str, value: str) -> None:
        self._data[key] = value
```

### Test Pattern (MANDATORY - Arrange-Act-Assert)
```python
import pytest
from uuid import UUID
from <context>.application.use_cases import SomeUseCase
from <context>.application.commands import SomeCommand
from <context>.domain.exceptions import SomeError

@pytest.fixture
def use_case(gateway1, gateway2):  # From conftest
    return SomeUseCase(gateway1, gateway2)

def test_given_stuff_when_executing_should_return_expected_result(
    use_case: SomeUseCase,
    entity_repository: EntityRepository,
):
    # Arrange
    entity_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    command = SomeCommand(id=entity_id, field="value")
    
    # Act
    result = use_case.execute(command)
    
    # Assert
    assert result == entity_id
    saved = entity_repository.get_by_id(entity_id)
    assert saved.field == "value"

def test_given_stuff_when_executing_should_raise_error(use_case: SomeUseCase):
    # Arrange
    invalid_command = SomeCommand(id=UUID(...), field="invalid")
    
    # Act & Assert
    with pytest.raises(SomeError):
        use_case.execute(invalid_command)
```

### Test Naming Convention (MANDATORY)
Format: `test_given_<input>when_<calling_use_case>should_<expected_behavior>`
Examples:
- `test_given_user_when_creating_should_return_user_id`
- `test_given_invalid_user_when_creating_should_raise_error`
- `test_given_valid_data_when_saving_should_encrypt_password`

## TDD PROCESS (CRITICAL - NEVER SKIP STEPS)

### STEP 1: PLAN Phase
Before ANY implementation, you MUST:
1. Identify the bounded context (or ask if unclear)
2. List ALL test cases with Given-When-Then format
3. List ALL gateways needed with their methods
4. List ALL domain exceptions needed
5. Confirm if `shared_kernel` imports needed (authentication, encryption, etc.)
6. WAIT FOR MY VALIDATION before proceeding

**PLAN Example:**
```
Context: password_management_context

Use Case: CreatePasswordUseCase
Command: CreatePasswordCommand(user_id, group_id, id, name, decrypted_password, folder?)
Returns: UUID

Test Cases:
1. GIVEN user owns group WHEN creating password THEN password is created and encrypted
2. GIVEN user not owner WHEN creating password THEN raise UserNotOwnerOfGroupError
3. GIVEN group not exists WHEN creating password THEN raise GroupNotFoundError
4. GIVEN valid password WHEN created THEN permissions are set for group

Gateways:
- PasswordRepository (save, get_by_id)
- PasswordPermissionsRepository (set_owner)
- GroupAccessGateway (group_exists, is_user_owner_of_group)

Shared Kernel:
- EncryptionService (encrypt)

Domain Exceptions:
- GroupNotFoundError(group_id)
- UserNotOwnerOfGroupError(user_id, group_id)
```

### STEP 2: IMPLEMENT Phase (One Test at a Time)
For EACH test case:
1. **RED**: Write ONLY the test (must fail)
   - Run: `uv pytest tests/<context>/unit/use_cases/test_<name>.py::<test_name>`
   - Verify it fails with expected error
2. **GREEN**: Write MINIMAL code in use case to pass THIS test only
   - Run same test again
   - Verify it passes
3. Move to next test (NEVER refactor until ALL tests pass)

**Implementation Example:**
```python
# RED - Test 1
def test_should_create_password_when_user_owns_group(
    use_case: CreatePasswordUseCase,
    password_repository: PasswordRepository,
    group_access_gateway: GroupAccessGateway,
):
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")
    
    group_access_gateway.set_group_owner(group_id, user_id)
    
    command = CreatePasswordCommand(
        user_id=user_id,
        group_id=group_id,
        id=password_id,
        name="My Password",
        decrypted_password="secret123",
    )
    
    result_id = use_case.execute(command)
    
    assert result_id == password_id
    saved = password_repository.get_by_id(password_id)
    assert saved is not None
    assert saved.name == "My Password"

# GREEN - Minimal implementation
class CreatePasswordUseCase:
    def __init__(self, password_repository, encryption_service, 
                 password_permissions_repository, group_access_gateway):
        self.password_repository = password_repository
        self.encryption_service = encryption_service
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
    
    def execute(self, command: CreatePasswordCommand) -> UUID:
        encrypted_value = self.encryption_service.encrypt(command.decrypted_password)
        password = Password.create(
            id=command.id,
            name=command.name,
            encrypted_value=encrypted_value,
            folder=command.folder,
        )
        self.password_repository.save(password)
        return password.id
```

### STEP 3: REFACTOR Phase (ONLY After ALL Tests Pass)
When ALL tests are GREEN, extract:
1. **Commands** → `application/commands/<command_name>.py`
2. **Responses** → `application/responses/<response_name>.py` (if complex return)
3. **Services** → `application/services/<service_name>.py` (if duplicated logic from other use cases, or complex orchestration)
4. **Domain Logic** → Move to `domain/entities/` or `domain/value_objects/`
5. Update `__init__.py` files for imports

NEVER refactor if ANY test is failing.

## EXECUTION RULES (CRITICAL)

1. **Run Tests**: ALWAYS use `uv pytest <test_context_folder>` for current context
2. **One Test At A Time**: NEVER write multiple tests before making them pass
3. **Minimal Implementation**: Write ONLY enough code to pass current test
4. **No Premature Abstraction**: Keep code simple until refactor phase
5. **Fixtures Usage**: ALWAYS use pytest fixtures from conftest.py
6. **No Comments**: Code must be self-documenting (NEVER add redundant comments)

## FINAL VALIDATION

Before marking use case as complete, verify:
- [ ] ALL tests pass: `uv pytest tests/<context>`
- [ ] Use case follows exact structure pattern
- [ ] All imports are from allowed layers only
- [ ] Command and gateways are properly defined
- [ ] Fakes are in `tests/<context>/unit/fakes/`
- [ ] conftest.py provides all needed fixtures
- [ ] Test names follow `test_should_<what>_when_<condition>` pattern
- [ ] No redundant comments in code

Wait for instructions.
