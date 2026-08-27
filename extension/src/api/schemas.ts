/**
 * Runtime shapes for everything the extension reads from a vault.
 *
 * Validated rather than trusted, for two reasons that a generated client would
 * not cover. The base URL is a string the *user typed*, so a typo'd or hostile
 * host must not be mistaken for a vault. And self-hosting makes version skew
 * normal: a vault can be months behind the extension, and the popup should say
 * so rather than throw a TypeError deep inside a component.
 *
 * Unknown keys are ignored throughout, so a newer vault adding a field does not
 * break an older extension.
 */
import { z } from 'zod'

export const healthSchema = z.object({
  status: z.string(),
})

export const vaultStatusSchema = z.object({
  status: z.enum(['NOT_SETUP', 'LOCKED', 'PENDING_UNLOCK', 'UNLOCKED']),
})

export const startPairingSchema = z.object({
  user_code: z.string().min(1),
  expires_at: z.string(),
  poll_interval_seconds: z.number().int().positive(),
})

export const exchangePairingSchema = z.object({
  status: z.enum(['approved', 'pending']),
  expires_at: z.string(),
  poll_interval_seconds: z.number().int().positive().nullable().optional(),
  token: z.string().nullable().optional(),
  token_id: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  display_name: z.string().nullable().optional(),
})

export const extensionSessionSchema = z.object({
  user_id: z.string(),
  email: z.string(),
  display_name: z.string(),
  is_read_only: z.boolean(),
})

export const groupSchema = z.object({
  id: z.string(),
  name: z.string(),
  is_personal: z.boolean(),
  user_id: z.string().nullable(),
  owners: z.array(z.string()),
  members: z.array(z.string()),
})

export const listGroupsSchema = z.object({
  groups: z.array(groupSchema),
})

export const entrySchema = z.object({
  id: z.string(),
  name: z.string(),
  folder: z.string(),
  group_id: z.string(),
  login: z.string().nullable(),
  url: z.string().nullable(),
  can_read: z.boolean(),
  can_write: z.boolean(),
  accessible_group_ids: z.array(z.string()),
  access_expires_at: z.string().nullable().optional(),
})

export const listEntriesSchema = z.array(entrySchema)

export const revealPasswordSchema = z.object({
  password: z.string(),
})

export type StartPairingDto = z.infer<typeof startPairingSchema>
export type ExchangePairingDto = z.infer<typeof exchangePairingSchema>
export type ExtensionSessionDto = z.infer<typeof extensionSessionSchema>
export type GroupDto = z.infer<typeof groupSchema>
export type EntryDto = z.infer<typeof entrySchema>
