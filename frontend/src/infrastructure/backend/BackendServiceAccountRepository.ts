import {
  createServiceAccountIamServiceAccountsPost,
  listServiceAccountsIamServiceAccountsGet,
  revokeServiceAccountIamServiceAccountsServiceAccountIdDelete,
  rotateServiceAccountTokenIamServiceAccountsServiceAccountIdRotatePost,
} from '@/client/sdk.gen'
import type { ServiceAccountSummary } from '@/client/types.gen'
import type { ServiceAccountRepository } from '@/application/ports/ServiceAccountRepository'
import type {
  CreatedServiceAccount,
  RotatedServiceAccountToken,
  ServiceAccount,
  ServiceAccountPage,
} from '@/domain/serviceAccount/ServiceAccount'
import {
  InvalidServiceAccountNameError,
  ServiceAccountAlreadyRevokedError,
  ServiceAccountDomainError,
  ServiceAccountNotFoundError,
  ServiceAccountNotOwnerError,
  TooManyActiveServiceAccountsError,
} from '@/domain/serviceAccount/errors'

/**
 * Backend adapter for ServiceAccountRepository. Maps snake_case DTOs to
 * camelCase domain objects and translates HTTP status codes into domain errors.
 */
export class BackendServiceAccountRepository implements ServiceAccountRepository {
  async create(groupId: string, name: string): Promise<CreatedServiceAccount> {
    const response = await createServiceAccountIamServiceAccountsPost({
      body: { group_id: groupId, name },
    })
    throwFor(
      response.error,
      response.response?.status,
      'Could not create the service account',
      (detail) => new TooManyActiveServiceAccountsError(detail),
    )
    if (!response.data)
      throw new ServiceAccountDomainError('Empty response from create service account')
    return {
      id: response.data.id,
      groupId: response.data.group_id,
      name: response.data.name,
      token: response.data.token,
    }
  }

  async listForGroup(groupId: string): Promise<ServiceAccountPage> {
    const response = await listServiceAccountsIamServiceAccountsGet({
      query: { group_id: groupId },
    })
    throwFor(
      response.error,
      response.response?.status,
      'Could not load the service accounts',
      (detail) => new ServiceAccountDomainError(detail ?? 'Could not load the service accounts'),
    )
    return {
      accounts: (response.data?.items ?? []).map(toServiceAccount),
      active: response.data?.active ?? 0,
      maxActive: response.data?.max_active ?? 0,
    }
  }

  async rotate(serviceAccountId: string): Promise<RotatedServiceAccountToken> {
    const response = await rotateServiceAccountTokenIamServiceAccountsServiceAccountIdRotatePost({
      path: { service_account_id: serviceAccountId },
    })
    throwFor(
      response.error,
      response.response?.status,
      'Could not rotate the token',
      (detail) => new ServiceAccountAlreadyRevokedError(detail),
    )
    if (!response.data)
      throw new ServiceAccountDomainError('Empty response from rotate service account token')
    return { id: response.data.id, token: response.data.token }
  }

  async revoke(serviceAccountId: string): Promise<void> {
    const response = await revokeServiceAccountIamServiceAccountsServiceAccountIdDelete({
      path: { service_account_id: serviceAccountId },
    })
    throwFor(
      response.error,
      response.response?.status,
      'Could not revoke the service account',
      (detail) => new ServiceAccountAlreadyRevokedError(detail),
    )
  }
}

/**
 * Translates a failed call into a domain error.
 *
 * `onConflict` is per-operation on purpose: the backend answers 409 both for
 * the cap being full and for an account that is already revoked, and the status
 * alone cannot tell them apart. Which one is possible depends on the call, so
 * the caller names it rather than this function guessing from the message text.
 */
function throwFor(
  error: unknown,
  status: number | undefined,
  fallback: string,
  onConflict: (detail: string | null) => ServiceAccountDomainError,
): void {
  if (!error) return
  const detail = extractDetail(error)
  if (status === 403) throw new ServiceAccountNotOwnerError()
  if (status === 404) throw new ServiceAccountNotFoundError()
  if (status === 409) throw onConflict(detail)
  if (status === 400) throw new InvalidServiceAccountNameError(detail ?? fallback)
  throw new ServiceAccountDomainError(detail ?? fallback)
}

function toServiceAccount(dto: ServiceAccountSummary): ServiceAccount {
  return {
    id: dto.id,
    groupId: dto.group_id,
    name: dto.name,
    createdByUserId: dto.created_by_user_id ?? null,
    createdByUserName: dto.created_by_user_name ?? null,
    createdAt: dto.created_at ?? null,
    revokedAt: dto.revoked_at ?? null,
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
