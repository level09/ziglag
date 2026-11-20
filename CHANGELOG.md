# Changelog

## Unreleased

- Move from a vendored stk 16.0.0 fork to stk 17 as an installed package (`stkit` 17.15.1, quart-security 2.4.0 per `uv.lock`). ZigLag is now the `ziglag/` app package. The vendored `stk/` directory, `run.py`, `alembic/`, `alembic.ini`, `checks.py`, and the local `deploy.sh` are gone. Commands run as `uv run stk ...` instead of `uv run quart ...`.
- Migrations are split into two lineages in one version table: stk's, shipped in the package, and ZigLag's in `ziglag/migrations/`. A database created by the stk 16 based release is not upgraded by `stk db upgrade`; it needs the adoption step first.
- Uploaded logos move from `stk/static/uploads/` to `ziglag/static/uploads/`. Archived invoice PDFs stay in `instance/invoices/` and the default SQLite database stays `instance/ziglag.db`.
- Replace the Docker, Nginx, `postgres/`, `.env-sample`, `setup.sh`, and CI files with the stk 17 versions. Compose now requires unique database and Redis passwords, `STK_HOST`, and TLS certificate paths, and publishes only ports 80 and 443. Nginx passes `/static/` to the app instead of reading `stk/static` from disk. Compose keeps `instance/` on the `invoice-data` volume and adds a `logo-data` volume for uploaded logos. The image still installs DejaVu Sans for PDF generation.
- Production installs use stk's upstream `deploy.sh` with `REPO=level09/ziglag`. It does not install a Unicode font: install `fonts-dejavu-core` on the server.
- Behaviour changes from stk 17 that apply here: emails are normalised and login is case-insensitive, sessions older than an hour are sent to `/verify` for sensitive pages, `stk_0007` marks existing accounts confirmed, password reset by email turns on when `MAIL_SERVER` and `STK_PUBLIC_URL` are both set, and a TOTP secret under 112 bits fails like a wrong code. See the upgrade section in [SECURITY.md](SECURITY.md), including the duplicate-email check query to run before upgrading.
- Replace the stk 16 era agent skills with the stk 17 set and update the pre-commit ruff version to the one locked in `uv.lock`.

### Upgrading an existing deployment

Stop the app. Back up the database, `instance/invoices/`, `stk/static/uploads/`, `.env`, and encryption keys. Move `stk/static/uploads/*` to `ziglag/static/uploads/`. Install with `uv sync --frozen --extra full`. Adopt the database with `uv run stk adopt-stk16`, then run `uv run stk db upgrade` and `uv run stk protect-mfa`. Start the app. [SECURITY.md](SECURITY.md) has the details and the Docker volume note.

## ZigLag 0.2.0 (2026-10-06)

- Update the vendored framework to stk 16.0.0 and Quart-Security 2.0.1.
- Add shared authentication state, session revocation, encrypted MFA seeds, atomic login limits, stricter OAuth checks, and application CSRF protection.
- Update pinned Vue, Vuetify, Axios, and Tabler assets. Preserve ZigLag pages and backup commands.
- Add security migrations after the existing invoice migration chain. See [SECURITY.md](SECURITY.md) before upgrading a deployment.
- Add finance reports and invoice date filters.
- Align invoice tax treatment and template columns with their migrations. The migration drift check now passes.

## v11.3.0 (2025-12-02)

### Added
- Lite mode: Zero-config startup with `uv sync && flask run` — no Redis required
- Full mode: Optional Redis + Celery via `uv sync --extra full`
- SQLAlchemy-based sessions as default (Redis sessions optional)
- AI-assisted development with AGENTS.md for Claude Code and Cursor

### Changed
- Redis and Celery moved to optional dependencies
- SQLite database path now uses absolute path in `instance/stk.db`
- Updated documentation for lite/full mode workflow
- Simplified README with clearer positioning

## v11.2.0 (2025-04-24)

### Added
- Production-ready Docker configuration with multi-stage builds
- PostgreSQL service in Docker Compose setup
- Improved environment variable handling for Docker
- Support for user-specific Docker UID configuration
- Enhanced setup.sh script with Docker configuration option

### Changed
- Optimized Dockerfile with multi-stage build for smaller, more secure images
- Fixed Redis connectivity by using correct environment variables
- Improved nginx configuration with proper retry settings
- Enhanced tmpfs configuration for better performance
- Added proper health checks for all Docker services

## v11.1.0 (2025-03-30)

### Added
- Migrated from pip/venv to uv for package management
- Faster installation and dependency resolution
- Better Python environment isolation

### Changed
- Updated setup.sh script to use uv instead of venv
- Modified Dockerfile to use uv for package installation
- Updated documentation to reference uv

## v11.0 (2023-03-27)

### Added
- New activity model to track user actions like creating and editing users/roles
- Cursor Rules for improved code generation and assistance
- Comprehensive documentation for Cursor Rules approach

### Changed
- Improved user and roles tables design in both frontend and backend
- Transitioned from OpenAI integration to Cursor Rules for code generation
- Enhanced admin user creation with better console output

### Removed
- Removed flask-openai dependency and related code generation commands
- Removed OpenAI API key requirements

### Fixed
- Various UI and UX improvements
- Code cleanup and bug fixes
