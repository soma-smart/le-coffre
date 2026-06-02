import { describe, expect, it } from 'vitest'
import { useAsyncStatus } from '@/composables/useAsyncStatus'

describe('useAsyncStatus', () => {
  it('starts idle with no error', () => {
    const { status, error, isLoading, isError } = useAsyncStatus()
    expect(status.value).toBe('idle')
    expect(error.value).toBeNull()
    expect(isLoading.value).toBe(false)
    expect(isError.value).toBe(false)
  })

  it('transitions idle → loading → ready for a successful task', async () => {
    const { status, isLoading, run } = useAsyncStatus<number>()
    const flow = run(async () => {
      expect(status.value).toBe('loading')
      expect(isLoading.value).toBe(true)
      return 42
    })

    await expect(flow).resolves.toBe(42)
    expect(status.value).toBe('ready')
    expect(isLoading.value).toBe(false)
  })

  it('transitions idle → loading → error for a thrown task, and does not re-throw', async () => {
    const { status, error, isError, run } = useAsyncStatus()
    const boom = new Error('boom')

    const result = await run(async () => {
      throw boom
    })

    expect(result).toBeUndefined()
    expect(status.value).toBe('error')
    expect(error.value).toBe(boom)
    expect(isError.value).toBe(true)
  })

  it('clears the previous error when a new run starts', async () => {
    const { status, error, run } = useAsyncStatus()

    await run(async () => {
      throw new Error('first')
    })
    expect(status.value).toBe('error')
    expect(error.value).toBeInstanceOf(Error)

    await run(async () => 'ok')
    expect(status.value).toBe('ready')
    expect(error.value).toBeNull()
  })

  it('reset() returns to idle', async () => {
    const { status, error, run, reset } = useAsyncStatus()
    await run(async () => {
      throw new Error('x')
    })
    expect(status.value).toBe('error')

    reset()
    expect(status.value).toBe('idle')
    expect(error.value).toBeNull()
  })
})
