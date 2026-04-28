import { computed, reactive, watch, type ComputedRef, type Ref, type UnwrapNestedRefs } from 'vue'

export interface UseModelFromEntityOptions<TEntity, TForm extends Record<string, unknown>> {
  /** The optional entity prop. `null` / `undefined` means "create" mode. */
  entity: Ref<TEntity | null | undefined>
  /** Form shape for the create mode (when entity is absent). */
  initial: () => TForm
  /** Form shape for the edit mode (entity → form). */
  fromEntity: (entity: TEntity) => TForm
}

export interface UseModelFromEntityReturn<TForm extends Record<string, unknown>> {
  /** Reactive form object — bind directly with v-model. */
  form: UnwrapNestedRefs<TForm>
  /** True when an entity is provided (edit mode). */
  isEditing: ComputedRef<boolean>
  /** True when at least one field differs from the latest baseline. */
  dirty: ComputedRef<boolean>
  /** Re-runs `fromEntity(entity)` (or `initial()` when there's no entity). */
  reset: () => void
}

function shallowEqual(a: Record<string, unknown>, b: Record<string, unknown>): boolean {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)])
  for (const key of keys) {
    if (a[key] !== b[key]) return false
  }
  return true
}

/**
 * Two-way sync between an optional entity prop and a reactive form object.
 *
 * Replaces the imperative `watch(() => props.entity, (e) => { name.value = e?.name; … })`
 * pattern that several modals re-implement. The caller defines two pure
 * functions (`initial` for create mode, `fromEntity` for edit mode); the
 * composable owns the watcher and a baseline snapshot used by `dirty`.
 *
 * The form is `reactive`, not a bag of refs — bind directly with v-model.
 */
export function useModelFromEntity<TEntity, TForm extends Record<string, unknown>>(
  options: UseModelFromEntityOptions<TEntity, TForm>,
): UseModelFromEntityReturn<TForm> {
  const initial = options.initial()
  const form = reactive({ ...initial }) as UnwrapNestedRefs<TForm>
  let baseline: Record<string, unknown> = { ...initial }

  const isEditing = computed(
    () => options.entity.value !== null && options.entity.value !== undefined,
  )

  function applySnapshot(snapshot: TForm) {
    // Shallow-assign to keep the same reactive object identity (so v-model
    // bindings already in the DOM keep working).
    for (const key of Object.keys(form) as Array<keyof typeof form>) {
      delete (form as Record<string, unknown>)[key as string]
    }
    Object.assign(form, snapshot)
    baseline = { ...snapshot }
  }

  function reset() {
    const snapshot = options.entity.value
      ? options.fromEntity(options.entity.value)
      : options.initial()
    applySnapshot(snapshot)
  }

  watch(
    () => options.entity.value,
    () => reset(),
    { immediate: true },
  )

  const dirty = computed(() => !shallowEqual(form as Record<string, unknown>, baseline))

  return { form, isEditing, dirty, reset }
}
