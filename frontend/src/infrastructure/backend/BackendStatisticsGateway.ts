import {
  getPasswordStatisticForAdminPasswordsStatisticsGet,
  getStatisticForAdminIamStatisticsGet,
} from '@/client/sdk.gen'
import type { StatisticsGateway } from '@/application/ports/StatisticsGateway'
import type { AdminStatistics } from '@/domain/statistics/Statistics'
import { StatisticsUnavailableError } from '@/domain/statistics/errors'

/**
 * Backend adapter for StatisticsGateway. The counts live in two contexts
 * (IAM exposes users + groups, passwords exposes its own count), so this
 * adapter fans out to both endpoints in parallel and merges the snake_case
 * DTOs into one camelCase domain object. Either call failing fails the whole
 * fetch — the dashboard is all-or-nothing. Only @/client touchpoint for the
 * statistics context.
 */
export class BackendStatisticsGateway implements StatisticsGateway {
  async getAdminStatistics(): Promise<AdminStatistics> {
    const [iam, passwords] = await Promise.all([
      getStatisticForAdminIamStatisticsGet(),
      getPasswordStatisticForAdminPasswordsStatisticsGet(),
    ])

    if (iam.error || !iam.data) {
      throw new StatisticsUnavailableError(extractDetail(iam.error) ?? undefined)
    }
    if (passwords.error || !passwords.data) {
      throw new StatisticsUnavailableError(extractDetail(passwords.error) ?? undefined)
    }

    return {
      userCount: iam.data.user_count,
      groupCount: iam.data.group_count,
      passwordCount: passwords.data.password_count,
      oneTimeLinkCount: passwords.data.one_time_link_count,
      activeOneTimeLinkCount: passwords.data.active_one_time_link_count,
    }
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
