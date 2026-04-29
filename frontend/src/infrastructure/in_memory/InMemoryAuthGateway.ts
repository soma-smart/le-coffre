import type {
  AuthGateway,
  ConfigureSsoInput,
  LoginInput,
  RegisterAdminInput,
  SsoCallbackInput,
} from '@/application/ports/AuthGateway'
import type { SsoCallbackResult } from '@/domain/auth/Auth'
import { InvalidCredentialsError } from '@/domain/auth/errors'

/**
 * Test-only AuthGateway. Keeps a tiny in-memory "admin account" plus
 * SSO configuration flags. Refresh / ssoCallback / getSsoUrl can be
 * overridden for specific tests via the setXxx helpers — everything
 * else has reasonable defaults that let a component spec exercise the
 * happy path without extra wiring.
 */
export class InMemoryAuthGateway implements AuthGateway {
  private adminEmail: string | null = null
  private adminPassword: string | null = null
  private ssoConfigured = false
  private nextSsoUrl = 'https://sso.example/authorize'
  private nextCallback: SsoCallbackResult = {
    user: {
      userId: 'sso-user',
      email: 'sso@example.com',
      displayName: 'SSO User',
      isNewUser: false,
    },
  }

  seedAdmin(email: string, password: string): this {
    this.adminEmail = email
    this.adminPassword = password
    return this
  }

  setSsoConfigured(value: boolean): this {
    this.ssoConfigured = value
    return this
  }

  setSsoUrl(url: string): this {
    this.nextSsoUrl = url
    return this
  }

  setSsoCallback(result: SsoCallbackResult): this {
    this.nextCallback = result
    return this
  }

  async login(input: LoginInput): Promise<void> {
    if (input.email !== this.adminEmail || input.password !== this.adminPassword) {
      throw new InvalidCredentialsError()
    }
  }

  async registerAdmin(input: RegisterAdminInput): Promise<string> {
    this.adminEmail = input.email
    this.adminPassword = input.password
    return `admin-${input.email}`
  }

  async refreshAccessToken(): Promise<void> {
    // no-op in tests; real implementation relies on cookies
  }

  async configureSsoProvider(_input: ConfigureSsoInput): Promise<void> {
    void _input
    this.ssoConfigured = true
  }

  async getSsoUrl(): Promise<string> {
    return this.nextSsoUrl
  }

  async ssoCallback(_input: SsoCallbackInput): Promise<SsoCallbackResult> {
    void _input
    return this.nextCallback
  }

  async isSsoConfigured(): Promise<boolean> {
    return this.ssoConfigured
  }
}
