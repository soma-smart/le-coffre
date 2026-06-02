import { hasInjectionContext, inject, type App, type InjectionKey, type Plugin } from 'vue'
import type { Container } from '@/container'

/**
 * Single Vue-aware bridge between the framework-free container and the
 * presentation layer. Components and setup stores resolve use cases via
 * `useContainer().<feature>.<useCase>.execute(...)`.
 *
 * Resolution is a two-step lookup:
 *   1. inject(CONTAINER_KEY) — primary path, used by every
 *      `.vue` component mounted with containerPlugin installed.
 *   2. A module-level fallback — covers Pinia setup stores accessed
 *      from outside a component tree (e.g. test `beforeEach` blocks
 *      instantiating a store to seed state), where Vue's inject() has
 *      no component context and would otherwise return undefined.
 *
 * In production, containerPlugin sets both. In tests, createTestContext
 * sets the fallback, and each test's afterEach hook (registered in
 * test/setup.ts) resets it for isolation.
 */
export const CONTAINER_KEY: InjectionKey<Container> = Symbol('le-coffre-container')

let fallbackContainer: Container | null = null

export function setContainer(container: Container): void {
  fallbackContainer = container
}

export function resetContainer(): void {
  fallbackContainer = null
}

export function containerPlugin(container: Container): Plugin {
  return {
    install(app: App) {
      app.provide(CONTAINER_KEY, container)
      setContainer(container)
    },
  }
}

export function useContainer(): Container {
  if (hasInjectionContext()) {
    const injected = inject<Container | null>(CONTAINER_KEY, null)
    if (injected) return injected
  }
  if (fallbackContainer) return fallbackContainer
  throw new Error(
    'Container not provided. In the app, install containerPlugin in main.ts. ' +
      'In tests, pass { global: { provide: { [CONTAINER_KEY]: container } } } to mount() ' +
      'or use createTestContext(...) in beforeEach.',
  )
}
