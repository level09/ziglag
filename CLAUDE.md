# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is ZigLag

Self-hosted invoicing application built on vendored stk 16.0.0. The stack uses async Quart, SQLAlchemy 2, Vue 3, Vuetify 4, quart-security 2.0.1, Alembic, and fpdf2. SQLite is the local default. Production deployments use PostgreSQL, Redis, Caddy, systemd, and the stk deploy script.

ZigLag issues PDF invoices with German and EU B2B safeguards. It does not yet generate XRechnung or ZUGFeRD.

## Working Rules

- Keep changes minimal. Every changed line must trace to the request.
- Name a remote environment and wait for confirmation before running commands against it.
- Show destructive remote, database, filesystem, or Git commands and wait for explicit approval.
- Use one-line conventional commit messages. Do not mention AI in commits or pull requests.
- Stage only changed files by explicit path.
- Do not use em dashes or en dashes in published text.
- Ask `plan or implement?` only when the request does not make the mode clear.
- Find canonical configuration sources instead of hardcoding replacement values.
- Match existing stk patterns: async Quart, request-scoped sessions, Vue Options API, and `${}` delimiters.
- Use `uv` for Python commands and Ruff for formatting.

## Commands

```bash
./setup.sh                        # First-time setup (venv, deps, .env)
uv sync --extra dev               # Install with dev tools
uv run quart create-db            # Apply all migrations (upgrade to head)
uv run quart run --port 5001      # Dev server (5001 avoids macOS AirPlay on 5000)
uv run ruff check --fix . && uv run ruff format .  # Lint + format
uv run python checks.py           # Sanity checks (not pytest)
docker compose up --build          # Full stack (Redis, PostgreSQL, Nginx)
uv run python -m unittest discover -s tests -v  # Unit tests
uv run quart verify --json         # stk verification report
uv run quart inspect context --json  # Routes and models report
```

First run: `setup.sh` -> `create-db` -> `quart run` -> open browser -> `/setup` creates admin account.
CLI alternative: `uv run quart install -e admin@example.com -p yourpassword`

### Database Migrations (Alembic)

```bash
uv run quart db upgrade [revision]              # Apply migrations (default: head)
uv run quart db downgrade <revision>            # Rollback (e.g. -1 for one step)
uv run quart db revision -m "description"       # Autogenerate new revision
uv run quart db revision -m "desc" --empty      # Empty revision for manual SQL
uv run quart db current                         # Show current revision
uv run quart db history                         # Show migration history
uv run quart db stamp head                      # Adopt Alembic on existing DB
```

Migration config lives in `stk/migrations.py`. Alembic env in `alembic/env.py`. Revisions in `alembic/versions/`. SQLite uses batch mode automatically for ALTER TABLE support.

Current migration chain:

```text
20260326_0001 -> cfa8efad03ed -> 228ac4e0ebf5 -> 20260712_0001 -> 20260712_0002 -> 20261006_0001 -> 20261006_0002
```

## Architecture

### Async SQLAlchemy (not flask-sqlalchemy)

Engine and session factory live in `stk/extensions.py` as module-level globals (`ext.engine`, `ext.async_session_factory`). No `db` object. Models inherit from `Base` (plain `DeclarativeBase`), not `db.Model`.

Request-scoped sessions via `g.db_session`, created in `before_request`, closed in `after_request` (see `stk/app.py`).

```python
# In request handlers: use g.db_session
from quart import g
from sqlalchemy import select
result = await g.db_session.execute(select(User).where(User.active == True))
users = result.scalars().all()

# In CLI commands: use ext.async_session_factory directly
import stk.extensions as ext
async with ext.async_session_factory() as session:
    ...
```

All relationships must use `lazy="selectin"` for async compatibility.

### CLI Commands

Sync click commands wrapping `asyncio.run()` in `stk/cli/`. `stk/commands.py` preserves compatibility imports. Quart CLI doesn't support async click commands. The `db` group is a click.Group with Alembic subcommands. All commands are auto-registered via `register_commands()` in `app.py`.

### Blueprints

- `stk/public/` - unauthenticated routes, OAuth callbacks (Google, GitHub)
- `stk/user/` - auth, login, registration, OAuth, WebAuthn, 2FA, session management
- `stk/portal/` - protected dashboard (blueprint-level `@auth_required`)
- `stk/invoicing/` - clients, invoices, payments, PDF generation, reports, settings
- `stk/invoicing/public.py` - tokenized public invoice view and archived PDF delivery
- `stk/websocket.py` - WebSocket blueprint (releases DB session early for long-lived connections)

### Auth (quart-security)

`SQLAlchemyUserDatastore` with `ext.async_session_factory`. The application uses the datastore session as `g.db_session`. Key decorators: `@auth_required("session")`, `@roles_required('admin')`.

**Features enabled:**
- Session auth with tracking (IP, device, browser via `Session` model)
- 2FA via TOTP authenticator (`SECURITY_TWO_FACTOR = True`)
- WebAuthn as first or multi-factor (`SECURITY_WEBAUTHN = True`)
- OAuth (Google, GitHub) via AuthLib `AsyncOAuth2Client`
- Password hashing: Argon2id, min 12 chars; legacy hashes remain readable
- Account lockout: `failed_login_count` + `locked_until` on User model
- Recovery codes (3 codes)
- Session freshness: 60-minute window

**Signal handlers** (all async, in `stk/user/views.py`):
- `@user_authenticated.connect` - creates session record, tracks IP changes
- `@user_logged_out.connect` - deactivates session
- `@password_changed.connect` - logs change, marks password as user-set
- `@tf_profile_changed.connect` - logs 2FA modifications

**Rate limiting** uses `quart-rate-limiter`, initialized in `stk/app.py` and applied to the authentication blueprint.

### Models (`stk/user/models.py`)

- **User** - UserMixin. Auth fields, login tracking, lockout, 2FA, WebAuthn handle. Methods: `from_dict()`, `to_dict()`, `random_password()`, `logout_other_sessions()`, `get_active_sessions()`.
- **Role** - RoleMixin. Many-to-many with User via `roles_users`.
- **WebAuthn** - credential storage, FK to User via `fs_webauthn_user_handle`.
- **OAuth** - provider accounts linked to users. Unique on `(provider, provider_user_id)`.
- **Activity** - audit log. `register()` logs + broadcasts via WebSocket.
- **Session** - tracks active sessions with IP, device meta, expiry.

### Invoicing Models (`stk/invoicing/models.py`)

- **BusinessSettings** - legal identity, tax defaults, numbering, currency, template, payment instructions.
- **Client** - contact details and VAT ID.
- **Invoice** - draft and issued lifecycle, legal snapshots, tax treatment, totals, archive path.
- **InvoiceItem** - description, detail, quantity, unit price, taxable flag.
- **Payment** - amount, date, method, and notes.

Draft invoices are editable and deletable. Issuing, sending, or advancing a draft to another issued state validates it, snapshots legal and customer data, writes the final PDF once, and locks invoice content. Issued invoices cannot return to draft or be deleted. Cancellation is terminal.

Tax treatments are `standard`, `reverse_charge`, and `exempt`. Reverse charge prints an Article 196 statement and requires supplier and customer VAT IDs. The application does not determine whether Article 196 applies. Exempt invoices require a reason.

Invoice templates are `precision`, `branded`, and `editorial`. Business settings provide the default; drafts may override it. `stk/invoicing/presentation.py` owns template definitions and tax wording.

Issued PDF files live under `instance/invoices/<user_id>/<invoice_id>/invoice-<invoice_id>.pdf`. Backups must include the database and this directory.

### Background Tasks

No Celery. `stk/tasks.py` provides:
- `run_in_background(coro)` - fire-and-forget with exception logging
- `run_with_session(coro_factory)` - provides fresh DB session to coroutine
- `cleanup_expired_sessions()` - deactivates expired, deletes 30+ day old records

### Frontend

Vue 3 + Vuetify loaded from static files. **Custom delimiters `${` and `}` to avoid Jinja conflicts.** Every Vue app must set `delimiters: config.delimiters`. Server data passed via `<script type="application/json">` tags.

### Production Deployment

Use stk's `deploy.sh` for supported production installation.

```bash
wget -qO /tmp/deploy.sh https://raw.githubusercontent.com/level09/stk/master/deploy.sh
sudo DOMAIN=invoices.example.com REPO=level09/ziglag DB=postgres bash /tmp/deploy.sh
```

Do not run the deploy command without naming the target environment and receiving confirmation. Treat migrations, service restarts, and database actions on a remote host as production operations.

## Key Gotchas

- `User.from_dict()`, `Activity.register()`, `Session.create_session()` are all async.
- Signal handlers (`@user_authenticated.connect` etc.) are async.
- Pagination is manual: `offset().limit()` + `select(func.count())`.
- WebSocket connections release their DB session early to avoid pool starvation.
- Session backend: Redis if `REDIS_URL` is set, otherwise cookie-based.
- `DISABLE_MULTIPLE_SESSIONS` config controls single-session enforcement.
- Issued invoice downloads must serve `archived_pdf_path`, not regenerate from live settings.
- Never use `invoice_number` as a filesystem path component.
- fpdf2 requires a Unicode TTF. Docker installs DejaVu Sans; other hosts may set `INVOICE_FONT_PATH`.
- A PDF is not a structured German E-Rechnung. Do not claim XRechnung, ZUGFeRD, EN 16931, GoBD certification, or complete EU compliance.
