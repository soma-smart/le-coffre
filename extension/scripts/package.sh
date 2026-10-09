#!/usr/bin/env bash
# Build the extension and zip it for the Chrome Web Store.
#
# Two traps this script exists to close:
#
#   1. The store wants a ZIP whose ROOT is manifest.json, not a folder that
#      contains it. Uploading a zip of the `dist/` directory itself is rejected
#      with "manifest file is missing", the most common first-submission
#      mistake. Hence the `cd dist` before every writer below.
#   2. It builds first, always. `bun run build` chains vue-tsc, vite build and
#      validate-manifest.ts, so what ships is what those three approved.
#      Zipping a stale dist/ is how a debug build reaches a store review.
#
# No zip writer is available everywhere: this devcontainer has neither `zip`
# nor `bsdtar`, GitHub runners have `zip` and `python3`, macOS has `bsdtar`
# as its `tar`. So three are tried in order rather than assuming one.
#
# Source maps are included on purpose. The code is MIT and already public, the
# store forbids obfuscated code, and a reviewer who can read the bundle asks
# fewer questions. `sourcemap: true` in vite.config.ts is what produces them.

set -euo pipefail

cd "$(cd "$(dirname "$0")" && pwd)/.."

manifest_version=$(bun --print 'require("./manifest.json").version')
package_version=$(bun --print 'require("./package.json").version')

# Only the manifest version reaches users, and only package.json version is
# what a `bun pm` command shows. Bumping one and forgetting the other publishes
# an update whose number does not match anything in the repository.
if [ "$manifest_version" != "$package_version" ]; then
  echo "❌ version mismatch: manifest.json is $manifest_version, package.json is $package_version"
  echo "   Both must agree before packaging; only the manifest one reaches the store."
  exit 1
fi

archive="le-coffre-extension-${manifest_version}.zip"

bun run build

rm -f "$archive"

if command -v zip >/dev/null 2>&1; then
  (cd dist && zip -q -r -X "../${archive}" .)
elif command -v bsdtar >/dev/null 2>&1; then
  bsdtar -a -c -f "$archive" -C dist .
elif command -v python3 >/dev/null 2>&1; then
  (cd dist && python3 -m zipfile -c "../${archive}" .)
else
  echo "❌ no zip writer found. Install one of: zip, bsdtar, python3"
  exit 1
fi

# Cheap proof that trap 1 did not reopen: the manifest has to be at the root.
if command -v python3 >/dev/null 2>&1; then
  if ! python3 -m zipfile -l "$archive" | grep -qE '^manifest\.json[[:space:]]'; then
    echo "❌ ${archive} has no manifest.json at its root, the store would reject it"
    exit 1
  fi
fi

size=$(du -h "$archive" | cut -f1)
echo "✅ ${archive} (${size}), manifest at the root, ready to upload"
echo "   Upload it at https://chrome.google.com/webstore/devconsole"
