---
mode: agent
imports:
  - default_back
---

You are helping me implement FastAPI routes (primary adapters) for one or multiple use cases.

## CRITICAL ARCHITECTURE RULES

### Route Structure (MANDATORY)
Routes are primary adapters in `<context>/adapters/primary/fastapi/routes/`.

**File Naming Convention (CRITICAL)**:
- Format: `<entity>_<action>_routes.py`
- Examples: `password_create_routes.py`, `password_get_routes.py`, `user_delete_routes.py`
- ONE route per file (single responsibility)

**Router Configuration**:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/<entities>", tags=["<Context> Management"])
```

**Examples**:
- `router = APIRouter(prefix="/passwords", tags=["Password Management"])`
- `router = APIRouter(prefix="/users", tags=["User Management"])`
- `router = APIRouter(prefix="/vault", tags=["Vault"])`

### Request/Response Models (MANDATORY)

**Naming Convention (CRITICAL)**:
- Request: `<Action><Entity>Request`
- Response: `<Action><Entity>Response`
- Use Pydantic `BaseModel`

```python
from pydantic import BaseModel
from uuid import UUID

class CreatePasswordRequest(BaseModel):
    name: str
    password: str
    folder: str | None = None
    group_id: str

class CreatePasswordResponse(BaseModel):
    id: UUID
```

**Field Types (MANDATORY)**:
- Use proper types: `UUID`, `str`, `int`, `bool`, `list[...]`
- Use `str | None` for optional fields (not `Optional[str]`)
- NEVER use `Any` type

### Authentication (CRITICAL)

**Pattern for Authenticated Routes**:
```python
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.adapters.primary.app_dependencies import get_current_user
from fastapi import Depends

def endpoint(
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: SomeUseCase = Depends(get_some_usecase),
):
    # current_user.user_id available
    # current_user.roles available for authorization
```

**Pattern for Public Routes** (login, register, vault status):
```python
def endpoint(
    usecase: SomeUseCase = Depends(get_some_usecase),
):
    # No authentication required
```

**NEVER** import or use authentication from other locations.

### Exception Handling (MANDATORY)

**Standard Exception Mapping**:
```python
from fastapi import HTTPException
import logging

try:
    result = usecase.execute(command)
    return Response(...)
except <Entity>NotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
except <Entity>AccessDeniedError as e:
    raise HTTPException(status_code=403, detail=str(e))
except AccessDeniedError as e:  # from shared_kernel
    raise HTTPException(status_code=403, detail=str(e))
except <Context>DomainError as e:  # Catch-all for domain errors
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logging.error(e)
    raise HTTPException(status_code=500, detail="Internal server error")
```

**Exception Hierarchy (CRITICAL)**:
1. Specific exceptions first (NotFoundError, AccessDeniedError)
2. Context domain error (PasswordManagementDomainError)
3. Generic Exception last
4. ALWAYS log unexpected exceptions with `logging.error(e)`


### Swagger Documentation (MANDATORY)

**Complete Example**:
```python
@router.post(
    "/",
    response_model=CreatePasswordResponse,
    status_code=201,
    summary="Create a new password",
)
def create_password(
    request_body: CreatePasswordRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: CreatePasswordUseCase = Depends(get_create_password_usecase),
):
    """
    Create a new password entry.

    - **name**: Name/title for the password entry
    - **password**: The actual password to store (will be encrypted)
    - **folder**: Optional folder to organize the password
    - **group_id**: Group ID for password ownership
    - **Authentication**: Requires authentication via access_token cookie
    """
```

**Documentation Requirements (CRITICAL)**:
- `summary`: Short one-line description
- Docstring: Detailed description with parameter explanations
- List each field with `- **field_name**: Description`
- Always mention authentication requirements
- Use proper HTTP method in decorator

### Dependencies (app_dependencies.py)

**Location**: `<context>/adapters/primary/fastapi/app_dependencies.py`

**Pattern (MANDATORY)**:
```python
from fastapi import Depends
from starlette.requests import Request

# Gateway getter from app.state
def get_entity_repository(request: Request) -> EntityRepository:
    return request.app.state.entity_repository

# Use case factory with dependencies
def get_create_entity_usecase(
    entity_repository: EntityRepository = Depends(get_entity_repository),
    other_gateway: OtherGateway = Depends(get_other_gateway),
):
    return CreateEntityUseCase(entity_repository, other_gateway)
```

**Rules**:
- All gateways accessed via `request.app.state.<gateway_name>`
- Use case factories inject dependencies using `Depends()`
- NEVER instantiate gateways directly in route files
- Reuse gateway getters across multiple use case factories

### Routes Registration (__init__.py)

**Location**: `<context>/adapters/primary/fastapi/routes/__init__.py`

**Pattern (MANDATORY)**:
```python
from fastapi import APIRouter
from . import (
    entity_create_routes,
    entity_get_routes,
    entity_update_routes,
    entity_delete_routes,
)

def get_<context>_management_router():
    <context>_management_router = APIRouter()
    
    <context>_management_router.include_router(entity_create_routes.router)
    <context>_management_router.include_router(entity_get_routes.router)
    <context>_management_router.include_router(entity_update_routes.router)
    <context>_management_router.include_router(entity_delete_routes.router)
    
    return <context>_management_router
```

### Main.py Integration

**Dependencies Setup in Lifespan (MANDATORY)**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    engine = create_engine(get_database_url())
    
    with Session(engine) as session:
        # Initialize all gateways/repositories
        entity_repository = SqlEntityRepository(session)
        app.state.entity_repository = entity_repository
        
        # ... more dependencies
        
        yield
```

**Router Registration**:
```python
from <context>.adapters.primary.fastapi.routes import get_<context>_management_router

app = FastAPI()
app.include_router(get_<context>_management_router(), prefix="/api")
```

## E2E TESTING (CRITICAL)

### Test Structure

**Location**: `tests/e2e/test_<domain>_workflow.py` — all E2E tests are flat in `tests/e2e/`, NO subdirectories.

**Existing workflow files**:
- `test_complete_user_workflow.py` — user creation, deletion, promotion, password update
- `test_complete_groups_workflow.py` — group CRUD, ownership, membership
- `test_complete_authentication_workflow.py` — login, SSO, token refresh
- `test_password_management_workflow.py` — password CRUD, sharing, access control
- `test_vault_workflow.py` — vault setup, lock/unlock

**CRITICAL — Update before Create (MANDATORY)**:
1. **First**, identify which existing workflow file covers the same domain as the route you are adding
2. **If one exists**: add a new phase/section to the existing test function — do NOT create a new file
3. **Only if no related workflow exists**: create a new `test_<domain>_workflow.py` with a single test function `test_complete_<domain>_workflow`

**Naming Convention**:
- File: `test_<domain>_workflow.py`
- Function: `test_complete_<domain>_workflow` (one function per file)
- Examples: `test_password_management_workflow.py::test_complete_password_management_workflow`

### Test Pattern (MANDATORY)

All E2E tests follow a **single large function per file**, divided into clearly labelled phases using comment blocks. Each new feature is added as a new phase at the end of the relevant existing test.

**Adding to an existing test (default case)**:
```python
# In tests/e2e/test_password_management_workflow.py

def test_complete_password_management_workflow(
    client_factory, setup, configured_sso, sso_user_token
):
    """
    ...(existing docstring)...
    Phase N: <New feature description>
    - <bullet describing new steps>
    """
    # ... existing phases ...

    # =========================================================================
    # PHASE N: <NEW FEATURE NAME IN CAPS>
    # =========================================================================

    admin_client = client_factory()
    # ... setup for this phase (re-use variables from earlier phases when available) ...

    # Step N.1: <description>
    response = admin_client.post("/api/passwords/export", json={"format": "csv"})
    assert response.status_code == 200
    assert "name" in response.json()[0]

    # Step N.2: <description>
    ...
```

**Creating a new workflow file (only when no related file exists)**:
```python
# tests/e2e/test_<domain>_workflow.py
"""
Complete end-to-end test for <domain> workflow.

This consolidated test covers:
- <feature 1>
- <feature 2>
"""


def test_complete_<domain>_workflow(client_factory, setup):
    """
    Complete <domain> workflow.

    Phase 1: <description>
    - <bullet>
    Phase 2: <description>
    - <bullet>
    """

    # =========================================================================
    # PHASE 1: <FEATURE NAME IN CAPS>
    # =========================================================================

    admin_client = client_factory()
    # register + login admin
    admin_client.post(
        "/api/auth/register-admin",
        json={"email": "admin@example.com", "password": "admin", "display_name": "Admin"},
    )
    admin_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin"},
    )

    me_response = admin_client.get("/api/users/me")
    assert me_response.status_code == 200
    group_id = me_response.json()["personal_group_id"]

    # Step 1.1: CREATE
    create_response = admin_client.post(
        "/api/passwords",
        json={"name": "Test", "password": "SecureP@ss123", "group_id": group_id},
    )
    assert create_response.status_code == 201
    resource_id = create_response.json()["id"]

    # Step 1.2: READ
    get_response = admin_client.get(f"/api/passwords/{resource_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Test"

    # =========================================================================
    # PHASE 2: <NEXT FEATURE IN CAPS>
    # =========================================================================

    # ...
```

### E2E Test Fixtures (conftest.py)

**Available Fixtures (MANDATORY USAGE)**:

| Fixture | Scope | Description |
|---|---|---|
| `client_factory` | function | Returns a factory `_make_client()` → fresh `CsrfTestClient` per call. **Preferred over `e2e_client` for multi-user tests.** |
| `e2e_client` | function | Single `CsrfTestClient`. Use only when one actor is enough. |
| `setup` | function | Runs vault setup via `authenticated_admin_client`. Required when encryption is used. |
| `authenticated_admin_client` | function | `e2e_client` already logged in as `admin@example.com` / `admin`. |
| `unauthenticated_client` | function | Fresh client with no session. |
| `configured_sso` | function | Configures OIDC provider. Requires `setup`. |
| `sso_user_factory` | function | `factory(email, name)` → `{token, user_id, email, display_name, client}`. Requires `configured_sso`. |

**CRITICAL**: Always use `client_factory` when a test involves more than one user to avoid cookie interference:
```python
def test_complete_sharing_workflow(client_factory, setup):
    admin_client = client_factory()
    user_client = client_factory()
    # Each client carries its own cookies independently
```

### E2E Test Rules (CRITICAL)

1. **Update before Create**: Always add to an existing workflow file when the domain matches; create a new file only if none exists
2. **One function per file**: Each workflow file contains exactly one `test_complete_<domain>_workflow` function
3. **Phase structure**: Organise steps into named phases with `# ===` separator comments and numbered steps (`# Step N.M:`)
4. **Test Happy Path Only**: E2E tests verify complete workflows work correctly
5. **Use Real FastAPI App**: Import `app` from `main` module (never mock)
6. **Temporary Database**: The `database` fixture wipes rows between tests — no manual cleanup needed
7. **Assert at Each Step**: Verify state after every operation, not just at the end
8. **No `e2e_client` for multi-user**: Use `client_factory()` whenever more than one authenticated user is needed

## TDD PROCESS (CRITICAL - NEVER SKIP STEPS)

### STEP 1: PLAN Phase
Before ANY implementation, you MUST:
1. Identify the use case(s) to create routes for
2. Determine authentication requirements and roles
3. List all routes needed with HTTP methods and paths
4. Define Request/Response models for each route
5. List domain exceptions that could be raised
6. Describe E2E workflow test scenarios
7. WAIT FOR MY VALIDATION before proceeding

**PLAN Example:**
```
Use Case: CreatePasswordUseCase
Context: password_management_context

Authentication: Required (ValidatedUser)
Authorization: User must be authenticated

Route:
- Method: POST
- Path: /passwords
- Prefix: /passwords (from router)
- Full Path: /api/passwords (when registered with /api prefix)
- Status: 201 Created

Request Model: CreatePasswordRequest
- name: str
- password: str
- folder: str | None
- group_id: str

Response Model: CreatePasswordResponse
- id: UUID

Domain Exceptions:
- GroupNotFoundError → 400
- UserNotOwnerOfGroupError → 403
- PasswordManagementDomainError → 400 (catch-all)

Dependencies Needed:
- get_password_repository(request)
- get_password_permissions_repository(request)
- get_group_access_gateway(request)
- get_create_password_usecase(...dependencies...)

E2E Test:
- Related file: tests/e2e/test_password_management_workflow.py (already exists)
- Action: add a new phase "PHASE N: PASSWORD CREATION" to the existing test function
- Steps:
  1. Use client_factory() for the admin client
  2. Create password with POST /api/passwords → assert 201 + id
  3. Read back with GET /api/passwords/{id} → assert name/password match
```

### STEP 2: IMPLEMENT Phase
1. Create route file: `<entity>_<action>_routes.py`
2. Define Request/Response models
3. Implement route handler with proper exception handling
4. Create/update dependencies in `app_dependencies.py`
5. Register route in `__init__.py`
6. Update `main.py` if new dependencies needed in lifespan

### STEP 3: TEST Phase
1. Identify the relevant existing workflow file in `tests/e2e/` (check the list above)
2. **If a related file exists**: append a new phase to the existing test function
3. **If no related file exists**: create `tests/e2e/test_<domain>_workflow.py` with a single `test_complete_<domain>_workflow` function
4. Use appropriate fixtures (`client_factory`, `setup`, `configured_sso`, etc.)
5. Assert state at each step
6. Run test: `uv run pytest tests/e2e/test_<domain>_workflow.py`

### STEP 4: FINALIZE Phase
Verify:
- Route is accessible via full path
- Authentication works correctly
- All exceptions are properly mapped
- Swagger documentation is complete
- E2E test passes

## EXECUTION RULES (CRITICAL)

1. **One Route Per File**: NEVER put multiple routes in one file
2. **Proper Naming**: Follow `<entity>_<action>_routes.py` pattern
3. **Type Safety**: Use proper types, NEVER `Any`
4. **Exception Order**: Specific → Domain → Generic
5. **Logging**: ALWAYS log unexpected exceptions
6. **Documentation**: Complete docstrings with field descriptions
7. **Dependencies**: Access via `request.app.state`, NEVER instantiate directly
8. **E2E Tests**: Update an existing workflow file when the domain matches; create a new one only if none exists

## FINAL VALIDATION

Before marking routes as complete, verify:
- [ ] Route file follows naming convention: `<entity>_<action>_routes.py`
- [ ] Router has correct prefix and tags
- [ ] Request/Response models use proper naming and types
- [ ] Authentication is properly implemented (if required)
- [ ] All domain exceptions are caught and mapped
- [ ] Swagger documentation is complete and accurate
- [ ] Dependencies are in `app_dependencies.py` using `request.app.state`
- [ ] Route is registered in `__init__.py` (order matters!)
- [ ] `main.py` lifespan initializes required dependencies
- [ ] Existing related workflow file was updated (or new file created if none existed)
- [ ] New steps added as a new phase with `# ===` separator and numbered steps
- [ ] E2E test uses proper fixtures (`client_factory` for multi-user, `setup` when encryption needed)
- [ ] E2E test passes: `uv run pytest tests/e2e/test_<domain>_workflow.py`

## DISCREPANCY RESOLUTION

**Enforced Standard**: If you find inconsistencies between contexts, follow these rules:
1. **File Naming**: `<entity>_<action>_routes.py` (NOT `<action>_<entity>_routes.py`)
2. **Optional Types**: Use `str | None` (NOT `Optional[str]`)
3. **Router Registration Order**: Specific paths before generic paths
4. **Exception Handling**: Specific exceptions first, then domain error, then generic
5. **E2E Test Focus**: Happy path workflows (NOT individual endpoint tests)

Wait for instructions.
