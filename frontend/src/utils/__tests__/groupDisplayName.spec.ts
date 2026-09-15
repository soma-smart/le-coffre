import { describe, expect, it } from 'vitest'
import { translateGroupName } from '../groupDisplayName'

describe('translateGroupName', () => {
  const t = (key: string, params?: Record<string, unknown>) => {
    if (key === 'common.personalGroupName') return `Groupe personnel de ${params?.username}`
    return key
  }

  it('translates a personal group name matching the backend pattern', () => {
    expect(translateGroupName(t, "malvergnat's Personal Group", true)).toBe(
      'Groupe personnel de malvergnat',
    )
  })

  it('translates a personal group name even without the isPersonal flag, based on the pattern alone', () => {
    expect(translateGroupName(t, "malvergnat's Personal Group")).toBe(
      'Groupe personnel de malvergnat',
    )
  })

  it('never touches a shared group name, even one that happens to match the pattern', () => {
    expect(translateGroupName(t, "malvergnat's Personal Group", false)).toBe(
      "malvergnat's Personal Group",
    )
  })

  it('leaves a shared, free-form group name unchanged', () => {
    expect(translateGroupName(t, 'Team Marketing', false)).toBe('Team Marketing')
  })

  it('falls back to the raw name when it does not match the personal-group pattern', () => {
    expect(translateGroupName(t, 'Some Random Group', true)).toBe('Some Random Group')
  })

  it('extracts a username containing an apostrophe correctly', () => {
    expect(translateGroupName(t, "o'brien's Personal Group", true)).toBe(
      "Groupe personnel de o'brien",
    )
  })
})
