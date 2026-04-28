import type { PreferencesGateway } from '@/application/ports/PreferencesGateway'
import type { PreferenceKey } from '@/domain/preferences/Preference'

export interface WritePreferenceCommand<T> {
  key: PreferenceKey
  value: T
}

export class WritePreferenceUseCase {
  constructor(private readonly gateway: PreferencesGateway) {}

  execute<T>(command: WritePreferenceCommand<T>): void {
    this.gateway.write(command.key, command.value)
  }
}
