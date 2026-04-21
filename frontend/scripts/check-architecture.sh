#!/usr/bin/env bash
# Fast pre-flight guard for the frontend clean-architecture dependency rule.
#
# Invoked by .pre-commit-config.yaml. The authoritative enforcement lives in
# frontend/eslint.config.ts (no-restricted-imports with per-layer overrides),
# which CI runs via `bunx eslint .`. This grep-based guard is intentionally
# redundant — it's kept because it runs in a fraction of a second without
# needing node_modules, so pre-commit stays fast even on a fresh clone.
#
# If the ESLint rules change, keep this in sync.
#
# Rules:
#   domain/                       — zero framework imports
#   application/                  — imports only from domain/
#   infrastructure/in_memory/     — test fakes; no SDK, no Vue, no Pinia
#
# The script resolves its own directory so it works regardless of where
# it's invoked from (pre-commit runs from the repo root).

set -euo pipefail

cd "$(cd "$(dirname "$0")" && pwd)/.."

fail=0

# Tests sit alongside production code under __tests__/ folders. Unit
# specs legitimately reach into infrastructure/in_memory/ to instantiate
# fakes, so we exclude __tests__/ from the dependency-rule grep — the
# rule applies to production source only.
check_forbidden() {
  local layer="$1"
  shift
  local pattern
  for pattern in "$@"; do
    if grep -rnE --exclude-dir=__tests__ "from ['\"]${pattern}" "src/${layer}/" 2>/dev/null; then
      echo "❌ src/${layer}/ imports from ${pattern} (forbidden by dependency rule)"
      fail=1
    fi
  done
}

# domain/: nothing external
check_forbidden "domain" "@/client" "vue" "pinia" "@/application" "@/infrastructure"

# application/: only domain/
check_forbidden "application" "@/client" "vue" "pinia" "@/infrastructure"

# infrastructure/in_memory/: test fakes only
check_forbidden "infrastructure/in_memory" "@/client" "vue" "pinia"

if [ "$fail" -eq 0 ]; then
  echo "✅ Dependency rule respected: domain/application/in_memory stay framework-free"
  exit 0
fi
exit 1
