// Run with: node --test .github/scripts/__tests__/*.test.mjs
//
// Pins the reading of `bun audit --json`. The previous script parsed the npm
// audit shape (`report.vulnerabilities[*].fixAvailable`), which bun never
// emits, so it printed "No vulnerabilities" over a critical CVE and could not
// fail. These samples are what bun 1.3.14 actually prints.
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { evaluateReport, formatAdvisories, loadAccepted } from '../check-bun-audit.mjs'

const BUN_SAMPLE = {
  minimist: [
    {
      id: 1096466,
      url: 'https://github.com/advisories/GHSA-xvch-5gv4-984h',
      title: 'Prototype Pollution in minimist',
      severity: 'critical',
      vulnerable_versions: '<0.2.4',
      cwe: ['CWE-1321'],
      cvss: { score: 9.8, vectorString: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H' },
    },
  ],
  undici: [
    {
      id: 1239933,
      url: 'https://github.com/advisories/GHSA-3wwx-pv8p-q78v',
      title: 'undici vulnerable to Denial of Service via unhandled error',
      severity: 'moderate',
      vulnerable_versions: '>=7.28.0 <7.29.1',
      cwe: ['CWE-248'],
      cvss: { score: 5.9, vectorString: 'CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:H' },
    },
  ],
}

describe('evaluateReport', () => {
  it('fails on a critical advisory at the default threshold', () => {
    const outcome = evaluateReport(BUN_SAMPLE)

    assert.equal(outcome.kind, 'fail')
    assert.deepEqual(
      outcome.failing.map((advisory) => [advisory.package, advisory.severity]),
      [['minimist', 'critical']],
    )
  })

  it('lists every advisory, not only the failing ones', () => {
    const outcome = evaluateReport(BUN_SAMPLE)

    assert.deepEqual(
      outcome.advisories.map((advisory) => [advisory.package, advisory.severity]),
      [
        ['minimist', 'critical'],
        ['undici', 'moderate'],
      ],
    )
  })

  it('passes when nothing reaches the threshold', () => {
    const outcome = evaluateReport({ undici: BUN_SAMPLE.undici }, 'high')

    assert.equal(outcome.kind, 'ok')
    assert.equal(outcome.failing.length, 0)
    assert.equal(outcome.advisories.length, 1)
  })

  it('honours a lower threshold', () => {
    const outcome = evaluateReport({ undici: BUN_SAMPLE.undici }, 'moderate')

    assert.equal(outcome.kind, 'fail')
  })

  it('treats an empty object as clean', () => {
    const outcome = evaluateReport({})

    assert.equal(outcome.kind, 'ok')
    assert.deepEqual(outcome.advisories, [])
  })

  it('treats an {"error": ...} body as "the audit did not run", not as clean', () => {
    // bun answers a registry failure with this shape on stdout. Reading it as
    // "no packages, no advisories" would turn an outage into a green tick.
    const outcome = evaluateReport({ error: 'audit request failed' })

    assert.equal(outcome.kind, 'unusable')
  })

  it('treats anything that is not an object keyed by package as unusable', () => {
    for (const body of [null, 'clean', 42, [], { pkg: [null] }, { pkg: ['x'] }]) {
      assert.equal(evaluateReport(body).kind, 'unusable', JSON.stringify(body))
    }
  })

  it('fails closed on a severity it does not know', () => {
    const outcome = evaluateReport({ pkg: [{ title: 'x', severity: 'catastrophic' }] })

    assert.equal(outcome.kind, 'fail')
  })

  it('refuses an unknown threshold instead of silently enforcing nothing', () => {
    assert.throws(() => evaluateReport({}, 'severe'), /Unknown audit level/)
  })
})

describe('accepted risks', () => {
  const ENTRY = {
    advisory: 'GHSA-xvch-5gv4-984h',
    package: 'minimist',
    reason: 'No fixed release exists and it only runs in the lint toolchain.',
    review_by: '2027-01-06',
  }

  it('reports an accepted advisory without failing on it', () => {
    const { active } = loadAccepted([ENTRY], '2026-10-06')
    const outcome = evaluateReport(BUN_SAMPLE, 'high', active)

    assert.equal(outcome.kind, 'ok')
    assert.equal(outcome.advisories.find((advisory) => advisory.package === 'minimist').accepted, true)
  })

  it('does not accept the same advisory reported against another package', () => {
    const { active } = loadAccepted([{ ...ENTRY, package: 'not-minimist' }], '2026-10-06')

    assert.equal(evaluateReport(BUN_SAMPLE, 'high', active).kind, 'fail')
  })

  it('stops honouring an entry past its review date, so the build goes red again', () => {
    const { active, expired } = loadAccepted([ENTRY], '2027-01-07')

    assert.deepEqual(active, [])
    assert.equal(expired.length, 1)
    assert.equal(evaluateReport(BUN_SAMPLE, 'high', active).kind, 'fail')
  })

  it('refuses a malformed entry instead of skipping it', () => {
    for (const broken of [
      { ...ENTRY, advisory: 'CVE-2026-1' },
      { ...ENTRY, package: '' },
      { ...ENTRY, reason: 'ok' },
      { ...ENTRY, review_by: 'soon' },
      null,
    ]) {
      assert.throws(() => loadAccepted([broken], '2026-10-06'), Error, JSON.stringify(broken))
    }
    assert.throws(() => loadAccepted({}, '2026-10-06'), /JSON array/)
  })

  it('validates the entries actually committed in the repository', async () => {
    const { readFileSync } = await import('node:fs')
    const entries = JSON.parse(readFileSync(new URL('../../bun-audit-accepted.json', import.meta.url), 'utf8'))

    assert.doesNotThrow(() => loadAccepted(entries, '2026-10-06'))
  })

  it('marks an accepted advisory in the printed report', () => {
    const { active } = loadAccepted([ENTRY], '2026-10-06')
    const outcome = evaluateReport(BUN_SAMPLE, 'high', active)

    assert.match(formatAdvisories(outcome.advisories, outcome.failing), /ok \[critical\] Prototype Pollution in minimist \(accepted/)
  })
})

describe('formatAdvisories', () => {
  it('groups by package, prints url and severity, and marks the failing ones', () => {
    const outcome = evaluateReport(BUN_SAMPLE)

    const text = formatAdvisories(outcome.advisories, outcome.failing)

    assert.match(text, /^minimist:\n {2}!! \[critical\] Prototype Pollution in minimist\n {7}https:/m)
    assert.match(text, /^undici:\n {5}\[moderate\] undici vulnerable/m)
  })
})

describe('the CLI wrapper', () => {
  it('reads empty stdout as "the audit did not run" and stays green with a warning', async () => {
    // The documented behaviour for an unreachable registry. Exercised through a
    // fake `bun` on PATH so the retry and annotation path is the real one.
    const { spawnSync } = await import('node:child_process')
    const { mkdtempSync, writeFileSync, chmodSync } = await import('node:fs')
    const { tmpdir } = await import('node:os')
    const { join } = await import('node:path')

    const bin = mkdtempSync(join(tmpdir(), 'fake-bun-'))
    writeFileSync(join(bin, 'bun'), '#!/bin/sh\nexit 1\n')
    chmodSync(join(bin, 'bun'), 0o755)

    const result = spawnSync(
      process.execPath,
      [new URL('../check-bun-audit.mjs', import.meta.url).pathname, bin],
      {
        encoding: 'utf8',
        env: { ...process.env, PATH: `${bin}:${process.env.PATH}`, BUN_AUDIT_BACKOFF_MS: '1' },
      },
    )

    assert.equal(result.status, 0, result.stdout + result.stderr)
    assert.match(result.stdout, /::warning title=Dependency audit skipped::/)
  })
})
