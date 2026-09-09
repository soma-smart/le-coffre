# Privacy policy, Le Coffre browser extension

Last updated: 9 September 2026. Applies to the "Le Coffre" browser extension
only, not to the Le Coffre server, which you host yourself.

## The short version

The extension talks to exactly one server: the Le Coffre vault whose address
you type into it. SOMA operates no server for this extension, receives no data
from it, and has no way to observe your use of it. There is no analytics, no
telemetry, no crash reporting, no advertising, and no third-party service of
any kind. The extension loads no code, fonts or images from anywhere but its
own bundle.

## What it stores, and where

Nothing leaves your browser except the requests you trigger against your own
vault.

Persisted to disk, kept until you disconnect or uninstall:

- the vault address you entered
- the exact host permission you granted, so it can be checked and revoked
- the group you selected in the settings
- the read-only access token issued when you paired, and its expiry date
- the device name reported at pairing, and your extension settings

Kept in memory only, discarded when the browser closes:

- the pairing in progress: its code, its PKCE verifier and its deadline
- a short-lived cache of entry metadata, about sixty seconds. It holds names,
  folders, logins and URLs, never a password. It is deliberately kept out of
  disk storage because a login and a URL together reveal which sites you hold
  accounts on
- the timestamp of your last authenticated call, which drives the idle lock

**Decrypted passwords are never stored, anywhere.** They are fetched on demand,
written to the clipboard, and dropped. They never enter the popup's UI code.

## The clipboard

Copying a login or a password writes it to your system clipboard, then clears
it after the delay configured in the extension by overwriting it with a single
space. The extension requests `clipboardWrite` and never `clipboardRead`: it
cannot see anything you copy elsewhere. Because it cannot read the clipboard,
it also cannot check whether its value is still there before clearing, so
something you copied in the meantime may be overwritten.

While a secret is on the clipboard it is readable by any application on your
computer. That is a property of clipboards, not of this extension.

## What your vault records

Revealing a password calls your own vault, which writes an entry in its own
audit log, exactly as the web application does. That log lives in your
self-hosted instance and is visible to you and your administrators. Listing
groups and entries reads metadata and is not audited as an access to a secret.

## Permissions, and why each one is needed

- **`storage`**: to keep the items listed above.
- **`alarms`**: the extension's background worker is stopped by the browser
  after a few seconds of inactivity, so timers cannot be used. Alarms drive the
  pairing poll and the idle lock.
- **`clipboardWrite`**: to copy a login or a password, and to clear it.
- **`offscreen`**: the clipboard write needs a page that outlives the popup,
  otherwise the automatic clearing would not happen when you dismiss the popup,
  which is the normal case.
- **Host access, requested at runtime, never at install**: your vault is
  self-hosted, so its address cannot be known when the extension is built. The
  extension therefore declares no host permission at install time and asks for
  the single narrowest pattern covering your vault's API once you have typed
  its address. You can withdraw it at any time from your browser's extension
  settings.

The credential the extension holds is read-only and never carries
administrator rights, whatever your role in the vault is. It cannot create,
modify, delete or share anything, and it cannot manage your connected devices.

## Removing your data

- **Disconnect** in the extension clears everything listed above and revokes
  the host permission.
- **Uninstalling** the extension deletes all of it with the extension.
- **Revoking from the vault** (your profile page, or changing your account
  password, or deleting your account) invalidates the token server-side even if
  the extension is still installed.

Tokens also expire on their own thirty days after pairing, with no renewal.

## Source code and contact

The extension is open source under the MIT licence, at
<https://github.com/soma-smart/le-coffre>, in the `extension/` directory. Its
design, including the reasoning behind each of the choices above, is documented
in `extension/README.md`.

Questions and privacy requests: open an issue on that repository. Security
vulnerabilities: use GitHub's private vulnerability reporting, as described in
`SECURITY.md`. Please do not report vulnerabilities in a public issue.
