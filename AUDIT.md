# Le Coffre — Security Audit & Penetration Test

| | |
|---|---|
| **Target** | `soma-smart/le-coffre` (self-hosted secret/password manager) |
| **Commit audited** | `bf43c26b62470aa1336959388d97d838a72b4801` (branch `main`) |
| **Audit date** | 2026-06-11 |
| **Scope** | Backend (FastAPI / Python), Frontend (Vue 3), build & container configuration |
| **Type** | White-box code audit + dynamic penetration test against a local instance |

> **Responsible disclosure note.** This report intentionally keeps the exploitation
> details of the most sensitive finding (**A-01, SSRF**) at a high level. Full
> step-by-step reproduction for that finding is delivered through a private channel
> so that it can be remediated before public weaponization. All other findings are
> low-impact hardening items and are documented in full here.

---

## 1. Executive summary

Le Coffre is a well-engineered application with a **strong security core**. The
cryptographic design (AES-256-GCM with per-message salt/nonce, Shamir's Secret
Sharing for the master key), the authentication layer (JWT validation that correctly
rejects `alg=none` and wrong-key tokens, `HttpOnly` + `SameSite=Strict` cookies),
the CSRF synchronizer-token middleware, the login lockout, and the per-password
ACL all behaved correctly under active testing. Dependency and secret scanning came
back essentially clean.

The findings below are therefore **not** breaks of the core vault. They concentrate
in one area — **broken/insufficient object-level authorization on identity endpoints**
— plus a server-side request forgery in the SSO configuration flow and a series of
hardening gaps (missing HTTP security headers, missing input validation, error-handling
defects, container hygiene).

No Critical issue and no unauthenticated path to plaintext secrets was found.

### Findings at a glance

| ID | Severity | Title | Class |
|----|----------|-------|-------|
| A-01 | Medium | SSRF via SSO OIDC discovery URL | CWE-918 / OWASP A10 |
| A-02 | Medium | Broken object-level authorization on identity endpoints (user/group IDOR + full user enumeration) | CWE-639 / OWASP A01 |
| A-03 | Low | Password-ID existence oracle through divergent error responses | CWE-203 |
| A-04 | Low | Authorization failure on password sharing surfaces as HTTP 500 | CWE-755 |
| A-05 | Low | Missing input validation (email format, field length, uniqueness) | CWE-20 |
| A-06 | Low | Missing HTTP security headers and no application-level CORS policy | CWE-693 |
| A-07 | Low | `JWT_SECRET_KEY` soft-fails to a random per-process key | CWE-453 |
| A-08 | Low | Unauthenticated vault state disclosure & unlock surface | CWE-306 (partly by design) |
| A-09 | Low | No server-side logout / token revocation; refresh token not rotated | CWE-613 |
| A-10 | Info | Container image hardening (Trivy misconfigurations) | CWE-1357 |
| A-11 | Info | Security state is process-local (rate limit / lockout / CSRF / vault key) | Design / HA |

---

## 2. Scope & methodology

### 2.1 In scope
- Application-layer authentication, authorization and session handling
- Cryptography and key management (vault, password encryption, SSO secret storage)
- API input handling, error handling and information disclosure
- Dependency, secret and container/IaC configuration security

### 2.2 Out of scope (per project `SECURITY.md`)
- Full host/OS/runtime compromise (root access is assumed game-over)
- Side-channel / memory-forensics attacks against an unsealed vault

### 2.3 Methodology
The instance was built and run locally (FastAPI backend on `127.0.0.1:8000`,
SQLite database, vault initialized with a 3-share / 2-threshold Shamir configuration).
Three test principals were provisioned: one `admin`, and two regular users (`alice`,
`bob`) with separate groups and a password owned by `bob`, enabling cross-tenant
authorization testing. Every dynamic finding below was reproduced against this
running instance; "good behaviour" (defenses that held) was verified the same way.

**Static tooling** (run via Docker / `uvx`, no host modification):

| Tool | Version | Purpose | Headline result |
|------|---------|---------|-----------------|
| Semgrep | 1.165.0 | SAST (`p/python`, `p/owasp-top-ten`, `p/secrets`, JS/TS) | 2 findings, both false positives |
| Bandit | 1.9.4 | Python SAST | 5 findings, all `B413` false positives (PyCryptodome) |
| pip-audit | latest | Python dependency CVEs | No known vulnerable dependencies |
| `bun audit` | bun 1.2.21 | JS dependency CVEs | No vulnerabilities |
| Trivy | 0.71.0 | Deps + secrets + IaC misconfig | 0 dep CVEs, 0 secrets, Dockerfile misconfigs only |
| Gitleaks | 8.30.1 | Secret scan over full git history | 14 hits, all test fixtures / docstring examples |

---

## 3. Detailed findings

### A-01 — SSRF via SSO OIDC discovery URL  ·  Medium  ·  CWE-918 / OWASP A10
**Location:** `server/src/identity_access_management_context/adapters/secondary/oauth2_sso_gateway.py:44-46`
(reached from `application/use_cases/sso/configure_sso_provider_use_case.py:63`)

The `POST /api/auth/sso/configure` endpoint accepts a `discovery_url` and the server
fetches it server-side (`httpx.AsyncClient().get(discovery_url)`) to auto-discover the
OIDC endpoints. The URL is **not validated**: there is no scheme allow-list and no
restriction against loopback, private (RFC 1918), link-local or cloud-metadata
(`169.254.169.254`) destinations. The endpoint requires the `admin` role, which bounds
exploitability to an authenticated administrator (or a compromised/rogue admin session),
but in a cloud deployment it is a path from "admin web session" to "fetch internal
services / cloud-metadata credentials."

The fetch is **semi-blind**: on a malformed response the error is returned to the caller
as `"Configuration failed: <underlying error>"` (`oauth2_sso_gateway.py:68`,
`configure_sso_provider_use_case.py:101`), and the parsed JSON keys are reflected (e.g.
`Missing fields in discovery: ['authorization_endpoint', 'token_endpoint']`), giving an
oracle over internal JSON endpoints.

> Out-of-band confirmation that the **server** issues the outbound request (against an
> attacker-designated internal listener) was obtained during testing. Detailed
> reproduction steps and the cloud-metadata exfiltration angle are provided in the
> private advisory accompanying this report.

**Remediation**
- Validate `discovery_url` before fetching: require `https`, resolve the hostname and
  reject loopback / private / link-local / ULA / metadata ranges (re-check after DNS
  resolution to defeat DNS-rebinding; pin to the resolved IP for the request).
- Optionally constrain to an operator-configured allow-list of provider hostnames.
- Disable redirects (`follow_redirects=False`) and do not echo the upstream error
  body/keys back to the client.

---

### A-02 — Broken object-level authorization on identity endpoints  ·  Medium  ·  CWE-639 / OWASP A01
**Locations:**
- `server/src/identity_access_management_context/adapters/primary/fastapi/routes/user/user_get_routes.py` (`GET /users/{id}`)
- `.../routes/user/user_list_routes.py` (`GET /users/`)
- `.../routes/group/get_group_routes.py` (`GET /groups/{id}`)

These endpoints require only authentication (`get_current_user`) and perform **no
object-level authorization**. The `GetUserCommand` / `GetGroupCommand` are built from
the path id alone and never receive the caller's identity, so any logged-in user can:

- read any other user's record (id, username, **email**, name, **roles**);
- **enumerate every account** in the system via `GET /users/` (the list endpoint is not
  admin-restricted), exposing all emails and revealing which accounts are admins;
- read any group's full ownership/membership via `GET /groups/{id}`.

For a password manager this is meaningful: it lets a low-privilege user map the entire
user base, harvest internal email addresses, and single out administrators as targets.

**Evidence (regular user `alice`, role `[]`):**
```
$ curl -b alice.cookies http://127.0.0.1:8000/api/users/<admin_id>
{"id":"...","username":"admin","email":"admin@audit.local","name":"Audit Admin","roles":["admin"]}

$ curl -b alice.cookies http://127.0.0.1:8000/api/users/        # lists EVERY account
[{"username":"admin","email":"admin@audit.local","roles":["admin"]},
 {"username":"alice","email":"alice@audit.local","roles":[]},
 {"username":"bob","email":"bob@audit.local","roles":[]}, ...]

$ curl -b alice.cookies http://127.0.0.1:8000/api/groups/<bob_private_group_id>
{"id":"...","name":"Bob Secret Team","is_personal":false,"owners":["<bob_id>"],"members":[]}
```
By contrast, the **password** ACL is correctly enforced (see §4) — this finding is
specific to the identity (user/group) endpoints.

**Remediation**
- Restrict `GET /users/` to administrators; restrict `GET /users/{id}` to self-or-admin.
- Restrict `GET /groups/{id}` to members/owners of the group (or admin). Thread the
  authenticated principal into the use case and enforce it there, consistent with how
  the password context already does authorization.

---

### A-03 — Password-ID existence oracle through divergent error responses  ·  Low  ·  CWE-203
**Locations:** `password_get_routes.py`, `password_events_list_routes.py`,
`application/use_cases/get_password_use_case.py`

Access to a password the caller may not read is intended to be indistinguishable from a
missing password, but the responses diverge by **body** and, for the events endpoint,
by **status code**:

```
GET /api/passwords/<nonexistent>          -> 404 {"detail":"The requested password with ID ... was not found"}
GET /api/passwords/<exists,forbidden>     -> 404 {"detail":"User ... does not have permission to access password ..."}
GET /api/passwords/<nonexistent>/events   -> 404 (not found)
GET /api/passwords/<exists,forbidden>/events -> 403 (permission)
```
An authenticated attacker can therefore distinguish "this password id exists" from "it
does not," and the messages additionally echo the requester and resource UUIDs.

**Remediation**
- Return an identical response (same status code **and** body) for "not found" and
  "forbidden" — `404` with a generic detail is the simplest. Apply consistently across
  `GET /passwords/{id}`, `/events`, `/access`. Avoid echoing user/resource UUIDs.

---

### A-04 — Authorization failure on password sharing surfaces as HTTP 500  ·  Low  ·  CWE-755
**Location:** `password_management_context/adapters/primary/fastapi/routes/share_password_routes.py:74-76`
(use case raises at `application/use_cases/access/share_access_use_case.py:68`)

When a non-owner attempts `POST /api/passwords/{id}/share`, the use case raises
`UserNotOwnerOfGroupError`, but the route's `except` chain does not handle it, so it
falls through to the generic handler and returns **`500 Internal Server Error`** (with a
full traceback logged) instead of `403`. Access is still correctly denied (no privilege
escalation — the share does not occur and the target still cannot read the password),
so the impact is limited to noisy error handling and a weak information signal.

**Evidence:**
```
$ curl -X POST .../passwords/<bob_pw>/share -b alice.cookies -H "X-CSRF-Token: ..." -d '{"group_id":"<alice_group>"}'
{"detail":"Internal server error"}   [HTTP 500]
# server log: UserNotOwnerOfGroupError: User <alice> is not the owner of group <bob_group>
```

**Remediation**
- Add `except UserNotOwnerOfGroupError -> HTTPException(403, ...)` to the share route
  (mirroring the other authorization branches). Audit sibling routes for other
  domain exceptions that are not mapped to a 4xx.

---

### A-05 — Missing input validation  ·  Low  ·  CWE-20
**Locations:** `user_create_routes.py` (`CreateUserRequest`),
`password_create_routes.py` (`CreatePasswordRequest`), `group_create_routes.py`

Request models use bare `str` fields with no constraints. Observed during testing:
- `email` accepts non-email values (`"not-an-email"`) and **duplicate** emails are
  accepted (two users created with the same address);
- `name` accepts a 4000-character value (no upper bound), and no field has a length
  limit — usable for storage abuse and oversized-payload pressure;
- no password policy on user creation.

```
$ curl -X POST .../users/ -b admin.cookies -H "X-CSRF-Token: ..." \
       -d '{"username":"badval","email":"not-an-email","name":"<4000 chars>","password":"x"}'
-> HTTP 201 Created
```

**Remediation**
- Use `pydantic.EmailStr` for email fields; add `min_length`/`max_length` constraints to
  all free-text fields; enforce email uniqueness at the application layer; add a minimum
  password policy. Consider an explicit request-body size limit at the proxy/app layer.

---

### A-06 — Missing HTTP security headers and no application-level CORS policy  ·  Low  ·  CWE-693
**Location:** `server/src/main.py:246-258` (middleware stack)

API responses carry none of the standard hardening headers — no
`Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`,
`Strict-Transport-Security`, `Referrer-Policy`, or `Permissions-Policy` — and there is no
application-level CORS configuration (cross-origin `OPTIONS` returns `405`). Defense-in-
depth headers may be intended for the nginx layer, but they are absent from the
application's own responses and should not be assumed present in every deployment.

**Remediation**
- Add a small security-headers middleware (or set the headers at nginx and document the
  requirement). For an API served to a SPA, at minimum send `X-Content-Type-Options:
  nosniff`, a restrictive `Referrer-Policy`, `Cache-Control: no-store` on sensitive
  responses, and `Strict-Transport-Security` in production. Define an explicit, locked-
  down CORS policy rather than relying on the default-deny.

---

### A-07 — `JWT_SECRET_KEY` soft-fails to a random per-process key  ·  Low  ·  CWE-453
**Location:** `server/src/config.py:10-31`

If `JWT_SECRET_KEY` is unset, the app only emits a `warnings.warn(...)` and boots with a
random per-process key. In a multi-replica or restart-prone production deployment this
silently invalidates all sessions (tokens minted by one replica are rejected by another),
and an operator who misses the warning ships a non-persistent signing key.

**Remediation**
- Fail closed in production: when `ENVIRONMENT=production` and `JWT_SECRET_KEY` is unset,
  raise on startup instead of warning. Keep the random-key convenience for development only.

---

### A-08 — Unauthenticated vault state disclosure & unlock surface  ·  Low  ·  CWE-306 (partly by design)
**Locations:** `vault_status_get_routes.py`, `vault_unlock_routes.py`, `vault_setup_routes.py`

The vault `setup`, `validate-setup`, `unlock` and `status` endpoints are intentionally
unauthenticated (unlock must precede any login). This is documented in `SECURITY.md` and
mitigated by network isolation. Two observations refine the residual risk:
- `GET /api/vault/status` returns the lock state unauthenticated (`{"status":"UNLOCKED",...}`),
  giving an unauthenticated network peer the vault's current state.
- `unlock` accumulates shares and returns `202` until the threshold is met, which is a
  small information signal, and share submission is only bounded by the global per-IP
  rate limit.

**Remediation**
- Keep the documented network-isolation requirement prominent. Consider authenticating
  `GET /vault/status`, adding a dedicated rate limit / audit-alert on `unlock` share
  submissions, and avoiding a distinct "more shares needed" signal.

---

### A-09 — No server-side logout / token revocation  ·  Low  ·  CWE-613
**Location:** authentication routes (no logout/revocation route present)

There is no logout endpoint that invalidates the session server-side and no refresh-token
rotation or revocation; a refresh token stays valid for its full 4-hour lifetime. The
blast radius is reduced by the **short 5-minute access-token lifetime**, but a leaked
refresh token cannot be revoked before expiry.

**Remediation**
- Add a logout endpoint that clears cookies and the per-user CSRF token, and consider a
  refresh-token denylist / rotation-on-use so a stolen refresh token can be invalidated.

---

### A-10 — Container image hardening (Trivy misconfigurations)  ·  Info  ·  CWE-1357
**Locations:** `Dockerfile.dev`, `server/Dockerfile`, `frontend/Dockerfile`

Trivy reported only Dockerfile hygiene issues (no dependency CVEs, no secrets). Most are
in `Dockerfile.dev` (the developer image), which also installs `sudo`: `apt-get` without
`--no-install-recommends` (×3, HIGH), `RUN cd` instead of `WORKDIR` (×2), and no
`HEALTHCHECK`. The production images are flagged only for `apt-get` recommends (builder
stage, discarded) and a missing `HEALTHCHECK` on the frontend image.

**Remediation**
- Add `--no-install-recommends` to `apt-get install`, use `WORKDIR` instead of `RUN cd`,
  and define `HEALTHCHECK`s. Keep `sudo` out of any image that could be used as a base for
  runtime. Wire Trivy/Hadolint Dockerfile linting into CI.

---

### A-11 — Security state is process-local  ·  Info  ·  Design / HA
**Location:** `server/src/main.py` lifespan (`InMemoryRateLimiter`,
`InMemoryLoginLockoutGateway`, `CsrfTokenManager`, `InMemoryVaultSessionGateway`)

Rate-limit counters, login-lockout counters, CSRF tokens and the unsealed vault key are
all in-memory and process-local. Across multiple replicas the protections are per-instance
(an attacker can spread brute-force/abuse across replicas), CSRF tokens are not portable
between instances, and all state resets on restart. This is acceptable for a single-instance
deployment but is a correctness/HA concern at scale.

**Remediation**
- For multi-instance deployments, back rate-limit/lockout/CSRF state with a shared store
  (e.g. Redis), and document that vault unsealing is per-replica. Note the trade-offs
  explicitly in the deployment guide.

---

## 4. Strengths confirmed during testing

The following defenses were verified live and **held**:

- **Cryptography** — Vault key wrapping and password encryption use AES-256-GCM with a
  random 16-byte salt and GCM nonce per message, authenticated decryption
  (`decrypt_and_verify`), PBKDF2 key derivation over a high-entropy master key, and
  Shamir's Secret Sharing for the master key. Plaintext is never persisted.
- **JWT validation** — Forged `alg=none` tokens and tokens signed with a wrong secret are
  both rejected with `401`; the verifier pins a single algorithm (no algorithm-confusion).
- **Password ACL** — A regular user could not read, list events of, or share another
  user's password (group-membership/ownership enforced in the use case).
- **Privilege escalation blocked** — `POST /users/{id}/promote-admin` returned `403` to a
  non-admin (`AdminPermissionChecker` enforced in the use case).
- **CSRF** — Mutating requests without a valid `X-CSRF-Token` are rejected with `403`;
  cookies are `HttpOnly` + `SameSite=Strict` (+ `Secure` in production).
- **Brute-force** — Login lockout triggers after 5 failed attempts (`Retry-After: 300`),
  with a uniform `401 "Invalid credentials"` body that does not enable user enumeration;
  a dedicated per-IP rate limit also covers `/api/auth/login`.
- **Injection / sinks** — Data access is via the SQLModel ORM (parameterized); no
  `eval`/`exec`/`subprocess`/`pickle`/`yaml.load` sinks; no file-upload surface.
- **Supply chain** — No known-vulnerable Python or JavaScript dependencies; no real
  secrets in git history; sensitive values are not written to logs.

---

## 5. Prioritized recommendations

1. **Fix A-02 (authorization on identity endpoints)** — highest-value change; restrict
   user/group reads and the user-list endpoint to the appropriate principals.
2. **Fix A-01 (SSO SSRF)** — add destination validation + scheme allow-list, disable
   redirects, stop reflecting upstream errors.
3. **Normalize error responses (A-03, A-04)** — identical not-found/forbidden responses;
   map domain authorization errors to `403`, never `500`.
4. **Add input validation (A-05)** and **security headers (A-06)**.
5. **Harden configuration (A-07, A-08, A-09)** — fail-closed JWT secret in production,
   authenticate vault status, add logout/refresh revocation.
6. **CI hardening** — add SAST (Semgrep/Bandit), secret scanning (Gitleaks) and Dockerfile
   linting (Trivy/Hadolint) to the pipeline (A-10), and plan shared security state for
   multi-replica deployments (A-11).

---

## 6. Appendix — reproduction environment

- Backend run locally with `uv run fastapi dev src/main.py` (SQLite, `ENVIRONMENT=development`).
- Principals: `admin` (role `admin`), `alice` & `bob` (regular users); `bob` owns a private
  group and a password used as the cross-tenant target.
- All dynamic findings reproduced with `curl`/`jq`; static scans run via Docker (`semgrep`,
  `trivy`, `gitleaks`) and `uvx` (`bandit`, `pip-audit`) plus `bun audit`.
- Tool versions are listed in §2.3.

*Full exploitation detail for A-01 is delivered separately via private disclosure.*
