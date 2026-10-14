#!/usr/bin/env bash
# Fast pre-flight guard for the extension's dependency rules.
#
# Invoked by .pre-commit-config.yaml. The authoritative enforcement lives in
# extension/eslint.config.ts, which CI runs via `bunx eslint .`. This grep-based
# guard is intentionally redundant, it runs in a fraction of a second without
# needing node_modules, so pre-commit stays fast even on a fresh clone.
#
# If the ESLint rules change, keep this in sync.
#
# Rules:
#   domain/                     pure TypeScript: no Vue, no Zod, no api/, no platform/
#   popup/                      never calls the API; everything goes through the worker
#   everywhere but
#   platform/chrome/            no chrome.* / browser.* globals (the Firefox seam)

set -euo pipefail

cd "$(cd "$(dirname "$0")" && pwd)/.."

fail=0

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
check_forbidden "domain" "vue" "zod" "@/api" "@/platform"

# popup/: no direct API access, send a message to the service worker instead
check_forbidden "popup" "@/api"

# The Firefox seam. src/offscreen/ is exempt alongside src/platform/chrome/:
# it is itself a browser-specific adapter (a Chrome-only offscreen document).
#
# Only `chrome.` is grepped, not `browser.`: `browser` is the conventional local
# name for a Browser-port instance, and a local binding shadows the global, so a
# grep cannot tell the two apart. ESLint's no-restricted-globals resolves scopes
# properly and is the authoritative check for that half of the rule.
#
# Comment lines are stripped first, this file and browser.ts both discuss
# `chrome.*` in prose, and flagging documentation would train people to ignore
# the guard.
offenders=$(
  grep -rn --exclude-dir=__tests__ --exclude-dir=chrome --exclude-dir=offscreen \
    -E '(^|[^.[:alnum:]_"'"'"'])chrome\.' src/ 2>/dev/null |
    grep -vE '^[^:]+:[0-9]+:[[:space:]]*(//|\*|/\*)' || true
)
if [ -n "$offenders" ]; then
  echo "$offenders"
  echo "❌ chrome.* used outside src/platform/chrome/ (breaks the Firefox seam)"
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "✅ Dependency rules respected: domain is pure, popup has no network, chrome.* is contained"
  exit 0
fi
exit 1
