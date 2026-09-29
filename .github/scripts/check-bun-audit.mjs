#!/usr/bin/env node
/**
 * Fail CI on dependency vulnerabilities at or above a severity threshold.
 *
 * `bun.lock` is the only lockfile in this repository, and GitHub's dependency
 * graph does not read it, so Dependabot alerts do not cover `frontend/` or
 * `extension/`. This step is what catches vulnerabilities in them.
 *
 * `bun audit --json` (1.3.14) prints one object on stdout, keyed by package
 * name, each value an array of advisories:
 *
 *   {"<pkg>": [{"id", "url", "title", "severity", "vulnerable_versions", ...}]}
 *
 * and exits 1 when that object is not empty. Bun says nothing about whether a
 * fix exists, so "fail only when a fix is available" cannot be expressed; the
 * rule is severity instead. Every advisory is printed, grouped by package, and
 * the build fails when any of them is at or above BUN_AUDIT_LEVEL (default
 * `high`). A severity this script does not know counts as failing rather than
 * as ignorable. `--audit-level` and `--ignore` are not used: both proved
 * unreliable in JSON mode on 1.3.14.
 *
 * Two failures have to stay distinguishable, which is the whole reason this is
 * a script and not an inline heredoc:
 *
 *   - the audit ran and found something at or above the threshold, which must
 *     fail the build
 *   - the audit could not run at all, most often `ConnectionClosed: audit
 *     request failed` when the advisory API is unreachable, or an
 *     `{"error": ...}` body instead of the report
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
 *   BUN_AUDIT_LEVEL=low|moderate|high|critical   (default: high)
 *
 * `evaluateReport` is exported for `node --test`; the process only runs the
 * audit when this file is the entry point.
 */
import { spawnSync } from 'node:child_process'
import { setTimeout as sleep } from 'node:timers/promises'
import { fileURLToPath } from 'node:url'

const ATTEMPTS = 3
// Overridable so the test suite can exercise the retry path in milliseconds.
const BACKOFF_MS = Number(process.env.BUN_AUDIT_BACKOFF_MS ?? 5_000)
// Without this a hung audit holds the runner until the job timeout, hours
// later. A stalled attempt is just another attempt that produced no report.
const TIMEOUT_MS = 120_000
const DEFAULT_LEVEL = 'high'

/** Lowest to highest, as bun (and npm before it) name them. */
export const SEVERITY_LEVELS = ['info', 'low', 'moderate', 'high', 'critical']

function rank(severity) {
  const index = SEVERITY_LEVELS.indexOf(String(severity).toLowerCase())
  // Fail closed: a severity this script has never seen is not a reason to
  // wave the advisory through.
  return index === -1 ? SEVERITY_LEVELS.length : index
}

/**
 * Decide what a parsed `bun audit --json` report means.
 *
 * Returns one of:
 *   { kind: 'unusable', reason }             the body is not an audit report
 *   { kind: 'ok', advisories, failing: [] }  nothing at or above the threshold
 *   { kind: 'fail', advisories, failing }    at least one advisory is
 *
 * `advisories` is every advisory found, flattened and sorted by package, each
 * as { package, id, severity, title, url }. A report is usable only when it is
 * a plain object whose every value is an array of advisory objects; `{"error":
 * "..."}`, arrays, strings and null are all "the audit did not run".
 */
export function evaluateReport(report, level = DEFAULT_LEVEL) {
  if (!SEVERITY_LEVELS.includes(level)) {
    throw new Error(`Unknown audit level "${level}", expected one of ${SEVERITY_LEVELS.join(', ')}`)
  }

  if (report === null || typeof report !== 'object' || Array.isArray(report)) {
    return { kind: 'unusable', reason: 'the report is not an object keyed by package' }
  }

  const advisories = []
  for (const [name, entries] of Object.entries(report)) {
    if (!Array.isArray(entries)) {
      return { kind: 'unusable', reason: `"${name}" does not hold a list of advisories` }
    }
    for (const entry of entries) {
      if (entry === null || typeof entry !== 'object' || Array.isArray(entry)) {
        return { kind: 'unusable', reason: `"${name}" holds an advisory that is not an object` }
      }
      advisories.push({
        package: name,
        id: entry.id ?? null,
        severity: typeof entry.severity === 'string' ? entry.severity.toLowerCase() : 'unknown',
        title: entry.title ?? '(untitled advisory)',
        url: entry.url ?? null,
      })
    }
  }

  advisories.sort((left, right) => left.package.localeCompare(right.package))
  const threshold = rank(level)
  const failing = advisories.filter((advisory) => rank(advisory.severity) >= threshold)

  return { kind: failing.length > 0 ? 'fail' : 'ok', advisories, failing }
}

/** Every advisory, grouped by package, with the ones over the threshold marked. */
export function formatAdvisories(advisories, failing) {
  const lines = []
  const overThreshold = new Set(failing)
  let current = null
  for (const advisory of advisories) {
    if (advisory.package !== current) {
      current = advisory.package
      lines.push(`${current}:`)
    }
    const marker = overThreshold.has(advisory) ? '!!' : '  '
    lines.push(`  ${marker} [${advisory.severity}] ${advisory.title}`)
    if (advisory.url) lines.push(`       ${advisory.url}`)
  }
  return lines.join('\n')
}

/** Returns the parsed report, or null when the audit itself could not run. */
function audit(cwd) {
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

async function main() {
  const cwd = process.argv[2] ?? process.cwd()
  const level = process.env.BUN_AUDIT_LEVEL || DEFAULT_LEVEL
  if (!SEVERITY_LEVELS.includes(level)) {
    console.log(`::error::BUN_AUDIT_LEVEL must be one of ${SEVERITY_LEVELS.join(', ')}, got "${level}"`)
    process.exit(2)
  }

  let outcome = null
  for (let attempt = 1; attempt <= ATTEMPTS && outcome === null; attempt += 1) {
    if (attempt > 1) {
      console.log(`Retrying (${attempt}/${ATTEMPTS})...`)
      await sleep(BACKOFF_MS)
    }
    const report = audit(cwd)
    if (report === null) continue
    const evaluated = evaluateReport(report, level)
    if (evaluated.kind === 'unusable') {
      console.log(`bun audit did not return a report: ${evaluated.reason}`)
      console.log(JSON.stringify(report).slice(0, 2_000))
      continue
    }
    outcome = evaluated
  }

  if (outcome === null) {
    // Unreachable is not the same as clean, and this line is what keeps the
    // difference visible on the run summary instead of a silent green tick.
    console.log(`::warning title=Dependency audit skipped::bun audit could not run in ${cwd} after ${ATTEMPTS} attempts. Dependencies were NOT checked.`)
    process.exit(0)
  }

  if (outcome.advisories.length === 0) {
    console.log('✅ No known vulnerabilities')
    return
  }

  console.log(`${outcome.advisories.length} advisories found (threshold: ${level}, "!!" marks the ones at or above it):`)
  console.log(formatAdvisories(outcome.advisories, outcome.failing))

  if (outcome.kind === 'fail') {
    console.log(`❌ ${outcome.failing.length} advisories at or above "${level}"`)
    process.exit(1)
  }

  console.log(`✅ Nothing at or above "${level}" (lower severities are reported, not enforced)`)
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  await main()
}
