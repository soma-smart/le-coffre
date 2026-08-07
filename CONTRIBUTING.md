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

## Dependency updates

**`frontend/bun.lock` is the only frontend lockfile.** CI and `frontend/Dockerfile` work from it — never add a `package-lock.json` alongside it, or Dependabot will start updating that one instead and leave `bun.lock` behind.

If you edit `frontend/package.json` by hand, regenerate the lockfile in the same commit, or every frontend job fails with `lockfile had changes, but lockfile is frozen`:

```bash
cd frontend && bun install && git add bun.lock
```

Dependabot does **not** do this for you: it bumps `frontend/package.json` and leaves the lockfile behind. The `dependabot-lockfile.yml` workflow covers that gap — on any Dependabot PR touching `frontend/package.json` it runs `bun install` and pushes the regenerated `bun.lock`, which retriggers `front-ci` to validate the result. It authenticates with a `GH_PAT` stored as a **Dependabot** secret; Dependabot-triggered workflows cannot read Actions secrets, so the two stores must both hold the token.

You can also start it by hand on any PR whose diff touches `frontend/package.json`:

- **Add the `regenerate-lockfile` label** to the PR. This is the only route that works while the workflow itself is still under review, because a `pull_request` run uses the workflow file from the PR branch.
- **Actions → Dependabot lockfile → Run workflow**, passing a PR number. GitHub only offers `workflow_dispatch` for workflows already on the default branch, so this becomes available once the workflow is merged. It refuses to run against the default branch.

The bun version is pinned by `packageManager` in `frontend/package.json`. `setup-bun` reads it via `bun-version-file`, and `frontend/Dockerfile` plus `Dockerfile.dev` hardcode the matching version — keep all three in step when bumping, otherwise a `bun.lock` written by one can fail `--frozen-lockfile` in another.

The backend works the same way: Dependabot's uv updates keep `server/uv.lock` in step with `pyproject.toml`. If they ever disagree, run `cd server && uv lock`.

One consequence of having no `package-lock.json`: GitHub's dependency graph does not read `bun.lock`, so frontend dependencies do not appear there and Dependabot **alerts** do not cover them. Vulnerability detection comes from CI instead — `bun audit` runs against the full transitive tree in the `front-ci` job and fails the build on anything with a fix available, and `release.yml` scans the built frontend image with grype.

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
