/**
 * Framework-free container — holds every use case the presentation layer
 * needs. Vue imports nothing from this file; `plugins/container.ts` is the
 * only Vue-aware bridge. Tests build their own container with in-memory
 * fakes; production wires HTTP adapters via `composition_root.ts`.
 *
 * Features will extend `Container` and `Ports` as the migration progresses.
 * For now, both are empty on purpose — the skeleton lets us wire DI end
 * to end before any real use case exists.
 */

export interface Ports {
  // Filled in by later commits: passwordRepository, groupRepository, …
}

export interface Container {
  // Filled in by later commits: passwords, groups, users, vault, …
}

export function buildContainer(_ports: Ports): Container {
  return {}
}
