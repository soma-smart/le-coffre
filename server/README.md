# Le-Coffre backend

## Start the backend

- install uv
```bash
pip install uv
```

- install the dependencies
```bash
uv sync
```

- run the server
```bash
uv run fastapi dev src/main.py
```

## Run the tests

To have the tests run automatically on file changes, you can use the `ptw` command:
```bash
uv run ptw .
```

Or classic pytest:
```bash
uv run pytest
```
