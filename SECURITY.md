# Security upgrade

ZigLag is built on stk 17, installed as the `stkit` package (17.15.1 in `uv.lock`),
and requires quart-security 2.4.0 as locked. It no longer vendors stk. The
dependency versions are recorded in `uv.lock`.

## Upgrading an existing deployment from the stk 16 based release

Stop the application during the upgrade. Back up the database, `instance/invoices/`,
uploaded logos (`stk/static/uploads/`), `.env`, and any encryption keys. Then:

1. Move `stk/static/uploads/*` to `ziglag/static/uploads/`. Logos now live in the
   app package. With Docker Compose, the previous stack bind-mounted `./stk` from the
   host, so copy the files from there into the `logo-data` volume, which is mounted at
   `/app/ziglag/static/uploads`. `instance/invoices/` and the default SQLite database
   `instance/ziglag.db` do not move.
2. Update the proxy. Nginx and Caddy must pass `/static/` to the app instead of
   reading `stk/static` from disk. The `nginx/` files in this repository already do.
3. Install with `uv sync --frozen --extra full`.
4. Adopt the existing database. stk 17 starts a new migration history and does not
   upgrade a database created by stk 16. The database must be at revision
   `20261006_0002`, the head of ZigLag 0.2.0. The command refuses any other revision
   and refuses a second run. It was tested on SQLite only. On PostgreSQL, rehearse it
   on a restored copy first. If it fails partway, restore the backup.

```sh
uv run stk adopt-stk16
```

5. Apply migrations and protect MFA seeds:

```sh
uv run stk db upgrade
uv run stk protect-mfa
```

Run these commands only after approving the target environment. Start the
application after both commands complete.

Behaviour changes that come with stk 17 and apply to ZigLag:

- Emails are stored trimmed and lowercased, and login matches them regardless of
  case. Existing rows keep their stored case and still sign in, but two rows whose
  emails differ only by case make login for that address fail. Find them with
  `uv run stk shell -c "await sql('select lower(email), count(*) from \"user\" group by 1 having count(*) > 1')"`
  and merge or rename one. An account stored with a decomposed Unicode or punycode
  email must be rewritten with `quart_security.normalize_email` to sign in; ASCII
  addresses are unaffected.
- A session older than an hour that opens Change Password, Two-Factor Auth, Recovery
  Codes or passkey settings goes to `/verify` to enter its password or use a passkey,
  then returns to the page.
- Migration `stk_0007` marks every existing account confirmed.
- Password reset by email at `/reset` turns on once `MAIL_SERVER` and `STK_PUBLIC_URL`
  are both set (`SECURITY_RECOVERABLE` overrides). Reset links work once, for one
  hour, and a reset signs out every session. Public sign-up stays off because ZigLag
  sets `SECURITY_REGISTERABLE = False`.
- When an admin changes a user's email, the user is signed out everywhere.
- A locked account fails login with the same message as a wrong password.
- A TOTP secret under 112 bits fails like a wrong code and logs which user to reset,
  instead of a server error.
- Auth mail links are built from `STK_PUBLIC_URL`, never the request Host header. Set
  it in production.

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

The Docker Compose stack refuses to start without unique `DB_ADMIN_PASSWORD`,
`DB_PASSWORD`, `REDIS_PASSWORD`, `STK_HOST`, `TLS_CERTIFICATE`, and
`TLS_PRIVATE_KEY`, and publishes only ports 80 and 443 through Nginx. An existing
PostgreSQL volume needs a privilege review, because the non-superuser app role is
created only on a new volume. The stack still needs a deployment review before
production use. This framework upgrade does not establish production readiness.
