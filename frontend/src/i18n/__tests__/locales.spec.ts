import { describe, expect, it } from 'vitest'
import fr from '../locales/fr.json'
import en from '../locales/en.json'

type Messages = { [key: string]: string | Messages }

const locales: Record<string, Messages> = { fr, en }

/** Dotted paths to every leaf string in a messages tree, e.g. "auth.login.title". */
function leafKeys(messages: Messages, prefix = ''): string[] {
  return Object.entries(messages).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return typeof value === 'string' ? [path] : leafKeys(value, path)
  })
}

function valueAt(messages: Messages, path: string): unknown {
  return path.split('.').reduce<unknown>((node, segment) => {
    return node && typeof node === 'object' ? (node as Messages)[segment] : undefined
  }, messages)
}

describe('i18n locales', () => {
  const keysByLocale = Object.fromEntries(
    Object.entries(locales).map(([name, messages]) => [name, new Set(leafKeys(messages))]),
  )
  const allKeys = new Set(Object.values(keysByLocale).flatMap((keys) => [...keys]))

  it.each(Object.keys(locales))('%s.json has every key present in the other locales', (name) => {
    const keys = keysByLocale[name]
    const missing = [...allKeys].filter((key) => !keys.has(key)).sort()

    // A key missing here but present elsewhere means either a translation was
    // never added, or the JSON shape diverged (a string in one locale, a
    // nested object at the same path in another) — leafKeys() surfaces both
    // as a path mismatch.
    expect(missing).toEqual([])
  })

  it.each(Object.keys(locales))('%s.json has no empty translation values', (name) => {
    const messages = locales[name]
    const empty = leafKeys(messages).filter((key) => (valueAt(messages, key) as string).trim() === '')

    expect(empty).toEqual([])
  })

  it('uses the same {placeholder} names for a given key across locales', () => {
    const placeholder = /\{(\w+)\}/g
    const namesIn = (value: string) => new Set([...value.matchAll(placeholder)].map((m) => m[1]))

    const mismatches: string[] = []
    for (const key of allKeys) {
      const namesByLocale = Object.entries(locales).map(([name, messages]) => {
        const value = valueAt(messages, key)
        return { name, names: typeof value === 'string' ? namesIn(value) : new Set<string>() }
      })

      const [first, ...rest] = namesByLocale
      const isMismatched = rest.some(
        (entry) =>
          entry.names.size !== first.names.size || [...first.names].some((n) => !entry.names.has(n)),
      )
      if (isMismatched) {
        const summary = namesByLocale.map((e) => `${e.name}=[${[...e.names].join(',')}]`).join(' ')
        mismatches.push(`${key}: ${summary}`)
      }
    }

    // A placeholder present in one locale's message but not another's is
    // usually a typo (e.g. {relative} vs {relatve}) — t() would silently
    // render the literal "{relative}" instead of interpolating it.
    expect(mismatches).toEqual([])
  })
})
