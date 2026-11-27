import type { EventActorResponse } from '@/client/types.gen'
import type { EventActor } from '@/domain/principal/EventActor'

export function toEventActor(dto: EventActorResponse | null): EventActor | null {
  if (dto === null) return null
  return {
    kind: dto.kind === 'service_account' ? 'serviceAccount' : 'user',
    displayName: dto.display_name,
  }
}
