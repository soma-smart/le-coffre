import { describe, expect, it } from 'vitest'
import { isPersonalGroupName, translateGroupName } from '../groupDisplayName'

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

  it('treats an omitted isPersonal the same as true, trusting the caller', () => {
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

  it('extracts a username containing an apostrophe correctly', () => {
    expect(translateGroupName(t, "o'brien's Personal Group", true)).toBe(
      "Groupe personnel de o'brien",
    )
  })

  it('trusts an explicit isPersonal: true even against a name that does not match the pattern', () => {
    // translateGroupName does not re-verify the name itself — a caller unsure
    // whether isPersonal holds should check with isPersonalGroupName first.
    expect(translateGroupName(t, 'Some Random Group', true)).toBe('Groupe personnel de ')
  })
})

describe('isPersonalGroupName', () => {
  it('matches the backend personal-group pattern', () => {
    expect(isPersonalGroupName("malvergnat's Personal Group")).toBe(true)
  })

  it('rejects a free-form shared group name', () => {
    expect(isPersonalGroupName('Team Marketing')).toBe(false)
  })

  it('rejects a name that merely happens to be the same length as the suffix', () => {
    expect(isPersonalGroupName('Some Random Group')).toBe(false)
  })
})
