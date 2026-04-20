import { inject, type App, type InjectionKey, type Plugin } from 'vue'
import type { Container } from '@/container'

/**
 * Single Vue-aware bridge between the framework-free container and the
 * presentation layer. Components and setup stores resolve use cases via
 * `useContainer().<feature>.<useCase>.execute(...)`.
 *
 * Tests bypass the plugin entirely by passing a fake container through
 * `mount(Component, { global: { provide: { [CONTAINER_KEY]: fake } } })`.
 */
export const CONTAINER_KEY: InjectionKey<Container> = Symbol('le-coffre-container')

export function containerPlugin(container: Container): Plugin {
  return {
    install(app: App) {
      app.provide(CONTAINER_KEY, container)
    },
  }
}

export function useContainer(): Container {
  const container = inject(CONTAINER_KEY)
  if (!container) {
    throw new Error(
      'Container not provided. In the app, install containerPlugin in main.ts. ' +
        'In tests, pass { global: { provide: { [CONTAINER_KEY]: container } } } to mount().',
    )
  }
  return container
}
