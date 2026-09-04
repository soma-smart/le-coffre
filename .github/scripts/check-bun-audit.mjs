#!/usr/bin/env node
/**
 * Fail CI on dependency vulnerabilities that have a fix available.
 *
 * `bun.lock` is the only lockfile in this repository, and GitHub's dependency
 * graph does not read it, so Dependabot alerts do not cover `frontend/` or
 * `extension/`. This step is what catches vulnerabilities in them.
 *
 * Two failures have to stay distinguishable, which is the whole reason this is
 * a script and not an inline heredoc:
 *
 *   - the audit ran and found something fixable, which must fail the build
 *   - the audit could not run at all, most often `ConnectionClosed: audit
 *     request failed` when the advisory API is unreachable
 *
 * The previous inline version redirected stdout to a file, swallowed the exit
 * code with `|| true`, then parsed the empty file, so an unreachable registry
 * failed the job with a JSON.parse stack trace pointing at nothing. A build
 * that goes red on registry availability teaches people to re-run CI until it
 * is green, which is worse for security than saying plainly that the check did
 * not run. So an unreachable audit is retried, then reported as a warning
 * annotation on the run.
 *
 * Usage: node .github/scripts/check-bun-audit.mjs [package-directory]
 */
import { spawnSync } from 'node:child_process'
import { setTimeout as sleep } from 'node:timers/promises'

const ATTEMPTS = 3
const BACKOFF_MS = 5_000
// Without this a hung audit holds the runner until the job timeout, hours
// later. A stalled attempt is just another attempt that produced no report.
const TIMEOUT_MS = 120_000
const cwd = process.argv[2] ?? process.cwd()

/** Returns the parsed report, or null when the audit itself could not run. */
function audit() {
  // A non-zero exit is expected: `bun audit` uses it to report findings, and
  // the JSON is on stdout either way. Only unparsable output means failure.
  const result = spawnSync('bun', ['audit', '--json'], {
    cwd,
    encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024,
    timeout: TIMEOUT_MS,
  })

  if (result.signal) {
    console.log(`bun audit was killed after ${TIMEOUT_MS / 1000}s (${result.signal})`)
    return null
  }

  const stdout = (result.stdout ?? '').trim()
  if (!stdout) {
    console.log((result.stderr ?? '').trim() || `bun audit produced no output (${result.status})`)
    return null
  }

  try {
    return JSON.parse(stdout)
  } catch {
    console.log('bun audit produced output that is not JSON:')
    console.log(stdout.slice(0, 2_000))
    return null
  }
}

let report = null
for (let attempt = 1; attempt <= ATTEMPTS && report === null; attempt += 1) {
  if (attempt > 1) {
    console.log(`Retrying (${attempt}/${ATTEMPTS})...`)
    await sleep(BACKOFF_MS)
  }
  report = audit()
}

if (report === null) {
  // Unreachable is not the same as clean, and this line is what keeps the
  // difference visible on the run summary instead of a silent green tick.
  console.log(`::warning title=Dependency audit skipped::bun audit could not run in ${cwd} after ${ATTEMPTS} attempts. Dependencies were NOT checked.`)
  process.exit(0)
}

const vulnerabilities = Object.values(report.vulnerabilities ?? {})
const fixable = vulnerabilities.filter((v) => v.fixAvailable !== false && v.fixAvailable != null)

if (fixable.length > 0) {
  console.log('❌ Vulnerabilities with available fixes:')
  for (const v of fixable) {
    console.log(`  ${v.name}: ${v.severity} (fix: ${JSON.stringify(v.fixAvailable)})`)
  }
  process.exit(1)
}

console.log('✅ No vulnerabilities with available fixes (any unfixable vulnerabilities are ignored)')
