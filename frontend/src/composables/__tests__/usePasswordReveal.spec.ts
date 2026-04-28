import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { usePasswordReveal } from '@/composables/usePasswordReveal'

function makeUseCases(value: string | (() => Promise<string> | string)) {
  const execute = vi.fn(async () => (typeof value === 'function' ? await value() : value))
  return { useCases: { get: { execute } }, execute }
}

describe('usePasswordReveal', () => {
  it('fetches once and caches across reveal → hide → reveal', async () => {
    const { useCases, execute } = makeUseCases('s3cret')
    const { passwordValue, isVisible, toggleVisibility } = usePasswordReveal({
      passwordId: ref('p1'),
      useCases,
    })

    expect(passwordValue.value).toBeNull()
    await toggleVisibility()
    expect(passwordValue.value).toBe('s3cret')
    expect(isVisible.value).toBe(true)

    await toggleVisibility() // hide
    expect(isVisible.value).toBe(false)
    expect(execute).toHaveBeenCalledTimes(1)

    await toggleVisibility() // reveal again — uses cache
    expect(isVisible.value).toBe(true)
    expect(execute).toHaveBeenCalledTimes(1)
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

  it('reset() clears the cache so the next toggle re-fetches', async () => {
    const { useCases, execute } = makeUseCases('first')
    const { toggleVisibility, reset } = usePasswordReveal({
      passwordId: ref('p1'),
      useCases,
    })

    await toggleVisibility()
    expect(execute).toHaveBeenCalledTimes(1)

    reset()
    await toggleVisibility()
    expect(execute).toHaveBeenCalledTimes(2)
  })
})
