<p align="center">
  <img src="stk/static/img/ziglag.svg" alt="ZigLag" height="80">
</p>

<h1 align="center">ZigLag</h1>

<p align="center">
  Self-hosted invoicing for freelancers and small businesses.<br>
  Built on <a href="https://github.com/level09/stk">stk 13.4.1</a>. Open source. No document limits.
</p>

## Status

ZigLag covers the owner's essential Invoice Simple workflow: clients, invoices, VAT, Article 196 reverse charge for qualifying B2B services, PDF delivery, payment tracking, public links, reports, and reusable templates.

The German invoice safeguards include separate Steuernummer and USt-IdNr. fields, customer VAT IDs, service periods, explicit tax treatments, issued-invoice locking, cancellation, activity history, and preservation of the exact issued PDF.

ZigLag currently issues PDF invoices. It does not generate structured XRechnung or ZUGFeRD files. Germany permits PDFs during the current transition period under the applicable conditions, but domestic German B2B invoices will require structured E-Rechnung output after the transition. See [Invoicing and compliance](docs/invoicing-compliance.mdx).

This is essential workflow parity, not full Invoice Simple feature parity. ZigLag does not currently include estimates, expense capture, recurring invoices, payment scheduling, hosted card payments, credit notes, or inbound invoice processing.

## Quick Start

```bash
git clone git@github.com:level09/ziglag.git
cd ziglag
./setup.sh
uv run quart create-db
uv run quart run --port 5001
```

Open `http://localhost:5001`. The first visit creates the administrator account through `/setup`.

## Invoicing

- Draft, issued, sent, viewed, paid, overdue, and cancelled states
- Immutable issued invoices with archived original PDFs
- Standard VAT, Article 196 reverse charge for qualifying EU B2B services, and tax-exempt treatments
- Supplier Steuernummer and USt-IdNr., customer VAT ID, and service period
- Precision, Branded, and Editorial invoice templates
- Per-business default template with per-invoice override
- Client autocomplete, line items, discounts, payments, and balance tracking
- PDF download, email delivery, and private share links
- Monthly and yearly paid-revenue reports

Drafts remain editable and deletable. Issuing or sending an invoice freezes its legal fields, customer snapshot, tax treatment, template, payment instructions, and PDF. Cancelled invoices retain their original record and PDF. ZigLag does not determine whether a transaction qualifies for Article 196 treatment; the issuer and tax adviser must make that determination.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, async Quart, SQLAlchemy 2 |
| Framework | stk 13.4.1 |
| Frontend | Vue 3 and Vuetify 3, no build step |
| Database | SQLite by default, PostgreSQL optional |
| Auth | Sessions, TOTP, WebAuthn, OAuth, recovery codes |
| PDF | fpdf2 with Unicode font support |
| Operations | Alembic, uvicorn, Caddy, systemd, PostgreSQL, Redis |

## Commands

```bash
uv sync --extra dev
uv run quart create-db
uv run quart run --port 5001
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
uv run python checks.py
uv run quart verify --json
uv run quart inspect context --json
```

## Configuration

`setup.sh` creates `.env`. Required secrets include:

```bash
SECRET_KEY=replace-me
SECURITY_PASSWORD_SALT=replace-me
SECURITY_TOTP_SECRETS=replace-me
```

Production installations should use PostgreSQL and Redis:

```bash
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://user:password@localhost/ziglag
REDIS_URL=redis://localhost:6379/1
```

Back up both the database and `instance/invoices/`. The latter contains the immutable PDFs issued by the application.

## Database

```bash
uv run quart db current
uv run quart db upgrade
uv run quart db revision -m "description"
uv run quart db downgrade -1
```

The current migration chain is linear:

```text
20260326_0001 -> cfa8efad03ed -> 228ac4e0ebf5 -> 20260712_0001
```

## Deploy

stk includes the production deploy script. On a fresh Ubuntu server:

```bash
wget -qO /tmp/deploy.sh https://raw.githubusercontent.com/level09/stk/master/deploy.sh
sudo DOMAIN=invoices.example.com REPO=level09/ziglag DB=postgres bash /tmp/deploy.sh
```

The script installs PostgreSQL, Redis, Caddy, systemd services, application dependencies, migrations, and TLS. Review [deployment documentation](docs/deployment.mdx) before using it on a server.

Docker remains available:

```bash
docker compose up --build
```

## Production Checklist

- Run all tests and `quart verify` against the release commit.
- Use PostgreSQL, Redis, HTTPS, and secure cookie settings.
- Back up the database and issued-PDF archive together.
- Test restore procedures before relying on the installation.
- Confirm invoice wording and tax treatment with the business's Steuerberater.
- Add XRechnung or ZUGFeRD before the applicable German E-Rechnung deadline.

## License

MIT
