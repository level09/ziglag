# Invoicing Operations Hardening

## Scope

Close the operational gaps that remain before Ziglag replaces Invoice Simple for the current German invoicing workflow. This change covers restorable local backups, invoice number allocation, portable PDF archive paths, expiring share links, and the local schema upgrade. Importing historical Invoice Simple invoices and structured E-Rechnung remain outside this change.

## Backup bundle

Add three Quart CLI commands:

- `quart backup create [--output PATH]` creates a timestamped compressed archive.
- `quart backup verify ARCHIVE` validates the archive structure and every recorded checksum without changing application state.
- `quart backup restore ARCHIVE [--force]` restores the database and invoice archive.

The bundle contains a database backup, `instance/invoices/`, and a JSON manifest with format version, creation time, database type, application version, file sizes, and SHA-256 checksums. SQLite is copied through its online backup API so a running application cannot produce a torn database. PostgreSQL uses `pg_dump` in custom format and restores with `pg_restore`. Missing required executables fail immediately.

Restore validates the complete bundle before changing anything. It refuses a non-empty target database or invoice directory unless `--force` is supplied. Forced restore first moves the existing local data into a timestamped safety directory. Restore uses temporary paths and atomic replacement where the platform permits it. Secrets and `.env` contents are never included.

This command creates a local recovery artifact. Production documentation must still require copying that artifact off the application server.

## Invoice numbering

Drafts no longer consume invoice numbers. New drafts have no legal invoice number and use an internal draft label in the UI. Issuance allocates the next number and increments the counter in the same database transaction that freezes and archives the invoice.

Business settings expose `invoice_next_number`. An update must be a positive integer and must be greater than every issued number using the active prefix. Changing the prefix is allowed, and validation applies to the selected prefix. Issuance retains the database uniqueness constraint and fails clearly on a concurrent collision rather than silently skipping numbers.

Existing numbered drafts keep their assigned numbers to avoid rewriting user-visible records. They do not advance the counter again when issued. Deleted future drafts can therefore leave historical gaps, but new drafts will not create new gaps.

## Portable PDF archives

New `archived_pdf_path` values are stored relative to the application instance directory. A single resolver rejects absolute paths and traversal outside the invoice archive. Existing absolute paths remain readable during migration and are converted to relative paths when they point inside the current instance directory. Paths outside it are reported for manual repair rather than guessed.

Backup and restore preserve the relative archive layout, so moving the application does not require database edits.

## Share-link lifecycle

Add `share_token_expires_at` to invoices. Creating or emailing a share link sets a configurable default expiry, initially 30 days. Creating a new link rotates the token and expiry. A revoke action clears both fields. Public HTML and PDF routes return 404 for missing, revoked, or expired tokens.

Issued invoice PDFs remain immutable. Expiry affects public access only, not the archived record or authenticated download.

## Migration and compatibility

Add an additive Alembic migration for share expiry and any numbering nullability required by unnumbered drafts. The migration preserves existing invoice numbers, tokens, and archive paths. Existing share tokens receive a 30-day expiry from migration time so none remain permanent.

Run `uv run quart db upgrade` on the local development database after the code and migration pass verification. Production upgrades remain an explicit deployment step and are not run by this change.

## Validation

Tests cover SQLite backup, verification, restore, checksum failure, refusal to overwrite, invoice numbering at issuance, starting-number validation, concurrent-number failure, relative path resolution, legacy path handling, share expiry, rotation, and revocation. PostgreSQL command construction is unit-tested without requiring a production database. The existing unit suite, application checks, migration round trip, lint, and format checks must pass.

## Operational boundary

This work makes local recovery testable but does not make a same-server archive resilient. Production requires a scheduled command, transfer to independent storage, retention monitoring, and periodic restore tests. Historical Invoice Simple PDFs remain a separate retained archive. XRechnung and ZUGFeRD support remain planned work for the German B2B deadlines.
