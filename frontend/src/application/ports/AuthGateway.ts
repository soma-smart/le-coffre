import type { SsoCallbackResult } from '@/domain/auth/Auth'

export interface LoginInput {
  email: string
  password: string
}

export interface RegisterAdminInput {
  email: string
  password: string
  displayName: string
}

export interface ConfigureSsoInput {
  clientId: string
  clientSecret: string
  discoveryUrl: string
}

export interface SsoCallbackInput {
  code: string
  state?: string
}

export interface AuthGateway {
  login(input: LoginInput): Promise<void>
  registerAdmin(input: RegisterAdminInput): Promise<string>
  refreshAccessToken(): Promise<void>
  configureSsoProvider(input: ConfigureSsoInput): Promise<void>
  getSsoUrl(): Promise<string>
  ssoCallback(input: SsoCallbackInput): Promise<SsoCallbackResult>
  isSsoConfigured(): Promise<boolean>
}
