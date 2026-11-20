# Le Coffre, command-line and other non-browser clients

Le Coffre ships no CLI. This page is the contract any command-line tool,
script or desktop app must follow to read from the vault on behalf of a person.
Automations that run without a person (CI pipelines, bootstrap scripts,
operators) use a group's service account instead.

## The one rule

**A non-browser client never signs in like the web app.** It pairs, exactly
like the [browser extension](../extension/README.md#how-it-authenticates), and
holds a read-only bearer token. It never holds a session cookie.

The SSO callback used to accept a `?redirect_uri=` override, so a CLI could
catch the authorization code on a loopback listener and leave with a full web
session: access and refresh cookies, write and admin rights, a sliding refresh,
and nothing on the connected-devices screen. That override is gone.
`GET /api/auth/sso/callback?…&redirect_uri=…` now answers **400** and names the
pairing endpoint, and a code issued to a loopback listener cannot be redeemed
against the vault's own redirect URI either. CLIs built on that flow no longer
work. That is intended.

## How it authenticates

1. **Register.** `POST /api/extension/device` with a PKCE S256 challenge and a
   device name. You get back a `user_code` (`K7QM-3XR9`), its expiry (10
   minutes) and the `poll_interval_seconds` to honour. No authentication is
   needed: the request grants nothing on its own.
2. **Approve.** Print the code and the URL `{vault}/extension/connect`, with no
   query and no fragment. The user signs in there the usual way (password or
   SSO), types the code, sees the requesting IP and what the credential can do,
   and approves or refuses. Never put the code in the URL: the ceremony rests on
   the user carrying it across themselves.
3. **Exchange.** Poll `POST /api/extension/device/exchange` with `user_code` and
   `code_verifier` every `poll_interval_seconds`. It answers
   `{"status": "pending"}` until approval, then `{"status": "approved",
   "token": …, "expires_at": …}` **exactly once**. Only the token's SHA-256 is
   stored server-side: lose that response and you pair again.
4. **Use.** Send `Authorization: Bearer <token>`.

## What the token can do

| | |
|---|---|
| Rights | Read-only. Never admin, whatever the user's role. Any `POST`, `PUT`, `PATCH` or `DELETE` carrying a bearer is refused with 403 before routing. |
| Routes | `GET /api/extension/session`, `GET /api/extension/groups`, `GET /api/passwords/list`, `GET /api/passwords/{id}`. Everything else answers 401. |
| Lifetime | 30 days absolute (`EXTENSION_TOKEN_LIFETIME_DAYS`), no refresh. |
| Inactivity | Stops working after 14 days unused (`EXTENSION_TOKEN_INACTIVITY_DAYS`). |
| Cap | 5 active tokens per user, shared with browser extensions. |
| Revocation | From the web app's profile page (one device or all), by an admin, by changing the account password, by deleting the account, or by expiry. |

Re-pairing is the only way back after expiry or revocation.

### Why a CLI gets the same lifetime as the extension

The device name is self-reported. The server cannot tell a CLI from a browser
extension, and a client that wants the longer lifetime only has to claim the
other name. A per-client policy would be a convention, not a control, so there
is a single policy for every paired device. To shorten it, lower the two
variables above: they apply to everything that pairs.

## Rules a client must follow

- **Honour the server's poll interval.** The pairing endpoints are anonymous and
  share a per-IP rate bucket sized for that cadence. Polling faster gets 429 for
  everyone behind the same NAT.
- **Only a definitive 400 ends a pairing.** On a 429, a dropped connection, a
  503 or a locked vault, keep the verifier and keep polling until the expiry.
- **Keep the token in the OS keychain** (macOS Keychain, Windows Credential
  Manager, Secret Service on Linux), not in a dotfile, an environment variable
  or a shell history. Never print it.
- **Send a recognisable device name**, such as `coffre-cli on alice-laptop`. It
  is what the user sees on the approval page and in their device list.
- **Ship it outside the vault.** Publish a CLI through signed releases or a
  package manager, the way the extension goes through the Chrome Web Store. A
  binary served by the vault turns a compromised instance into a compromised
  workstation for every user who downloads it.

## Minimal example

```sh
VAULT=https://coffre.example.com

verifier=$(openssl rand -base64 48 | tr '+/' '-_' | tr -d '=\n')
challenge=$(printf %s "$verifier" | openssl dgst -sha256 -binary | openssl base64 | tr '+/' '-_' | tr -d '=\n')

pairing=$(curl -sf -X POST "$VAULT/api/extension/device" \
  -H 'Content-Type: application/json' \
  -d "{\"code_challenge\":\"$challenge\",\"code_challenge_method\":\"S256\",\"device_name\":\"coffre-cli on $(hostname)\"}")
code=$(echo "$pairing" | jq -r .user_code)
interval=$(echo "$pairing" | jq -r .poll_interval_seconds)

echo "Open $VAULT/extension/connect and enter $code"

while :; do
  sleep "$interval"
  result=$(curl -sf -X POST "$VAULT/api/extension/device/exchange" \
    -H 'Content-Type: application/json' \
    -d "{\"user_code\":\"$code\",\"code_verifier\":\"$verifier\"}") || exit 1
  [ "$(echo "$result" | jq -r .status)" = approved ] && break
done

token=$(echo "$result" | jq -r .token)   # store it in the keychain, not here
curl -sf "$VAULT/api/passwords/list" -H "Authorization: Bearer $token"
```

This loop gives up on any error, 429 included, which a real client should not
do (see the rules above).

## Where it lives

- Pairing and tokens: `server/src/identity_access_management_context/`,
  `application/use_cases/extension/` and `adapters/primary/fastapi/routes/extension/`.
- Approval page: `frontend/src/pages/ExtensionConnectPage.vue`.
- The refused CLI SSO flow is pinned by PHASE 8 of
  `server/tests/e2e/test_complete_authentication_workflow.py`, and pairing
  by PHASE 9.
