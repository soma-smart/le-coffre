// Pinned so the browser's own locale never leaks in: an undefined locale would
// drop "dans 24 heures" into an otherwise English screen. en-GB rather than
// en-US because it is English while using a 24-hour clock and a day-first date
// natively, so no per-call option has to override the locale's own convention.
const LOCALE = 'en-GB'

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['day', 86_400_000],
  ['hour', 3_600_000],
  ['minute', 60_000],
]

/**
 * Renders an instant as a duration from now, e.g. "in 24 hours" or "3 minutes ago".
 *
 * Absolute timestamps read badly for lifetimes: a link created at 14:37 with a
 * 24-hour lifetime shows "7/22/2026, 2:37 PM", and at 14:40 the eye catches the
 * time, misses the date and concludes the link has already expired. A duration
 * cannot be misread that way.
 *
 * `numeric: 'always'` keeps "in 1 day" rather than "tomorrow", which is what you
 * want when the point is how much time is left, not which calendar day it is.
 */
export const formatRelativeTime = (isoDate: string, now: Date = new Date()): string => {
  const target = new Date(isoDate)
  if (Number.isNaN(target.getTime())) return ''

  const diffMs = target.getTime() - now.getTime()
  const formatter = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'always' })

  for (const [unit, unitMs] of UNITS) {
    if (Math.abs(diffMs) >= unitMs) {
      return formatter.format(Math.round(diffMs / unitMs), unit)
    }
  }
  return formatter.format(Math.round(diffMs / 1000), 'second')
}

const ABSOLUTE_FORMAT: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: 'short',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
}

/** Full timestamp, for the tooltip behind the relative label. */
export const formatAbsoluteTime = (isoDate: string): string => {
  const target = new Date(isoDate)
  return Number.isNaN(target.getTime()) ? '' : target.toLocaleString(LOCALE, ABSOLUTE_FORMAT)
}
