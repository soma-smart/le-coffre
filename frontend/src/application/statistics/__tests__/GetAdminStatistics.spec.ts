import { describe, expect, it } from 'vitest'
import { GetAdminStatisticsUseCase } from '@/application/statistics/GetAdminStatistics'
import { InMemoryStatisticsGateway } from '@/infrastructure/in_memory/InMemoryStatisticsGateway'

describe('GetAdminStatisticsUseCase', () => {
  it('returns the counts produced by the gateway', async () => {
    const gateway = new InMemoryStatisticsGateway().seed({
      userCount: 12,
      oneTimeLinkCount: 9,
      activeOneTimeLinkCount: 2,
      groupCount: 4,
      passwordCount: 87,
    })
    const useCase = new GetAdminStatisticsUseCase(gateway)

    expect(await useCase.execute()).toEqual({
      userCount: 12,
      groupCount: 4,
      passwordCount: 87,
      oneTimeLinkCount: 9,
      activeOneTimeLinkCount: 2,
    })
  })

  it('propagates gateway errors unchanged', async () => {
    const gateway = new InMemoryStatisticsGateway().failWith(new Error('boom'))
    const useCase = new GetAdminStatisticsUseCase(gateway)

    await expect(useCase.execute()).rejects.toThrow('boom')
  })
})
