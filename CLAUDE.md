# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is ZigLag

Self-hosted invoicing application built on stk 17, installed as the `stkit` package and imported as `stk`. The stack uses async Quart, SQLAlchemy 2, Vue 3, Vuetify 4, quart-security 2.4.0, Alembic, and fpdf2. SQLite is the local default. Production deployments use PostgreSQL, Redis, Caddy, systemd, and the stk deploy script.

ZigLag issues PDF invoices with German and EU B2B safeguards. It does not yet generate XRechnung or ZUGFeRD.

`ziglag/app.py` composes the app: `Stk(__name__, config=Config, extensions=[invoicing])`. Never edit stk's files: they are replaced on every upgrade. Override a template or static file by putting one at the same path in `ziglag/templates/` or `ziglag/static/`; `stk/<name>` is the original.

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
./setup.sh                        # First-time setup (deps, .env)
uv sync                           # Install with dev tools
uv run stk db upgrade             # stk's migrations, then the app's
uv run stk run --port 5001        # Dev server (5001 avoids macOS AirPlay on 5000)
uv run ruff check --fix . && uv run ruff format .  # Lint + format
docker compose up --build          # Full stack (Redis, PostgreSQL, Nginx)
uv run python -m unittest discover -s tests -v  # Unit tests
uv run stk verify --json           # stk verification report
uv run stk smoke --json            # Real-browser behavioral check
uv run stk inspect context --json  # Routes and models report
uv run stk doctor                  # App state and the command that fixes each problem
```

First run: `setup.sh` -> `uv run stk db upgrade` -> `uv run stk run` -> open browser -> `/setup` creates admin account.
CLI alternative: `uv run stk install -e admin@example.com -p yourpassword`

### Database Migrations (Alembic)

```bash
uv run stk db upgrade [revision]              # Apply stk's migrations, then the app's
uv run stk db downgrade <revision>            # Rollback
uv run stk db revision -m "description"       # Autogenerate a revision in the app's lineage
uv run stk db revision -m "desc" --empty      # Empty revision for manual SQL
uv run stk db current                         # Show current revision
uv run stk db history                         # Show migration history
uv run stk db check                           # Fail if models drifted from migrations
```

There are two lineages in one version table: stk's own (branch label `stk`, shipped inside the installed package) and ZigLag's in `ziglag/migrations/`. Each app revision depends on stk's head, so `stk db upgrade` applies both and heads are never merged by hand. There is no `alembic/` directory or `alembic.ini`. SQLite uses batch mode automatically for ALTER TABLE support. A database created by ZigLag on stk 16 is not upgraded by `stk db upgrade`; see the upgrade section in `SECURITY.md`.

ZigLag lineage on disk when this was written (verify with `uv run stk db history`):

```text
8b66aaa47d56 (branch label ziglag, depends on stk_0008)
```

## Architecture

### Async SQLAlchemy (not flask-sqlalchemy)

Engine and session factory live in the installed package, `stk/extensions.py`, as module-level globals (`ext.engine`, `ext.async_session_factory`). No `db` object. Models inherit from `Base` (plain `DeclarativeBase`), not `db.Model`.

Request-scoped sessions via `g.db_session`, created in `before_request`, closed in `after_request` (see `stk/app.py` in the installed package).

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

stk's commands run through `uv run stk`; the app is found from `[tool.stk] app` in `pyproject.toml`. ZigLag adds the `backup` group (`ziglag/backup_cli.py`). List every command with `uv run stk inspect commands --json`.

### Extensions and Blueprints

Each extension is a package with `init_app(app)`, listed in `ziglag/app.py`; its `models` module is imported before `init_app` runs. Templates and static files resolve app first, then each extension's, then stk's.

- `ziglag/invoicing/` - clients, invoices, payments, PDF generation, reports, settings
- `ziglag/invoicing/public.py` - tokenized public invoice view and archived PDF delivery

Core blueprints live in the installed `stk` package, not in this repository:

- `stk/public/` - unauthenticated routes, OAuth callbacks (Google, GitHub)
- `stk/user/` - admin user, role and activity pages, and the models
- `stk/portal/` - protected dashboard (blueprint-level `@auth_required`)
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
- Session freshness: 60-minute window; an older session opening a sensitive page goes to `/verify`

**Signal handlers** (all async, in `stk/user/views.py` of the installed package):
- `@user_authenticated.connect` - creates session record, tracks IP changes
- `@user_logged_out.connect` - deactivates session
- `@password_changed.connect` - logs change, marks password as user-set
- `@tf_profile_changed.connect` - logs 2FA modifications

**Rate limiting** keeps fixed one-minute windows per IP in the database, applied to the authentication endpoints by stk.

### Core Models (`stk/user/models.py`, installed package)

- **User** - UserMixin. Auth fields, login tracking, lockout, 2FA, WebAuthn handle. Methods: `from_dict()`, `to_dict()`, `random_password()`, `logout_other_sessions()`, `get_active_sessions()`.
- **Role** - RoleMixin. Many-to-many with User via `roles_users`.
- **WebAuthn** - credential storage, FK to User via `fs_webauthn_user_handle`.
- **OAuth** - provider accounts linked to users. Unique on `(provider, provider_user_id)`.
- **Activity** - audit log. `register()` stores the event and does not broadcast.
- **Session** - tracks active sessions with IP, device meta, expiry.

### Invoicing Models (`ziglag/invoicing/models.py`)

- **BusinessSettings** - legal identity, tax defaults, numbering, currency, template, payment instructions.
- **Client** - contact details and VAT ID.
- **Invoice** - draft and issued lifecycle, legal snapshots, tax treatment, totals, archive path.
- **InvoiceItem** - description, detail, quantity, unit price, taxable flag.
- **Payment** - amount, date, method, and notes.

Draft invoices are editable and deletable. Issuing, sending, or advancing a draft to another issued state validates it, snapshots legal and customer data, writes the final PDF once, and locks invoice content. Issued invoices cannot return to draft or be deleted. Cancellation is terminal.

Tax treatments are `standard`, `reverse_charge`, and `exempt`. Reverse charge prints an Article 196 statement and requires supplier and customer VAT IDs. The application does not determine whether Article 196 applies. Exempt invoices require a reason.

Invoice templates are `precision`, `branded`, and `editorial`. Business settings provide the default; drafts may override it. `ziglag/invoicing/presentation.py` owns template definitions and tax wording.

Issued PDF files live under `instance/invoices/<user_id>/<invoice_id>/invoice-<invoice_id>.pdf`. Backups must include the database and this directory.

### Background Tasks

No Celery. `stk/tasks/` in the installed package provides:
- `run_in_background(coro)` - fire-and-forget with exception logging
- `run_with_session(coro_factory)` - provides fresh DB session to coroutine
- `cleanup_expired_sessions()` - deactivates expired, deletes 30+ day old records

### Frontend

Vue 3 + Vuetify loaded from static files. **Custom delimiters `${` and `}` to avoid Jinja conflicts.** Every Vue app must set `delimiters: config.delimiters`. Server data passed via `<script type="application/json">` tags, placed in `{% block js %}`, never inside `{% block content %}`. Icons are Tabler (`ti ti-*`), type classes are Material Design 3 (`text-title-large`, not `text-h6`), and `stk verify` fails on the MD2 and MDI forms. The core layout and static files come from the installed package; override a file by path under `ziglag/templates/` or `ziglag/static/`, extending `stk/<name>` where possible.

### Production Deployment

Use stk's `deploy.sh` from upstream for supported production installation. ZigLag keeps no local copy. The script does not install a Unicode font, so install `fonts-dejavu-core` on the server (see Key Gotchas).

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
- Session backend: Redis if `REDIS_URL` is set (needs the `full` extra), otherwise cookie-based.
- `DISABLE_MULTIPLE_SESSIONS` config controls single-session enforcement.
- Uploaded logos are written to `ziglag/static/uploads/` (inside the app package, not `instance/`). Back them up with the database and `instance/invoices/`; in Docker they live on the `logo-data` volume.
- Issued invoice downloads must serve `archived_pdf_path`, not regenerate from live settings.
- Never use `invoice_number` as a filesystem path component.
- fpdf2 requires a Unicode TTF. Docker installs DejaVu Sans; on a server installed with `deploy.sh`, install `fonts-dejavu-core`; other hosts may set `INVOICE_FONT_PATH`.
- A PDF is not a structured German E-Rechnung. Do not claim XRechnung, ZUGFeRD, EN 16931, GoBD certification, or complete EU compliance.
