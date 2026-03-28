<p align="center">
  <img src="stk/static/img/ziglag.svg" alt="ZigLag" height="80">
</p>

<h1 align="center">ZigLag</h1>

<p align="center">
  Self-hosted invoicing for freelancers and small businesses.<br>
  Built on <a href="https://github.com/level09/stk">stk</a>. Open source. No subscriptions.
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
  <a href="https://github.com/level09/stk"><img src="https://img.shields.io/badge/Built%20on-stk-353aaf" alt="Built on stk"></a>
</p>

## Quick Start

```bash
git clone git@github.com:level09/ziglag.git && cd ziglag
./setup.sh
uv run quart create-db
uv run quart run --port 5001
```

Open `http://localhost:5001`. First visit shows a setup page to create your admin account.

## Features

**Invoicing**
- Create invoices with line items, tax (VAT/GST), discounts
- Client autocomplete from saved contacts
- Invoice status flow: Draft, Sent, Paid
- Record payments, mark paid in one click
- PDF generation (pure Python, no system deps)
- Shareable public invoice links
- Configurable invoice numbering, currency, labels

**Clients**
- Client database with contact details
- Total billed tracking per client
- Search and autocomplete on invoice creation

**Reports**
- Monthly revenue breakdown by tax year
- Client count, invoice count, paid totals
- Year-over-year comparison

**Business Settings**
- Business name, address, logo upload
- Tax configuration (rate, label, type, inclusive/exclusive)
- Invoice number prefix and auto-increment
- Currency and date format
- Default notes and payment instructions

**Dashboard**
- Invoice count, outstanding amount, total paid, client count
- Recent invoices with status
- Quick actions

## Stack

Built on the [stk framework](https://github.com/level09/stk):

| Layer | Tech |
|-------|------|
| Backend | Python 3.11+, Quart (async), SQLAlchemy 2.0+ |
| Frontend | Vue 3, Vuetify 3 (no build step) |
| Database | SQLite (default), PostgreSQL (optional) |
| Auth | Session auth, 2FA/TOTP, WebAuthn/Passkeys, OAuth |
| PDF | fpdf2 (pure Python) |
| Real-time | WebSocket with live invoice status updates |

## Design System

Neo-brutalist editorial aesthetic. Indigo-violet palette, Plus Jakarta Sans headlines, thick borders, offset shadows. See `design-system/` for the full spec.

## Configuration

Copy `.env-sample` to `.env`. Required variables:

```bash
SECRET_KEY=your_secret_key
SECURITY_PASSWORD_SALT=your_salt
```

Optional:

```bash
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://user:pass@localhost/ziglag
REDIS_URL=redis://localhost:6379/1
```

## Database

```bash
uv run quart create-db                     # apply all migrations
uv run quart db revision -m "description"  # generate new migration
uv run quart db upgrade                    # apply pending migrations
uv run quart db downgrade -1               # rollback one step
```

## Docker

```bash
docker compose up --build
```

## Deploy

```bash
curl -sSL https://raw.githubusercontent.com/level09/ignite/main/ignite.sh | sudo DOMAIN=your-domain.com bash
```

Auto-SSL via Caddy. See [Ignite](https://github.com/level09/ignite).

## License

MIT
