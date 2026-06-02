import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { usePasswordReveal } from '@/composables/usePasswordReveal'

function makeUseCases(value: string | (() => Promise<string> | string)) {
  const execute = vi.fn(async () => (typeof value === 'function' ? await value() : value))
  return { useCases: { get: { execute } }, execute }
}

describe('usePasswordReveal', () => {
  it('caches the secret across reveal → hide → reveal', async () => {
    // Behavioural: the use case returns a different value on every call.
    // If the composable refetched after hide+reveal, we'd see 'second';
    // because it caches, we still see 'first'.
    let counter = 0
    const useCases = {
      get: { execute: async () => `secret-${++counter}` },
    }
    const { passwordValue, isVisible, toggleVisibility } = usePasswordReveal({
      passwordId: ref('p1'),
      useCases,
    })

    await toggleVisibility() // reveal — secret-1
    expect(passwordValue.value).toBe('secret-1')
    expect(isVisible.value).toBe(true)

    await toggleVisibility() // hide
    expect(isVisible.value).toBe(false)

    await toggleVisibility() // reveal again — still secret-1
    expect(passwordValue.value).toBe('secret-1')
    expect(isVisible.value).toBe(true)
  })

  it('exposes loading state during the fetch', async () => {
    let resolve: (v: string) => void = () => {}
    const pending = new Promise<string>((r) => (resolve = r))
    const { useCases } = makeUseCases(() => pending)

    const { isLoading, toggleVisibility } = usePasswordReveal({
      passwordId: ref('p1'),
      useCases,
    })

    const flow = toggleVisibility()
    expect(isLoading.value).toBe(true)
    resolve('done')
    await flow
    expect(isLoading.value).toBe(false)
  })

  it('does not flip visibility when the fetch fails — and reports via onError', async () => {
    const onError = vi.fn()
    const useCases = {
      get: {
        execute: vi.fn(async () => {
          throw new Error('boom')
        }),
      },
    }
    const { isVisible, passwordValue, toggleVisibility } = usePasswordReveal({
      passwordId: ref('p1'),
      useCases,
      onError,
    })

    await toggleVisibility()
    expect(isVisible.value).toBe(false)
    expect(passwordValue.value).toBeNull()
    expect(onError).toHaveBeenCalledTimes(1)
  })

  it('revealAndCopy resolves to null when the fetch fails', async () => {
    const onError = vi.fn()
    const useCases = {
      get: {
        execute: vi.fn(async () => {
          throw new Error('boom')
        }),
      },
    }
    const { revealAndCopy } = usePasswordReveal({
      passwordId: ref('p1'),
      useCases,
      onError,
    })

    expect(await revealAndCopy()).toBeNull()
    expect(onError).toHaveBeenCalledTimes(1)
  })

  it('reset() clears the cache so the next reveal sees a fresh value', async () => {
    let counter = 0
    const useCases = {
      get: { execute: async () => `secret-${++counter}` },
    }
    const { passwordValue, toggleVisibility, reset } = usePasswordReveal({
      passwordId: ref('p1'),
      useCases,
    })

    await toggleVisibility()
    expect(passwordValue.value).toBe('secret-1')

    reset()
    await toggleVisibility()
    expect(passwordValue.value).toBe('secret-2')
  })
})
