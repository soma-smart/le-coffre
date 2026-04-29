import type { PreferencesGateway } from '@/application/ports/PreferencesGateway'
import type { PreferenceKey } from '@/domain/preferences/Preference'

export interface RemovePreferenceCommand {
  key: PreferenceKey
}

export class RemovePreferenceUseCase {
  constructor(private readonly gateway: PreferencesGateway) {}

  execute(command: RemovePreferenceCommand): void {
    this.gateway.remove(command.key)
  }
}
