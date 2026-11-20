<p align="center">
  <img src="ziglag/static/img/ziglag.svg" alt="ZigLag" height="80">
</p>

<h1 align="center">ZigLag</h1>

<p align="center">
  Self-hosted invoicing for freelancers and small businesses.<br>
  Built on <a href="https://github.com/level09/stk">stk 17</a>. Open source. No document limits.
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
uv run stk db upgrade
uv run stk run --port 5001
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
| Framework | stk 17 (`stkit` package) |
| Frontend | Vue 3 and Vuetify 4, no build step |
| Database | SQLite by default, PostgreSQL optional |
| Auth | Sessions, TOTP, WebAuthn, OAuth, recovery codes |
| PDF | fpdf2 with Unicode font support |
| Operations | Alembic, uvicorn, Caddy, systemd, PostgreSQL, Redis |

## Commands

```bash
uv sync
uv run stk db upgrade
uv run stk run --port 5001
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
uv run stk verify --json
uv run stk smoke --json
uv run stk inspect context --json
```

Create a restorable local bundle with `uv run stk backup create`, verify it, then copy it to independent storage.

## Configuration

`setup.sh` creates `.env`. Required secrets include:

```bash
SECRET_KEY=replace-me
SECURITY_PASSWORD_SALT=replace-me
```

Production installations should use PostgreSQL and Redis:

```bash
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://user:password@localhost/ziglag
REDIS_URL=redis://localhost:6379/1
```

Back up the database, `instance/invoices/` and `ziglag/static/uploads/`. The invoices directory contains the immutable PDFs issued by the application; the uploads directory contains business logos.

## Database

```bash
uv run stk db current
uv run stk db upgrade
uv run stk db revision -m "description"
uv run stk db downgrade -1
```

There are two migration lineages in one version table: stk's, shipped in the installed package, and ZigLag's in `ziglag/migrations/`. `uv run stk db upgrade` applies both. A database created by ZigLag on stk 16 needs the adoption step in [SECURITY.md](SECURITY.md) first.

## Deploy

stk includes the production deploy script. On a fresh Ubuntu server:

```bash
wget -qO /tmp/deploy.sh https://raw.githubusercontent.com/level09/stk/master/deploy.sh
sudo DOMAIN=invoices.example.com REPO=level09/ziglag DB=postgres bash /tmp/deploy.sh
```

The script installs PostgreSQL, Redis, Caddy, systemd services, application dependencies, migrations, and TLS. It does not install a Unicode font: run `apt-get install fonts-dejavu-core` on the server so PDF generation works. Review [deployment documentation](docs/deployment.mdx) before using it on a server.

Docker remains available:

```bash
docker compose up --build
```

## Production Checklist

- Run all tests and `stk verify` against the release commit.
- Use PostgreSQL, Redis, HTTPS, and secure cookie settings.
- Back up the database and issued-PDF archive together.
- Test restore procedures before relying on the installation.
- Confirm invoice wording and tax treatment with the business's Steuerberater.
- Add XRechnung or ZUGFeRD before the applicable German E-Rechnung deadline.

## License

MIT
