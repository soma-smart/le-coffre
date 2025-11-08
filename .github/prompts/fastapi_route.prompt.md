---
mode: agent
imports:
  - default_back
---

You are helping me implement FastAPI routes (primary adapters) for one or multiple use cases.

### Rules:

1. **Planning**:
   - I will provide the use case(s) to create routes for
   - Analyze each use case and propose the route structure
   - Ask if authentication is needed and what roles are required
   - Wait for my validation before implementation

2. **Route Structure**:
   - One route per file: `<action>_<entity>_routes.py` 
   - Implementation in `<context>/adapters/primary/fastapi/routes/`
   - Use `<Action><Entity>Request` and `<Action><Entity>Response` models
   - Custom router with appropriate prefix and tags

3. **Request/Response Models**:
   - Pydantic models with clear field types
   - Include optional fields when needed
   - Use proper type hints (UUID, str, int, etc.)

4. **Authentication**:
   - Use `get_current_user` from `identity_access_management_context.adapters.primary.dependencies` when needed
   - Import `ValidatedUser` for authenticated routes
   - Handle role-based access control as required

5. **Exception Handling**:
   - Map domain exceptions to appropriate HTTP status codes:
     - NotFound → 404
     - AccessDenied/NotAdmin → 403  
     - Domain validation errors → 400
     - Unexpected errors → 500 with `logging.error()`

6. **Documentation**:
   - Complete Swagger documentation with summary and description
   - Include parameter descriptions and examples
   - Document authentication requirements
   - Specify response status codes

7. **Dependencies**:
   - Create use case dependencies in `app_dependencies.py`
   - Avoid duplication unless different configurations needed
   - Use FastAPI's dependency injection properly

8. **File Updates**:
   - Update `__init__.py` to include new route modules
   - Update `main.py` if new dependencies are needed in the lifespan

9. **E2E Testing**:
   - Create workflow tests in `tests/e2e/<context>/`
   - Test complete workflows. For example: Create → Read → Update → Read → Delete → Read
   - Use real `main.py` implementation with fixtures from `conftest.py`
   - Test only Happy Path scenarios
   - Include assertions at each step to verify state

### Process:
1. **PLAN**: Analyze use cases + propose routes + authentication needs → wait for validation
2. **IMPLEMENT**: Create routes + models + dependencies + update files
3. **TEST**: Create E2E workflow tests
4. **FINALIZE**: Ensure all routes work + summary

### Example Route Pattern:
```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
import logging

from <context>.adapters.primary.fastapi.app_dependencies import get_<action>_<entity>_usecase
from <context>.application.use_cases import <Action><Entity>UseCase
from <context>.application.commands import <Action><Entity>Command
from <context>.domain.exceptions import <EntityNotFoundError>
from identity_access_management_context.adapters.primary.dependencies import ValidatedUser, get_current_user

router = APIRouter(prefix="/<entities>", tags=["<Context> Management"])

class <Action><Entity>Request(BaseModel):
    # Request fields

class <Action><Entity>Response(BaseModel):
    # Response fields

@router.<method>("/<path>", response_model=<Action><Entity>Response, status_code=<code>, summary="<Summary>")
def <action>_<entity>(
    request: <Action><Entity>Request,
    current_user: ValidatedUser = Depends(get_current_user),  # If auth needed
    usecase: <Action><Entity>UseCase = Depends(get_<action>_<entity>_usecase),
):
    """
    <Description>
    
    - **field**: Description
    - **Authorization**: Bearer token (if needed)
    """
    try:
        command = <Action><Entity>Command(...)
        result = usecase.execute(command)
        return <Action><Entity>Response(...)
    except <DomainException> as e:
        raise HTTPException(status_code=<code>, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")
```

Wait for instructions.
