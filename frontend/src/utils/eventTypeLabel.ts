import { humanizeEventType } from '@/domain/password/Password'

/**
 * Translates an audit event type for display, falling back to the domain's
 * generic humanization for any event type not (yet) in the translation
 * tables — so a new backend event type degrades instead of breaking.
 */
export function translateEventType(t: (key: string) => string, eventType: string): string {
  const key = `common.eventTypes.${eventType}`
  const translated = t(key)
  return translated === key ? humanizeEventType(eventType) : translated
}
