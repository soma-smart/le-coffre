# Security Policy

## Supported Versions

Only the latest **minor release of the current major version** is supported
with security updates.

Security fixes are **never backported** to unsupported versions.

| Version | Supported |
| ------- | --------- |
| >= 1.5.1 (latest) | :white_check_mark: |

If you are running an unsupported version, you are strongly encouraged to
upgrade before reporting a vulnerability.

---

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

### How to report

To report a security vulnerability, please use the **GitHub Private Vulnerability Reporting** feature:

1. Navigate to: <https://github.com/soma-smart/le-coffre/security/advisories/new>
2. Or go to the repository's **Security** tab and click **Report a vulnerability**
3. Fill in the private advisory form with the details below

### What to include

Please include as much information as possible to help us reproduce and assess
the issue:

- A clear description of the vulnerability
- Affected component(s) or context(s)
- Steps to reproduce (proof-of-concept if available)
- Potential impact (data exposure, etc.)
- Version(s) affected
- Any relevant logs or screenshots (with sensitive data redacted)

### What to expect

- **Acknowledgement within 72 hours**
- A first assessment within **7 days**
- Regular updates as the issue is investigated

If the vulnerability is accepted:

- We will work on a fix as quickly as possible
- A security advisory may be published once the fix is released
- Credit will be given to the reporter unless they request otherwise

If the vulnerability is declined:

- We will provide a clear explanation of the decision

### Responsible disclosure

We kindly ask reporters to follow **responsible disclosure practices** and not
to publicly disclose the vulnerability until a fix has been released or an
agreement has been reached.

---

## Threat Model and Assumptions

This project is designed under the following security assumptions:

- A compromise of the underlying server, operating system, or runtime
  environment (including root or equivalent access) is considered
  **out of scope**.
- An attacker with full control over the host is assumed to be able to access
  process memory and therefore cryptographic material by design.

The security model focuses on:

- Preventing unauthorized access through the application layer
- Enforcing strict authentication and authorization rules
- Protecting secrets at rest through cryptographic mechanisms
- Limiting blast radius in case of partial compromise

Reports that assume full host or infrastructure compromise without an
application-layer vulnerability may be declined as out of scope.

---

## Security Scope

The following components are **in scope** for security reports:

- Backend services (authentication, authorization, cryptography, API logic)
- Secret storage, encryption, and key management mechanisms
- Access control and permission enforcement
- CI/CD pipelines and deployment configuration
- Infrastructure-as-code related to security

The following are **out of scope**:

- Denial of Service (DoS) attacks without demonstrated impact
- Issues caused by misconfiguration of self-hosted deployments
- Social engineering attacks
- Vulnerabilities in third-party dependencies without a demonstrable impact
  on this project

---

## Cryptography Notice

This project implements **server-side encryption and key management**.

- No encryption keys or key shares are ever intentionally stored in this
  repository.
- Any issue related to key exposure, key lifecycle, or cryptographic misuse
  is considered **high severity**.

Please report such issues immediately using the channels described above.

---

## Threat Model Summary

We assume:

- The server-side runtime is trusted unless an application-layer vulnerability is demonstrated.
- The attacker may obtain database read access and should not be able to recover plaintext secrets from stored data alone.

We aim to protect against:

- Unauthorized access to secrets through broken authentication/authorization
- Data disclosure from storage compromises (e.g., database leaks)
- Accidental leakage through logs, telemetry, or backups

---

## Attack Scenarios & Mitigations

This section documents specific attack scenarios considered in our threat model
and the assumptions or mitigations in place.

### Scenario 1: Unsealing Attacks

**Assumption**: Network access to the application is strictly controlled
(VPN, firewall, or trusted network environment).

**Risk**: The vault unsealing endpoint (`/api/vault/unlock`) does not require
authentication. Anyone with network access can attempt to unseal the vault by
submitting Shamir shares.

**Rationale**: Unsealing must occur before users can authenticate, as the
encryption key is needed for application functionality.

**Mitigations**:

- Deploy behind VPN, reverse proxy with IP restrictions, or within a trusted network only
- All unsealing attempts are logged via audit events
- Monitor unsealing patterns for anomalies
- Rate limiting may be implemented in future versions
- Consider additional authentication layer for unsealing in high-security deployments

**Recommended deployment practice**: Restrict network access to trusted
administrators only during unsealing operations.

---

### Scenario 2: Memory Access to Encryption Key

**Classification**: Out of scope (by design).

**Risk**: The decrypted encryption key is stored in process memory
(`InMemoryVaultSessionGateway`). An attacker with process memory access
(e.g., via debugger, core dump, memory scraping) can extract this key.

**Architecture decision**: This is an accepted limitation. An attacker with
memory access to the running process has already compromised the runtime
environment, which is outside our threat model (similar to HashiCorp Vault's
position: <https://github.com/hashicorp/vault/issues/1446>).

**Mitigations in place**:

- Vault can be locked (`/api/vault/lock`) to clear the key from memory when not in use
- Only administrators can lock the vault
- Minimize the duration the vault remains unlocked in production

**Deployment recommendations**:

- Deploy in hardened, isolated environments
- Disable core dumps (`ulimit -c 0`)
- Use memory protection features of the operating system where available
- Implement regular vault locking during periods of inactivity
- Monitor for unauthorized process access attempts

---

### Scenario 3: Lock/Unlock State Not Shared Across Backend Replicas

**Classification**: Known limitation, not currently exploitable — only a
single backend replica is deployed today (`replicaCount: 1` in
`helm/le-coffre/values.yaml`). Documented ahead of enabling horizontal
scaling, which the Helm chart already supports (`values-example.yaml` sets
`replicaCount: 2` and enables autoscaling up to 5, as a documented example
for production).

**Risk**: The decrypted vault key and the locked/unlocked state both live in
each backend process's own memory (`InMemoryVaultSessionGateway`), with no
shared store or cross-instance signal. If more than one backend replica runs
behind the load balancer, each replica has its own independent copy of this
state:

- An administrator locking the vault only clears the key on whichever replica
  handled that request. Every other replica keeps serving decrypted
  passwords as if nothing happened, until it is separately locked (or
  restarted).
- Symmetrically, two replicas can each independently reconstruct the key
  from concurrently-submitted Shamir shares and each publish their own
  unlock event.
- Every replica also independently locks the vault on its own startup
  (`_record_vault_locked_on_startup` in `main.py`), since the decrypted key
  never survives a restart. A rolling restart with `replicaCount: 2` means
  two replicas start in short succession, so this is not a one-off: each of
  the two "server start" locks emails opted-in users again, and — because
  the read of the last recorded event and the write of the new one aren't
  atomic — the two replicas' `get_last_event_type` reads can both land before
  either has appended its own `VaultLockedEvent`, so both conclude the vault
  was last unlocked and both report a lock, even though only the very first
  replica up actually changed anything.

This defeats the operational purpose of "lock the vault" as an emergency
control (e.g. during a suspected intrusion or an offboarding): the
administrator has no way to know, from the UI, that the vault is still
usable through other replicas, and the lock action gives no such warning.

Per-request atomicity fixes (e.g. the check-and-clear on
`InMemoryVaultSessionGateway.clear_decrypted_key`) do not address this: they
only serialize concurrent requests handled by the *same* process, which
shares nothing with sibling replicas.

**Mitigation required before scaling past one replica** (not implemented):
move the decrypted key and the lock state out of per-process memory into a
store shared by every replica (e.g. Redis, or a locked SQL row), and/or add a
cross-instance signal (pub/sub, polling a shared flag) so that a lock on one
replica causes every replica to drop its in-memory key immediately. The
startup-lock bookkeeping needs its own fix along the same lines: make the
read of the last vault event and the append of the new one atomic (e.g. a
row lock or a unique constraint on "one server-start lock per boot"), so a
rolling restart records and emails one lock, not one per replica.

**Interim mitigation**: keep `replicaCount: 1` (and `autoscaling.enabled:
false`) for the backend until the above is implemented. Scaling the
*frontend* independently is unaffected, since it holds no vault state.

---

### Scenario 4: Insider Threats & Access Abuse

**Classification**: Partially in scope.

**Risks**:

- Legitimate user exfiltrates all passwords they have access to
- Group owner shares passwords with unauthorized groups
- Collusion between users to aggregate access
- Mass password retrieval without business justification

**Protections in place**:

- All password access operations emit audit events (create, read, update, delete, share, unshare)
- Group-based permissions limit blast radius
- Only group owners can share passwords
- Audit trail records who accessed what and when

**Detection & response**:

- Review audit logs regularly for unusual access patterns
- Monitor for mass password retrievals
- Investigate unexpected sharing activities
- Implement alerting on suspicious patterns (future enhancement)

**Out of scope**: A trusted user intentionally exfiltrating data they
legitimately have access to cannot be prevented at the application layer.
This is a broader organizational security concern requiring procedural
controls, monitoring, and least-privilege access policies.

---

### Scenario 5: Session Hijacking

**Classification**: In scope.

**Risk**: Stolen authentication tokens (`access_token` cookie) grant full
access to passwords until session expiration.

**Protections required** (deployment-specific):

- HTTPS/TLS mandatory for all connections
- Secure cookie flags (`Secure`, `HttpOnly`, `SameSite`)
- Short session timeouts recommended
- Consider IP binding or device fingerprinting for sensitive deployments

**Application-layer security**: Session management relies on standard web
security practices. Report any bypasses of authentication or authorization
checks as vulnerabilities.

---

### Scenario 6: Shamir Share Compromise

**Assumption**: Fewer than N shares are compromised.

**Risk**: If an attacker obtains N or more shares, they can reconstruct the
master key and decrypt the encryption key from the database, gaining access
to all passwords.

**Critical security guidance**:

- **Never store N or more shares in the same location**
- Store shares in physically separate, secure locations
- Use different custodians for each share
- Do not store shares electronically together (e.g., all in the same password manager)
- Prefer threshold values where N ≥ 3 for production deployments
- Do not commit shares to version control or backup systems
- Treat each share as highly sensitive cryptographic material

**Share distribution best practices**:

1. Generate shares during initial setup
2. Distribute to N different trusted administrators
3. Each administrator stores their share securely and separately
4. Document the share holders (without recording the shares themselves)
5. Establish a secure process for share usage during unsealing
6. Consider periodic share regeneration (not yet implemented)

**Out of scope**: Physical compromise of share storage locations or coercion
of share holders.

---

### Scenario 7: Database Compromise (Read-Only)

**Classification**: In scope - this is a primary design goal.

**Risk**: Attacker gains read access to the database containing encrypted
passwords and the encrypted encryption key.

**Protections in place**:

- All passwords encrypted with AES-256-GCM using unique IVs
- Encryption key itself is encrypted with the master key (derived from Shamir shares)
- Master key is never stored; must be reconstructed from shares
- Without N shares, the attacker cannot decrypt the encryption key
- Without the encryption key, individual passwords remain encrypted

**Result**: Database read access alone should not reveal plaintext passwords,
assuming Shamir shares are properly secured.

**Related vulnerability class**: Attacks that bypass encryption, expose keys
in logs, leak plaintext through error messages, or otherwise violate
encryption guarantees should be reported as high-severity vulnerabilities.

---

### Scenario 8: Supply Chain & Dependency Attacks

**Classification**: Partially in scope.

**Risk**: Compromised dependencies introduce vulnerabilities or backdoors.

**Mitigations**:

- Regular dependency updates via automated tooling
- Use of well-established cryptographic libraries (PyCryptodome)
- Code review for suspicious dependency behavior
- Reproducible builds (future enhancement)

**Reporting**: Vulnerabilities in direct dependencies with demonstrable
impact on Le Coffre should be reported. Generic dependency CVEs without
proven impact may be declined.

---

For details about the cryptographic design and key management model,
please refer to: [CRYPTOGRAPHIC_ARCHITECTURE.md](CRYPTOGRAPHIC_ARCHITECTURE.md)
