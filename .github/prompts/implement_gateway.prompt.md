---
mode: agent
imports:
  - default_back
---

You are helping me implement a gateway using strict TDD with integration tests.

### Rules:

1. **Implementation Planning**:
   - I will specify the gateway Protocol and the implementation type (SQL, Crypto, HTTP API, etc.)
   - Analyze the gateway methods and propose test cases for each method
   - Wait for my validation before implementation

2. **Test Planning**:
   - Plan integration tests for each gateway method
   - Include logical failure scenarios (connection errors, constraint violations)
   - Tests should be in `tests/<context>/integration/`
   - Use descriptive test names following Given-When-Then format

3. **TDD Implementation**:
   - One method at a time: Red → Green → Refactor (only after ALL tests pass)
   - Write failing test → Implement minimal logic in gateway → Next method
   - Use `uv pytest tests/<context>/integration/<test_file>` to run current tests
   - Follow Arrange-Act-Assert pattern

4. **Gateway Structure**:
   - Implementation in `<context>/adapters/secondary/gateways/`
   - Class inheriting from the Protocol
   - `__init__(dependencies)` for dependency injection
   - Only implement the logic required by the Protocol methods
   - Handle implementation-specific requirements as needed

5. **Infrastructure Setup**:
   - Create necessary models/schemas for the implementation type
   - Create fixtures in `conftest.py` for setup/teardown
   - Use temporary resources for test isolation

6. **Dependencies**:
   - Create required dependencies as needed
   - Use proper dependency injection in `__init__`
   - Handle resource lifecycle properly

7. **Test Fixtures**:
   - Use function-scoped fixtures for test isolation
   - Use `conftest.py` for shared fixtures across integration tests
   - Setup and teardown should be automatic

### Process:
1. **PLAN**: Analyze gateway + propose test cases for each method → wait for validation
2. **SETUP**: Create necessary infrastructure (models, fixtures, conftest)
3. **IMPLEMENT**: TDD cycle for each method → refactor when all pass
4. **FINALIZE**: Ensure all tests pass + summary

### SQL Implementation (Primary Pattern):
- Use SQLModel for ORM
- Create table models in `models/` subdirectory with `create_tables()` function
- Use SQLite with temporary files for tests
- Session-based dependency injection
- Handle upsert logic when appropriate
- Database fixtures should be function-scoped for isolation

### Example Structure:
```
src/<context>/adapters/secondary/gateways/
└── <type>/
    ├── <type>_<name>_<gateway>.py
    └── models/ (for SQL)
        └── <entity>.py

tests/<context>/integration/
├── conftest.py
└── test_<type>_<name>_<gateway>.py
```

Wait for instructions.
