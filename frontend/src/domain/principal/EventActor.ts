/** What kind of principal performed an event: a person, or a machine holding a token. */
export type PrincipalKind = 'user' | 'serviceAccount'

/** Who performed an event, as shown to humans. `null` where used means the actor no longer exists. */
export interface EventActor {
  kind: PrincipalKind
  displayName: string
}
