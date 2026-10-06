# Security upgrade

ZigLag vendors stk 16.0.0 from upstream commit
`55706d91afdf42651d33468548373ebe0f6ca9b7` and requires Quart-Security 2.0.1.
The dependency versions are recorded in `uv.lock`.

## Existing deployments

Stop the application during the upgrade. Back up the database, archived invoices,
and encryption keys. Install with `uv sync --frozen --extra full`, then run:

```sh
uv run stk db upgrade
uv run stk protect-mfa
```

Run these commands only after approving the target environment. The migrations
add `quart_security_state` and `rate_limit_window` after `20260712_0002`.
Old login cookies are invalidated. `protect-mfa` encrypts dormant MFA seeds.
Start the application after both commands complete.

Keep `SECRET_KEY` stable. By default, MFA encryption uses a key derived from it.
An independent `SECURITY_TOTP_ENCRYPTION_KEYS` keyring can contain comma-separated
Fernet keys, with the current write key first. Preserve all keys needed to read
existing seeds and restore backups. When moving from the default derived key,
include `derive_totp_encryption_key(old_secret_key)` in the keyring until rotation
is complete and pending setup states have expired. A wrong key fails closed.

## Request and authentication controls

Application mutations require a CSRF token. Axios receives the token from the
shared layout. Custom session clients must obtain a token from a rendered page
and send it as `X-CSRFToken`. Invoice send and share actions can have empty bodies;
they still require CSRF protection.

New passwords use Argon2id. Existing password hashes remain readable. OAuth uses
single-use state, PKCE, verified identities, and local MFA and lockout controls.
OAuth no longer links an existing account by email alone. Review provider links
created before this upgrade. Legacy provider tokens are not removed by this code.

Authentication limits use shared SQL state. WebSocket connections have bounded
queues and lifetimes, origin checks, and session revocation checks. Broadcasts
require an explicit recipient.

## Deployment requirements

Use HTTPS, secure cookies, unique application and database secrets, and a trusted
reverse proxy. Set `STK_PUBLIC_URL`, `SECURITY_WAN_RP_ID`, and
`SECURITY_WAN_EXPECTED_ORIGIN` to the deployed HTTPS host and origin. For local HTTP
development, explicitly set `SESSION_COOKIE_SECURE=False`.

The existing Docker Compose configuration still publishes database and Redis
ports and permits default passwords. It needs a separate deployment review before
production use. This framework upgrade does not establish production readiness.

The migration drift check also reports existing differences in nullability and
server defaults for invoice tax treatment and template fields. Resolve those
separately before requiring a clean migration drift gate.
