import { afterEach, describe, expect, it } from 'vitest'
import i18n from '@/i18n'
import { formatAbsoluteTime, formatRelativeTime } from '@/utils/relativeTime'

const NOW = new Date('2026-07-21T12:40:00Z')

afterEach(() => {
  i18n.global.locale.value = 'fr'
})

describe('formatRelativeTime', () => {
  it('reads a 24-hour link as a full day away, not as a past time', () => {
    // The reported confusion: a link created at 14:37 local with the default
    // 24-hour lifetime rendered "7/22/2026, 2:37 PM". At 14:40 the eye caught
    // "2:37" and concluded it had expired, missing that the date was tomorrow.
    const expiresAt = '2026-07-22T12:37:00Z'

    // Just under 24h of remaining time, so hours rather than days: "dans 24
    // heures" says the same thing more precisely than "demain" would.
    expect(formatRelativeTime(expiresAt, NOW)).toBe('dans 24 heures')
  })

  it('uses hours and minutes for shorter lifetimes', () => {
    expect(formatRelativeTime('2026-07-21T15:40:00Z', NOW)).toBe('dans 3 heures')
    expect(formatRelativeTime('2026-07-21T13:25:00Z', NOW)).toBe('dans 45 minutes')
  })

  it('renders past instants as elapsed time', () => {
    expect(formatRelativeTime('2026-07-21T12:35:00Z', NOW)).toBe('il y a 5 minutes')
    expect(formatRelativeTime('2026-07-20T12:40:00Z', NOW)).toBe('il y a 1 jour')
  })

  it('falls back to seconds just either side of now', () => {
    expect(formatRelativeTime('2026-07-21T12:40:30Z', NOW)).toBe('dans 30 secondes')
    expect(formatRelativeTime('2026-07-21T12:39:30Z', NOW)).toBe('il y a 30 secondes')
  })

  it('switches to English when the UI locale is English', () => {
    i18n.global.locale.value = 'en'

    expect(formatRelativeTime('2026-07-22T12:37:00Z', NOW)).toBe('in 24 hours')
    expect(formatRelativeTime('2026-07-21T12:35:00Z', NOW)).toBe('5 minutes ago')
  })

  it('follows the active UI locale rather than the browser locale', () => {
    // A hardcoded or undefined locale would drift from the language the rest
    // of the screen renders in, so assert the locale the formatter is built
    // with rather than just the string it happens to produce.
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
      formatRelativeTime('2026-07-22T12:37:00Z', NOW)
      i18n.global.locale.value = 'en'
      formatRelativeTime('2026-07-22T12:37:00Z', NOW)

      expect(localesUsed).toEqual(['fr', 'en-GB'])
    } finally {
      intl.RelativeTimeFormat = original
    }
  })

  it('renders the English tooltip on a 24-hour clock, with no AM/PM', () => {
    // English resolves to en-GB rather than en-US: it is English while using a
    // 24-hour clock and a day-first date natively, so this needs no hour12
    // override. Falling back to en-US would silently reintroduce AM/PM.
    i18n.global.locale.value = 'en'
    const absolute = formatAbsoluteTime('2026-07-22T12:37:00Z')

    expect(absolute).not.toMatch(/AM|PM/)
    expect(absolute).toContain('2026')
  })

  it('returns an empty string rather than "Invalid Date" for junk input', () => {
    expect(formatRelativeTime('not-a-date', NOW)).toBe('')
    expect(formatAbsoluteTime('not-a-date')).toBe('')
  })
})
