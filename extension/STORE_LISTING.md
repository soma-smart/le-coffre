# Chrome Web Store listing

The copy to paste into the developer console, kept here so a resubmission does
not mean rewriting it. Permission justifications are **not** duplicated here:
they live in `README.md`, section "Publishing to the Chrome Web Store", next to
the code that explains them.

Open decisions, to settle before submitting: whether to publish as `0.1.0` or
`1.0.0`, and whether to keep `http://*/*` in the optional host permissions.

## Summary

Taken automatically from `manifest.description`, 83 of the 132 characters
allowed. Nothing to paste.

> Read-only access to the passwords of one group in your self-hosted Le Coffre
> vault.

## Detailed description

The first line is deliberately the requirement, not a feature. Someone who
installs this without a vault gets an extension that cannot do anything, and a
reviewer who does not read that line files it as broken.

> **Requires a Le Coffre server that you host yourself.** Le Coffre is an
> open-source, self-hosted password manager for teams. This extension is a
> companion to it, not a standalone password manager.
>
> It gives you read-only access to the passwords of one group of your vault,
> from the toolbar, without opening the web application.
>
> - **Copy a login or a password in one click.** The password is fetched only
>   when you ask for it, and the clipboard is cleared automatically shortly
>   after.
> - **Search inside the group you chose**, by name, folder, login or address.
> - **Add or edit** opens the entry in your vault's web application. The
>   extension never writes anything.
>
> **What it can never do**, whatever your role in the vault is: create, modify,
> delete or share anything, read the passwords of groups you do not belong to,
> or manage your connected devices. The credential it holds is read-only and
> never carries administrator rights.
>
> **It never sees your password.** Connecting it works like pairing a device:
> the extension shows a code, your vault opens in a tab, you sign in there the
> way you usually do, including through your company's single sign-on, and you
> approve the request after checking that the code matches. The extension
> receives a credential that lasts 30 days, that you can revoke at any moment
> from your profile page, and that is revoked automatically if you change your
> account password or your account is deleted.
>
> **No host permission is requested at install.** Your vault's address is
> yours, so it cannot be known in advance. The extension asks for access to
> that one address, and only once you have typed it.
>
> No account with us, no analytics, no telemetry, no third-party service. The
> only server it ever contacts is your own vault. Source code, under the MIT
> licence: https://github.com/soma-smart/le-coffre
>
> Autofill is not implemented yet.

## Single purpose

The console asks for one statement. Keep it narrow, this is the policy that
rejects extensions doing two unrelated things.

> Read-only access to the passwords of a single group of a self-hosted Le Coffre
> vault, so the user can copy a login or a password without opening the web
> application.

## Category and language

Category: **Productivity**. Language: **English**, the interface is English
only; there is no `_locales` directory yet.

## Data usage disclosures

Every box has to be answered and the whole form certified; leaving it blank
blocks the submission.

- Personally identifiable information: **no**. The extension stores the email
  and display name returned by the user's own vault, in that user's browser
  only. Nothing is transmitted to us, because we operate no server.
- Health, financial, authentication information: **authentication information,
  yes.** It holds a read-only access token for the user's own vault, and it
  writes passwords to the clipboard on request. Both stay on the user's
  machine.
- Personal communications, location, web history, user activity: **no**.
- Website content: **no**. It reads no page. There is no content script.
- Certifications to accept: the data is not sold to third parties, is not used
  for purposes unrelated to the single purpose above, and is not used to
  determine creditworthiness or for lending.

Privacy policy URL: see `PRIVACY.md`, which has to be served from a URL before
it can be pasted here.

## Notes for the reviewer

Without this, the review stalls: the first screen asks for the address of a
self-hosted server the reviewer does not have.

> This extension is a client for Le Coffre, a self-hosted open-source password
> manager. It cannot be tested without a Le Coffre server, so here is a test
> instance:
>
> - Vault address to enter on the extension's first screen: <URL>
> - Test account: <email> / <password>
>
> Flow to follow: click Connect, the extension shows a code and opens a tab on
> the vault, sign in with the account above, check that the code matches, click
> Approve. The extension then lists the passwords of the selected group, and
> the copy buttons work.
>
> Notes on the permissions, detailed in the privacy policy:
>
> - No host permission is declared at install time. The extension declares
>   `optional_host_permissions` and requests, at runtime, the single narrowest
>   pattern covering the API of the address the user typed. The vault is
>   self-hosted, so its origin cannot be known when the extension is built.
> - The bundle loads no remote code: no external script, style, font or image.
>   The build fails on an inline script or an `eval` (`scripts/validate-manifest.ts`).
> - The credential the extension obtains is read-only server-side and the
>   administrator role is stripped from it. Four routes accept it, all of them
>   reads.
>
> Full source, MIT licence: https://github.com/soma-smart/le-coffre, directory
> `extension/`.

## Screenshots

At least one, 1280x800 or 640x400, up to five. The popup is 380px wide, so it
has to be **composed** on a background rather than captured as-is; a raw
capture is a small strip in a corner.

Worth showing, in this order:

1. The entry list with the copy buttons, the screen people spend their time on.
2. The pairing screen next to the vault's approval page, which is the whole
   anti-phishing ceremony and the least obvious part of the product.
3. The settings screen with the group picker.
4. The first screen, where the vault address is entered, since it is what makes
   the self-hosted requirement obvious.
