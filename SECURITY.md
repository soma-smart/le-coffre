# Security Policy

## Supported Versions

Only the latest **minor release of the current major version** is supported
with security updates.

Security fixes are **never backported** to unsupported versions.

| Version | Supported |
| ------- | --------- |
| >= 0.6.0 (latest) | :white_check_mark: |

If you are running an unsupported version, you are strongly encouraged to
upgrade before reporting a vulnerability.

---

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

### How to report

To report a security vulnerability, please use the **GitHub Private Vulnerability Reporting** feature:

1. Navigate to: https://github.com/soma-smart/le-coffre/security/advisories/new
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

For details about the cryptographic design and key management model,
please refer to: [CRYPTOGRAPHIC_ARCHITECTURE.md](CRYPTOGRAPHIC_ARCHITECTURE.md)
