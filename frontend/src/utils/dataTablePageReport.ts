/**
 * Builds a PrimeVue DataTable `currentPageReportTemplate` string with our
 * own translated wording around PrimeVue's own {first}/{last}/{totalRecords}
 * placeholders.
 *
 * Those three tokens must reach PrimeVue untouched — it substitutes them
 * itself once this string is returned — so they're spliced in via plain
 * string concatenation rather than passed through t(), which would try to
 * interpolate them as its own named parameters (and fail, since none are
 * supplied).
 */
export function buildPageReportTemplate(t: (key: string) => string, rowsNoun: string): string {
  return `${t('common.pagination.showing')} {first} ${t('common.pagination.to')} {last} ${t(
    'common.pagination.of',
  )} {totalRecords} ${rowsNoun}`
}
