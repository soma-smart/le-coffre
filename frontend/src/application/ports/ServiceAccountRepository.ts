import type {
  CreatedServiceAccount,
  RotatedServiceAccountToken,
  ServiceAccountPage,
} from '@/domain/serviceAccount/ServiceAccount'

export interface ServiceAccountRepository {
  /** The returned token is the only time it is ever readable. */
  create(groupId: string, name: string): Promise<CreatedServiceAccount>
  /** Every account of the group, revoked ones included, plus the cap counters. */
  listForGroup(groupId: string): Promise<ServiceAccountPage>
  /** Issues a new token and kills the current one. The account itself survives. */
  rotate(serviceAccountId: string): Promise<RotatedServiceAccountToken>
  revoke(serviceAccountId: string): Promise<void>
}
