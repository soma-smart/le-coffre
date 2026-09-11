import { describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { usePasswordSelection } from '@/composables/usePasswordSelection'
import type { Password } from '@/domain/password/Password'

function makePassword(overrides: Partial<Password> = {}): Password {
  return {
    id: 'p1',
    name: 'GitHub',
    folder: 'default',
    groupId: 'g1',
    createdAt: '2026-01-01T00:00:00Z',
    lastUpdatedAt: '2026-01-01T00:00:00Z',
    canRead: true,
    canWrite: true,
    login: null,
    url: null,
    accessibleGroupIds: [],
    accessExpiresAt: null,
    ...overrides,
  }
}

describe('usePasswordSelection', () => {
  it('selects the password matching the route id when it is in the pane', () => {
    const p1 = makePassword({ id: 'p1' })
    const p2 = makePassword({ id: 'p2' })
    const { selectedPassword, contextFixNeeded, staleId } = usePasswordSelection({
      visiblePasswords: ref([p1, p2]),
      allPasswords: ref([p1, p2]),
      routePasswordId: ref('p2'),
      autoSelectFirst: ref(true),
    })

    expect(selectedPassword.value?.id).toBe('p2')
    expect(contextFixNeeded.value).toBeNull()
    expect(staleId.value).toBeNull()
  })

  it('falls back to the first visible password when no id is in the route and autoSelectFirst is on', () => {
    const p1 = makePassword({ id: 'p1' })
    const p2 = makePassword({ id: 'p2' })
    const { selectedPassword } = usePasswordSelection({
      visiblePasswords: ref([p1, p2]),
      allPasswords: ref([p1, p2]),
      routePasswordId: ref(undefined),
      autoSelectFirst: ref(true),
    })

    expect(selectedPassword.value?.id).toBe('p1')
  })

  it('selects nothing when no id is in the route and autoSelectFirst is off (mobile)', () => {
    const p1 = makePassword({ id: 'p1' })
    const { selectedPassword } = usePasswordSelection({
      visiblePasswords: ref([p1]),
      allPasswords: ref([p1]),
      routePasswordId: ref(undefined),
      autoSelectFirst: ref(false),
    })

    expect(selectedPassword.value).toBeNull()
  })

  it('flags contextFixNeeded when the id resolves outside the current pane', () => {
    const inPane = makePassword({ id: 'p1' })
    const elsewhere = makePassword({ id: 'p2', groupId: 'g2', folder: 'Other' })
    const { selectedPassword, contextFixNeeded, staleId } = usePasswordSelection({
      visiblePasswords: ref([inPane]),
      allPasswords: ref([inPane, elsewhere]),
      routePasswordId: ref('p2'),
      autoSelectFirst: ref(true),
    })

    expect(contextFixNeeded.value?.id).toBe('p2')
    expect(staleId.value).toBeNull()
    // Don't guess at a different password while a redirect is pending.
    expect(selectedPassword.value).toBeNull()
  })

  it('flags staleId when the id resolves nowhere, and falls back to the first row', () => {
    const p1 = makePassword({ id: 'p1' })
    const { selectedPassword, contextFixNeeded, staleId } = usePasswordSelection({
      visiblePasswords: ref([p1]),
      allPasswords: ref([p1]),
      routePasswordId: ref('deleted'),
      autoSelectFirst: ref(true),
    })

    expect(staleId.value).toBe('deleted')
    expect(contextFixNeeded.value).toBeNull()
    expect(selectedPassword.value?.id).toBe('p1')
  })

  it('staleId falls back to null selection when autoSelectFirst is off', () => {
    const p1 = makePassword({ id: 'p1' })
    const { selectedPassword, staleId } = usePasswordSelection({
      visiblePasswords: ref([p1]),
      allPasswords: ref([p1]),
      routePasswordId: ref('deleted'),
      autoSelectFirst: ref(false),
    })

    expect(staleId.value).toBe('deleted')
    expect(selectedPassword.value).toBeNull()
  })

  it('returns null selection with an empty pane and no id', () => {
    const { selectedPassword, contextFixNeeded, staleId } = usePasswordSelection({
      visiblePasswords: ref([]),
      allPasswords: ref([]),
      routePasswordId: ref(undefined),
      autoSelectFirst: ref(true),
    })

    expect(selectedPassword.value).toBeNull()
    expect(contextFixNeeded.value).toBeNull()
    expect(staleId.value).toBeNull()
  })
})
