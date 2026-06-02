/**
 * Aggregate admin dashboard counts. A plain value object — no behaviour,
 * just the camelCase shape the presentation layer renders. The backend
 * sources these from two contexts (IAM + passwords); the gateway merges
 * them so the UI sees a single domain type.
 */
export interface AdminStatistics {
  userCount: number
  groupCount: number
  passwordCount: number
}
