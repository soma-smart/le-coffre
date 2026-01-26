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
from shared_kernel.authentication import ValidatedUser, get_current_user
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

**Location**: `tests/e2e/<context>/test_<feature>_workflow.py`

**Naming Convention (MANDATORY)**:
- Test complete workflows, not individual endpoints
- Format: `test_<feature>_workflow`
- Examples: `test_share_password_workflow`, `test_user_creation_with_personal_group`

### Test Pattern (MANDATORY)

**Complete Workflow Example**:
```python
def test_password_crud_workflow(e2e_client, setup):
    """
    Complete workflow: Create → Read → Update → Read → Delete → Verify Deleted
    
    This tests the entire password lifecycle end-to-end.
    """
    # Setup: Register and login admin
    admin_data = {
        "email": "admin@example.com",
        "password": "admin",
        "display_name": "Admin",
    }
    e2e_client.post("/api/auth/register-admin", json=admin_data)
    e2e_client.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin"})
    
    # Get personal group
    me_response = e2e_client.get("/api/users/me")
    assert me_response.status_code == 200
    group_id = me_response.json()["personal_group_id"]
    
    # Step 1: CREATE - Create a password
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": "SecureP@ss123",
            "folder": "Work",
            "group_id": group_id,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]
    
    # Step 2: READ - Verify password was created
    get_response = e2e_client.get(f"/api/passwords/{password_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Test Password"
    assert get_response.json()["password"] == "SecureP@ss123"
    
    # Step 3: UPDATE - Update the password
    update_response = e2e_client.put(
        f"/api/passwords/{password_id}",
        json={
            "name": "Updated Password",
            "password": "NewP@ss456",
            "folder": "Personal",
        },
    )
    assert update_response.status_code == 200
    
    # Step 4: READ - Verify update was successful
    get_updated = e2e_client.get(f"/api/passwords/{password_id}")
    assert get_updated.status_code == 200
    assert get_updated.json()["name"] == "Updated Password"
    assert get_updated.json()["password"] == "NewP@ss456"
    assert get_updated.json()["folder"] == "Personal"
    
    # Step 5: DELETE - Delete the password
    delete_response = e2e_client.delete(f"/api/passwords/{password_id}")
    assert delete_response.status_code == 204
    
    # Step 6: VERIFY DELETED - Confirm password no longer exists
    get_deleted = e2e_client.get(f"/api/passwords/{password_id}")
    assert get_deleted.status_code == 404
```

### E2E Test Fixtures (conftest.py)

**Available Fixtures (MANDATORY USAGE)**:
```python
@pytest.fixture
def e2e_client(database, env_vars):
    """TestClient with temporary database and environment"""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def setup(e2e_client):
    """Sets up vault with default shares (required for encryption)"""
    # Auto-setup vault

@pytest.fixture
def client_factory():
    """Creates separate clients to avoid cookie interference"""
    def _create_client():
        return TestClient(app)
    return _create_client

@pytest.fixture
def sso_user_factory(client_factory, configured_sso):
    """Factory to create and authenticate multiple SSO users"""
    def _create_sso_user(email: str, name: str):
        # Returns: {token, user_id, email, display_name, client}
    return _create_sso_user
```

**CRITICAL**: When testing with multiple users, use `client_factory` to avoid cookie interference:
```python
def test_multi_user_workflow(client_factory, setup):
    admin_client = client_factory()
    user1_client = client_factory()
    
    # Each client has separate cookies
```

### E2E Test Rules (CRITICAL)

1. **Test Happy Path Only**: E2E tests verify complete workflows work correctly
2. **Use Real FastAPI App**: Import from `main` module (not mocked)
3. **Temporary Database**: Each test gets fresh database via fixtures
4. **Complete Workflows**: Test sequences of operations, not single endpoints
5. **Assert at Each Step**: Verify state after each operation
6. **Authentication Setup**: Include login/registration when needed
7. **Clean Test Names**: Describe the full workflow being tested

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
- get_encryption_service(request)
- get_password_permissions_repository(request)
- get_group_access_gateway(request)
- get_create_password_usecase(...dependencies...)

E2E Test Workflow:
1. Setup admin user and login
2. Get admin's personal group ID
3. Create password with POST /api/passwords
4. Verify 201 response with password ID
5. Get password with GET /api/passwords/{id}
6. Verify password details match creation request
```

### STEP 2: IMPLEMENT Phase
1. Create route file: `<entity>_<action>_routes.py`
2. Define Request/Response models
3. Implement route handler with proper exception handling
4. Create/update dependencies in `app_dependencies.py`
5. Register route in `__init__.py`
6. Update `main.py` if new dependencies needed in lifespan

### STEP 3: TEST Phase
1. Create E2E workflow test in `tests/e2e/<context>/`
2. Test complete workflow (not just single endpoint)
3. Use appropriate fixtures (e2e_client, setup, client_factory)
4. Assert state at each step
5. Run test: `uv pytest tests/e2e/<context>/test_<feature>_workflow.py`

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
8. **E2E Tests**: Test workflows, not individual endpoints

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
- [ ] E2E workflow test covers complete user journey
- [ ] E2E test uses proper fixtures (e2e_client, setup, client_factory)
- [ ] E2E test passes: `uv pytest tests/e2e/<context>/test_<feature>_workflow.py`

## DISCREPANCY RESOLUTION

**Enforced Standard**: If you find inconsistencies between contexts, follow these rules:
1. **File Naming**: `<entity>_<action>_routes.py` (NOT `<action>_<entity>_routes.py`)
2. **Optional Types**: Use `str | None` (NOT `Optional[str]`)
3. **Router Registration Order**: Specific paths before generic paths
4. **Exception Handling**: Specific exceptions first, then domain error, then generic
5. **E2E Test Focus**: Happy path workflows (NOT individual endpoint tests)

Wait for instructions.
