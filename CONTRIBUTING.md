# Contributing to Le Coffre

Thank you for considering contributing to Le Coffre! We welcome contributions of all kinds. Please follow these guidelines to ensure a smooth collaboration.

## Development Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Bun](https://bun.sh/) — JavaScript runtime and package manager

### Backend

```bash
cd server

# Install core dependencies (required)
uv sync

# Install with optional OpenTelemetry monitoring support
uv sync --group monitoring
```

The `monitoring` group is **optional**. The application runs fully without it — all observability features degrade gracefully to no-ops. Only install it if you are working on distributed tracing or metrics.

### Running the backend tests

```bash
# Without monitoring group — OTel-specific tests are skipped automatically
uv run pytest

# With monitoring group — full suite including OTel tests
uv sync --group monitoring
uv run pytest
```

### Frontend

```bash
cd frontend
bun install
bun run dev
```

## How to Contribute

1. **Fork the Repository**  
  Create a fork of the repository to your GitHub account.

2. **Clone Your Fork**  
  Clone your fork to your local machine:

  ```bash
  git clone https://github.com/<your-username>/le-coffre.git
  cd le-coffre
  ```

1. **Create a Branch**  
  Create a new branch for your changes:

  ```bash
  git checkout -b feat/my-feature-branch
  ```

1. **Make Your Changes**
  Implement your changes and commit them with clear and descriptive commit messages:

  ```bash
  git add .
  git commit -m "Add feature: my-feature"
  ```

1. **Push Your Changes**
  Push your changes to your fork:

  ```bash
  git push origin feat/my-feature-branch
  ```
  
1. **Create a Pull Request**
  Go to the original repository and create a pull request from your branch. Provide a clear description of your changes and why they are needed.

## Guidelines for Contributions

Issues: Before starting work, check if an issue already exists. If not, create one to discuss your idea.
Pull Requests: Ensure your pull request is focused on a single feature or fix. Avoid bundling unrelated changes.
Code Style: Follow the project's coding standards and conventions.
Tests: Add or update tests to cover your changes, if applicable.
Documentation: Update the documentation if your changes affect usage or functionality.
