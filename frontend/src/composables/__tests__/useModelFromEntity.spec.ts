import { describe, expect, it } from 'vitest'
import { ref, nextTick } from 'vue'
import { useModelFromEntity } from '@/composables/useModelFromEntity'

interface User {
  id: string
  name: string
  email: string
}

const initial = () => ({ name: '', email: '' })
const fromEntity = (u: User) => ({ name: u.name, email: u.email })

describe('useModelFromEntity', () => {
  it('starts with the initial snapshot when no entity is provided', () => {
    const entity = ref<User | null>(null)
    const { form, isEditing, dirty } = useModelFromEntity({ entity, initial, fromEntity })

    expect(form).toEqual({ name: '', email: '' })
    expect(isEditing.value).toBe(false)
    expect(dirty.value).toBe(false)
  })

  it('hydrates the form when the entity is set, flipping isEditing', async () => {
    const entity = ref<User | null>(null)
    const { form, isEditing } = useModelFromEntity({ entity, initial, fromEntity })

    entity.value = { id: 'u1', name: 'Alice', email: 'alice@example.com' }
    await nextTick()
    expect(form).toEqual({ name: 'Alice', email: 'alice@example.com' })
    expect(isEditing.value).toBe(true)
  })

  it('clears back to the initial snapshot when the entity becomes null', async () => {
    const entity = ref<User | null>({ id: 'u1', name: 'Alice', email: 'alice@example.com' })
    const { form, isEditing } = useModelFromEntity({ entity, initial, fromEntity })
    expect(isEditing.value).toBe(true)

    entity.value = null
    await nextTick()
    expect(form).toEqual({ name: '', email: '' })
    expect(isEditing.value).toBe(false)
  })

  it('dirty flips true after a field edit, false after reset()', async () => {
    const entity = ref<User | null>({ id: 'u1', name: 'Alice', email: 'a@x' })
    const { form, dirty, reset } = useModelFromEntity({ entity, initial, fromEntity })
    expect(dirty.value).toBe(false)

    form.name = 'Renamed'
    await nextTick()
    expect(dirty.value).toBe(true)

    reset()
    await nextTick()
    expect(dirty.value).toBe(false)
    expect(form.name).toBe('Alice')
  })

  it('switching entities re-baselines dirty', async () => {
    const entity = ref<User | null>({ id: 'u1', name: 'Alice', email: 'a@x' })
    const { form, dirty } = useModelFromEntity({ entity, initial, fromEntity })

    form.name = 'Edited'
    await nextTick()
    expect(dirty.value).toBe(true)

    entity.value = { id: 'u2', name: 'Bob', email: 'b@x' }
    await nextTick()
    expect(form).toEqual({ name: 'Bob', email: 'b@x' })
    expect(dirty.value).toBe(false)
  })
})
