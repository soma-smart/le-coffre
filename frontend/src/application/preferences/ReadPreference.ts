import type { PreferencesGateway } from '@/application/ports/PreferencesGateway'
import type { PreferenceKey } from '@/domain/preferences/Preference'

export interface ReadPreferenceCommand {
  key: PreferenceKey
}

/**
 * Reads a stored preference. Returns `null` when nothing is stored — UI
 * code is expected to fall back to its component-level default.
 */
export class ReadPreferenceUseCase {
  constructor(private readonly gateway: PreferencesGateway) {}

  execute<T>(command: ReadPreferenceCommand): T | null {
    return this.gateway.read<T>(command.key)
  }
}
