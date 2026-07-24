import { describe, expect, it } from 'vitest'
import { formatAbsoluteTime, formatRelativeTime } from '@/utils/relativeTime'

const NOW = new Date('2026-07-21T12:40:00Z')

describe('formatRelativeTime', () => {
  it('reads a 24-hour link as a full day away, not as a past time', () => {
    // The reported confusion: a link created at 14:37 local with the default
    // 24-hour lifetime rendered "7/22/2026, 2:37 PM". At 14:40 the eye caught
    // "2:37" and concluded it had expired, missing that the date was tomorrow.
    const expiresAt = '2026-07-22T12:37:00Z'

    // Just under 24h of remaining time, so hours rather than days: "in 24 hours"
    // says the same thing more precisely than "in 1 day" would.
    expect(formatRelativeTime(expiresAt, NOW)).toBe('in 24 hours')
  })

  it('uses hours and minutes for shorter lifetimes', () => {
    expect(formatRelativeTime('2026-07-21T15:40:00Z', NOW)).toBe('in 3 hours')
    expect(formatRelativeTime('2026-07-21T13:25:00Z', NOW)).toBe('in 45 minutes')
  })

  it('renders past instants as elapsed time', () => {
    expect(formatRelativeTime('2026-07-21T12:35:00Z', NOW)).toBe('5 minutes ago')
    expect(formatRelativeTime('2026-07-20T12:40:00Z', NOW)).toBe('1 day ago')
  })

  it('falls back to seconds just either side of now', () => {
    expect(formatRelativeTime('2026-07-21T12:40:30Z', NOW)).toBe('in 30 seconds')
    expect(formatRelativeTime('2026-07-21T12:39:30Z', NOW)).toBe('30 seconds ago')
  })

  it('stays English whatever the browser locale is', () => {
    // Without a pinned locale this follows the browser and renders "dans 24
    // heures" in an interface that is English everywhere else. A reviewer on an
    // English browser would never see the regression, so assert the locale the
    // formatter is built with rather than the string it happens to produce.
    const intl = Intl as unknown as { RelativeTimeFormat: typeof Intl.RelativeTimeFormat }
    const original = intl.RelativeTimeFormat
    const localesUsed: unknown[] = []
    intl.RelativeTimeFormat = function (
      locale?: Intl.LocalesArgument,
      options?: Intl.RelativeTimeFormatOptions,
    ) {
      localesUsed.push(locale)
      return new original(locale, options)
    } as unknown as typeof Intl.RelativeTimeFormat

    try {
      expect(formatRelativeTime('2026-07-22T12:37:00Z', NOW)).toBe('in 24 hours')
      expect(localesUsed).toEqual(['en-GB'])
    } finally {
      intl.RelativeTimeFormat = original
    }
  })

  it('renders the tooltip on a 24-hour clock, with no AM/PM', () => {
    // en-GB is English and 24-hour natively, so this needs no hour12 override.
    // Falling back to en-US would silently reintroduce the AM/PM suffix.
    const absolute = formatAbsoluteTime('2026-07-22T12:37:00Z')

    expect(absolute).not.toMatch(/AM|PM/)
    expect(absolute).toContain('2026')
  })

  it('returns an empty string rather than "Invalid Date" for junk input', () => {
    expect(formatRelativeTime('not-a-date', NOW)).toBe('')
    expect(formatAbsoluteTime('not-a-date')).toBe('')
  })
})
