import {
  adminLoginAuthLoginPost,
  configureSsoProviderAuthSsoConfigurePost,
  getSsoUrlAuthSsoUrlGet,
  isSsoConfigSetAuthSsoIsConfiguredGet,
  refreshAccessTokenAuthRefreshTokenPost,
  registerAdminAuthRegisterAdminPost,
  ssoCallbackAuthSsoCallbackGet,
} from '@/client/sdk.gen'
import type { SsoCallbackResponse } from '@/client/types.gen'
import type {
  AuthGateway,
  ConfigureSsoInput,
  LoginInput,
  RegisterAdminInput,
  SsoCallbackInput,
} from '@/application/ports/AuthGateway'
import type { SsoCallbackResult } from '@/domain/auth/Auth'
import { AuthDomainError, InvalidCredentialsError } from '@/domain/auth/errors'

/**
 * Backend adapter for AuthGateway. Wraps every /auth/* SDK function
 * and translates:
 *
 * - camelCase input → snake_case body (display_name, client_id,
 *   client_secret, discovery_url).
 * - snake_case SsoCallbackResponse.user → camelCase SsoUserInfo.
 * - HTTP 401 on login → InvalidCredentialsError; any other failure →
 *   AuthDomainError carrying the backend detail string.
 *
 * The refresh endpoint is special: customClient.ts still calls the
 * raw SDK function from its 401 interceptor to avoid a circular
 * import between the container plugin and the HTTP client.
 */
export class BackendAuthGateway implements AuthGateway {
  async login(input: LoginInput): Promise<void> {
    const response = await adminLoginAuthLoginPost({
      body: { email: input.email, password: input.password },
    })
    if (response.response?.status === 401) throw new InvalidCredentialsError()
    this.throwIfError(response.error)
  }

  async registerAdmin(input: RegisterAdminInput): Promise<string> {
    const response = await registerAdminAuthRegisterAdminPost({
      body: {
        email: input.email,
        password: input.password,
        display_name: input.displayName,
      },
    })
    this.throwIfError(response.error)
    if (!response.data) throw new AuthDomainError('Empty response from register admin')
    return response.data.id
  }

  async refreshAccessToken(): Promise<void> {
    const response = await refreshAccessTokenAuthRefreshTokenPost({ credentials: 'include' })
    this.throwIfError(response.error)
  }

  async configureSsoProvider(input: ConfigureSsoInput): Promise<void> {
    const response = await configureSsoProviderAuthSsoConfigurePost({
      body: {
        client_id: input.clientId,
        client_secret: input.clientSecret,
        discovery_url: input.discoveryUrl,
      },
    })
    this.throwIfError(response.error)
  }

  async getSsoUrl(): Promise<string> {
    const response = await getSsoUrlAuthSsoUrlGet()
    this.throwIfError(response.error)
    if (!response.data) throw new AuthDomainError('Empty response from SSO URL endpoint')
    // Backend returns the URL as a raw string.
    return response.data as unknown as string
  }

  async ssoCallback(input: SsoCallbackInput): Promise<SsoCallbackResult> {
    const response = await ssoCallbackAuthSsoCallbackGet({
      query: { code: input.code, ...(input.state ? { state: input.state } : {}) },
      credentials: 'include',
    })
    this.throwIfError(response.error)
    if (!response.data) throw new AuthDomainError('Empty response from SSO callback')
    return toSsoCallbackResult(response.data)
  }

  async isSsoConfigured(): Promise<boolean> {
    const response = await isSsoConfigSetAuthSsoIsConfiguredGet()
    this.throwIfError(response.error)
    return !!response.data?.is_set
  }

  private throwIfError(error: unknown): void {
    if (!error) return
    throw new AuthDomainError(extractDetail(error) ?? 'Authentication operation failed')
  }
}

function toSsoCallbackResult(dto: SsoCallbackResponse): SsoCallbackResult {
  return {
    user: {
      userId: dto.user.user_id,
      email: dto.user.email,
      displayName: dto.user.display_name,
      isNewUser: dto.user.is_new_user,
    },
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const first = detail[0]
      if (first && typeof first === 'object' && 'msg' in first) {
        const msg = (first as { msg: unknown }).msg
        if (typeof msg === 'string') return msg
      }
    }
  }
  return null
}
