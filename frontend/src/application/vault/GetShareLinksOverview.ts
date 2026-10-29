import type { VaultRepository } from '@/application/ports/VaultRepository'
import type { ShareLinksOverview } from '@/domain/vault/ShareLinksOverview'

/** Read-only follow-up of the share links of the current setup. Administrators only. */
export class GetShareLinksOverviewUseCase {
  constructor(private readonly repository: VaultRepository) {}

  execute(): Promise<ShareLinksOverview> {
    return this.repository.getShareLinksOverview()
  }
}
