import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { useRecentPasswordActivity } from '@/composables/useRecentPasswordActivity'
import type { PasswordEvent } from '@/domain/password/Password'

function makeEvent(overrides: Partial<PasswordEvent> = {}): PasswordEvent {
  return {
    eventId: 'e1',
    eventType: 'PasswordAccessedEvent',
    occurredOn: '2026-01-01T00:00:00Z',
    actorUserId: 'u1',
    actorEmail: 'alice@example.com',
    eventData: {},
    ...overrides,
  }
}

describe('useRecentPasswordActivity', () => {
  it('loads events for the initial passwordId without any date filter', async () => {
    const execute = vi.fn().mockResolvedValue([makeEvent()])
    const { events } = useRecentPasswordActivity({
      passwordId: ref('p1'),
      useCases: { listEvents: { execute } },
    })

    await vi.waitFor(() => expect(events.value).toHaveLength(1))
    expect(execute).toHaveBeenCalledExactlyOnceWith({ passwordId: 'p1' })
  })

  it('sorts events most-recent first and truncates to the limit', async () => {
    const execute = vi
      .fn()
      .mockResolvedValue([
        makeEvent({ eventId: 'old', occurredOn: '2026-01-01T00:00:00Z' }),
        makeEvent({ eventId: 'newest', occurredOn: '2026-03-01T00:00:00Z' }),
        makeEvent({ eventId: 'mid', occurredOn: '2026-02-01T00:00:00Z' }),
      ])
    const { events } = useRecentPasswordActivity({
      passwordId: ref('p1'),
      useCases: { listEvents: { execute } },
      limit: 2,
    })

    await vi.waitFor(() => expect(events.value).toHaveLength(2))
    expect(events.value.map((e) => e.eventId)).toEqual(['newest', 'mid'])
  })

  it('re-fetches when the passwordId changes, and clears when it becomes null', async () => {
    const execute = vi.fn().mockResolvedValue([makeEvent({ eventId: 'a' })])
    const passwordId = ref<string | null>('p1')
    const { events } = useRecentPasswordActivity({
      passwordId,
      useCases: { listEvents: { execute } },
    })

    await vi.waitFor(() => expect(events.value).toHaveLength(1))

    execute.mockResolvedValue([makeEvent({ eventId: 'b' })])
    passwordId.value = 'p2'
    await vi.waitFor(() => expect(events.value.map((e) => e.eventId)).toEqual(['b']))
    expect(execute).toHaveBeenCalledWith({ passwordId: 'p2' })

    passwordId.value = null
    await nextTick()
    expect(events.value).toEqual([])
  })

  it('exposes isLoading while the fetch is in flight, and isError on failure', async () => {
    let resolveFetch: (value: PasswordEvent[]) => void = () => {}
    const execute = vi.fn().mockReturnValue(
      new Promise<PasswordEvent[]>((resolve) => {
        resolveFetch = resolve
      }),
    )
    const { isLoading, isError } = useRecentPasswordActivity({
      passwordId: ref('p1'),
      useCases: { listEvents: { execute } },
    })

    await nextTick()
    expect(isLoading.value).toBe(true)

    resolveFetch([])
    await vi.waitFor(() => expect(isLoading.value).toBe(false))
    expect(isError.value).toBe(false)
  })

  it('sets isError and leaves events empty when the use case throws', async () => {
    const execute = vi.fn().mockRejectedValue(new Error('boom'))
    const { events, isError } = useRecentPasswordActivity({
      passwordId: ref('p1'),
      useCases: { listEvents: { execute } },
    })

    await vi.waitFor(() => expect(isError.value).toBe(true))
    expect(events.value).toEqual([])
  })

  it('starts empty and never fetches when the initial passwordId is null', async () => {
    const execute = vi.fn()
    const { events } = useRecentPasswordActivity({
      passwordId: ref(null),
      useCases: { listEvents: { execute } },
    })

    await nextTick()
    expect(events.value).toEqual([])
    expect(execute).not.toHaveBeenCalled()
  })
})
