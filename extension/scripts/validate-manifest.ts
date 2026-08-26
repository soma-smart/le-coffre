/**
 * Validate a built extension directory before it can ship.
 *
 * Run as `bun run scripts/validate-manifest.ts dist`, from `bun run build` and
 * from the `extension-ci` job. Two classes of failure are caught here because
 * neither shows up in tests and both are expensive to discover later:
 *
 *  1. A permission escalation that nobody reviewed, above all a non-empty
 *     `host_permissions`, which would turn the install prompt into "Read and
 *     change all your data on all websites". For a password manager that is the
 *     worst possible trust signal, and it is one careless line away at all
 *     times. The permission allowlist below is deliberately annoying: widening
 *     it requires editing this file in the same PR, where a reviewer sees it.
 *
 *  2. Bundle output that MV3's `script-src 'self'` will refuse at runtime:
 *     inline <script> or eval(). Both work in `vite preview` and both render a
 *     blank popup in Chrome, with no build-time error.
 */
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

/** Permissions this extension is allowed to declare. Widen only with review. */
const ALLOWED_PERMISSIONS = new Set(['storage', 'alarms', 'offscreen', 'clipboardWrite'])

/** Host patterns allowed as *optional* permissions, requested at runtime. */
const ALLOWED_OPTIONAL_HOSTS = new Set(['https://*/*', 'http://*/*'])

const errors: string[] = []

function fail(message: string): void {
  errors.push(message)
}

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const full = join(dir, entry)
    return statSync(full).isDirectory() ? walk(full) : [full]
  })
}

const distArg = process.argv[2]
if (!distArg) {
  console.error('usage: validate-manifest.ts <dist-dir>')
  process.exit(2)
}
const dist = resolve(distArg)

if (!existsSync(dist)) {
  console.error(`✗ ${distArg} does not exist, run \`bun run build-only\` first`)
  process.exit(2)
}

// ── manifest ────────────────────────────────────────────────────────────────

const manifestPath = join(dist, 'manifest.json')
if (!existsSync(manifestPath)) {
  console.error(`✗ no manifest.json in ${distArg}`)
  process.exit(2)
}

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))

if (manifest.manifest_version !== 3) {
  fail(`manifest_version must be 3, found ${JSON.stringify(manifest.manifest_version)}`)
}

// The one that matters most.
if (Array.isArray(manifest.host_permissions) && manifest.host_permissions.length > 0) {
  fail(
    `host_permissions must stay empty, found ${JSON.stringify(manifest.host_permissions)}. ` +
      'The vault origin is arbitrary per install and must be requested at runtime ' +
      'via optional_host_permissions + chrome.permissions.request().',
  )
}

for (const permission of manifest.permissions ?? []) {
  if (!ALLOWED_PERMISSIONS.has(permission)) {
    fail(
      `permission "${permission}" is not in the reviewed allowlist ` +
        `(${[...ALLOWED_PERMISSIONS].join(', ')}). Add it to ALLOWED_PERMISSIONS in this file ` +
        'in the same PR so it gets reviewed.',
    )
  }
}

for (const host of manifest.optional_host_permissions ?? []) {
  if (!ALLOWED_OPTIONAL_HOSTS.has(host)) {
    fail(`optional_host_permissions entry "${host}" is not in the reviewed allowlist`)
  }
}

// Chrome accepts 1-4 dot-separated integers, each 0-65535. A `-rc1` suffix is
// rejected at upload time, which is the first RC tag, which is a bad time.
const version = String(manifest.version ?? '')
const parts = version.split('.')
if (
  parts.length < 1 ||
  parts.length > 4 ||
  !parts.every((p) => /^\d+$/.test(p) && Number(p) <= 65535)
) {
  fail(`version "${version}" must be 1-4 dot-separated integers, each <= 65535`)
}

// Every path the manifest names must actually be in the bundle.
const referenced = [
  manifest.background?.service_worker,
  manifest.action?.default_popup,
  ...Object.values(manifest.icons ?? {}),
  ...Object.values(manifest.action?.default_icon ?? {}),
].filter((value): value is string => typeof value === 'string')

for (const path of referenced) {
  if (!existsSync(join(dist, path))) {
    fail(`manifest references "${path}", which is not present in ${distArg}`)
  }
}

// ── CSP smoke check ─────────────────────────────────────────────────────────

const files = walk(dist)

for (const file of files.filter((f) => f.endsWith('.html'))) {
  const html = readFileSync(file, 'utf8')
  // A <script> tag with no src= is inline, and `script-src 'self'` blocks it.
  const inline = [...html.matchAll(/<script\b([^>]*)>/gi)].filter(
    (match) => !/\bsrc\s*=/i.test(match[1]),
  )
  if (inline.length > 0) {
    fail(
      `${relative(dist, file)} contains ${inline.length} inline <script> tag(s), which MV3's ` +
        "script-src 'self' blocks. Check that build.modulePreload is false in vite.config.ts.",
    )
  }
}

for (const file of files.filter((f) => f.endsWith('.js'))) {
  const js = readFileSync(file, 'utf8')
  // Word-boundary matches, so `evaluate(` and `.eval_` don't trip it.
  if (/\beval\s*\(/.test(js) || /\bnew\s+Function\s*\(/.test(js)) {
    fail(
      `${relative(dist, file)} uses eval() or new Function(), which MV3 forbids. ` +
        'A runtime-compiled Vue template is the usual cause.',
    )
  }
}

// ── report ──────────────────────────────────────────────────────────────────

if (errors.length > 0) {
  console.error(`✗ ${distArg} failed validation:\n`)
  for (const error of errors) {
    console.error(`  • ${error}`)
  }
  console.error('')
  process.exit(1)
}

console.log(
  `✓ ${distArg} validated, manifest v3, ${(manifest.permissions ?? []).length} reviewed ` +
    `permission(s), no host_permissions, no inline scripts, no eval`,
)
