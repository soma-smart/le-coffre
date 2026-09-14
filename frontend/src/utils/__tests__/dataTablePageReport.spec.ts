import { describe, expect, it } from 'vitest'
import { buildPageReportTemplate } from '../dataTablePageReport'

describe('buildPageReportTemplate', () => {
  it('translates the surrounding words while leaving PrimeVue\'s own tokens untouched', () => {
    const t = (key: string) =>
      ({
        'common.pagination.showing': 'Affichage de',
        'common.pagination.to': 'à',
        'common.pagination.of': 'sur',
      })[key as 'common.pagination.showing' | 'common.pagination.to' | 'common.pagination.of'] ??
      key

    const template = buildPageReportTemplate(t, 'événements')

    // PrimeVue does its own find-and-replace on these tokens after this
    // string is returned — they must survive untouched, not get consumed
    // by our own t() interpolation (which would fail silently since no
    // {first}/{last}/{totalRecords} values are ever supplied here).
    expect(template).toBe('Affichage de {first} à {last} sur {totalRecords} événements')
  })
})
