# Invoicing Operations Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make invoice numbering, archives, share links, and local backups safe enough for an operator-owned German PDF invoicing deployment.

**Architecture:** Keep backup mechanics in a focused `stk/backup.py` service called by thin Quart commands. Keep invoice lifecycle rules in the invoicing model and small path helpers, with routes coordinating transactions and UI actions. Use one additive Alembic migration and preserve all existing issued records.

**Tech Stack:** Python 3.12+, Quart, Click, async SQLAlchemy 2, Alembic, SQLite backup API, PostgreSQL `pg_dump`/`pg_restore`, Vue 3/Vuetify, unittest.

---

## File map

- Create `stk/backup.py`: bundle creation, verification, and restoration with database adapters.
- Create `tests/test_backup.py`: archive and CLI service behavior.
- Create `alembic/versions/20260712_0002_invoice_operations.py`: nullable draft number and share expiry.
- Modify `stk/commands.py`: register the `backup create|verify|restore` command group.
- Modify `stk/invoicing/models.py`: numbering validation, nullable numbers, share lifecycle, archive resolution.
- Modify `stk/invoicing/views.py`: allocate numbers at issue, store relative paths, rotate and revoke share links.
- Modify `stk/invoicing/public.py`: reject expired links and resolve archived PDFs safely.
- Modify `stk/templates/invoicing/settings.html`: editable validated next number.
- Modify `stk/templates/invoicing/invoice_edit.html`: draft label, share expiry, and revoke action.
- Modify `tests/test_invoicing.py`: lifecycle, paths, numbering, and share tests.
- Modify `docs/deployment.mdx` and `docs/invoicing-compliance.mdx`: backup schedule and offsite boundary.

### Task 1: Backup bundle service

**Files:**
- Create: `stk/backup.py`
- Create: `tests/test_backup.py`

- [ ] **Step 1: Write failing SQLite bundle tests**

Create tests that build a temporary SQLite database and invoice tree, call `create_backup()`, and assert that `manifest.json`, `database.sqlite3`, and invoice PDFs exist. Add tests that corrupt one member and expect `BackupError`, and that restore refuses a non-empty destination.

```python
class BackupBundleTests(unittest.TestCase):
    def test_sqlite_bundle_round_trip(self):
        archive = create_backup(self.database_url, self.instance_path, self.output)
        manifest = verify_backup(archive)
        self.assertEqual(manifest["database"]["kind"], "sqlite")
        restore_backup(archive, self.restore_database_url, self.restore_instance)
        self.assertEqual(self.invoice_bytes, self.restored_pdf.read_bytes())

    def test_verify_rejects_checksum_mismatch(self):
        with self.assertRaisesRegex(BackupError, "checksum"):
            verify_backup(self.corrupted_archive)

    def test_restore_refuses_non_empty_target(self):
        with self.assertRaisesRegex(BackupError, "not empty"):
            restore_backup(self.archive, self.database_url, self.instance_path)
```

- [ ] **Step 2: Run tests and confirm the missing module failure**

Run: `uv run python -m unittest tests.test_backup -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stk.backup'`.

- [ ] **Step 3: Implement the bundle service**

Define `BackupError(RuntimeError)`, `create_backup(database_url: str, instance_path: Path, output: Path) -> Path`, `verify_backup(archive: Path) -> dict`, and `restore_backup(archive: Path, database_url: str, instance_path: Path, *, force: bool = False) -> None`.

Use `sqlite3.Connection.backup()` for SQLite. Use argument arrays with `subprocess.run(command, check=True)` for `pg_dump` and `pg_restore`, never a shell string. Build all members in a temporary directory, calculate SHA-256 over bytes, write manifest format version `1`, then create the final tar archive through a temporary sibling followed by `Path.replace()`. Reject absolute archive members, `..` components, symlinks, missing members, duplicate members, unsupported format versions, and checksum mismatches before extraction. Exclude `.env` and all secrets.

- [ ] **Step 4: Pass backup tests**

Run: `uv run python -m unittest tests.test_backup -v`
Expected: all backup tests PASS.

- [ ] **Step 5: Commit**

```bash
git add stk/backup.py tests/test_backup.py
git commit -m "feat: add restorable backup bundles"
```

### Task 2: Backup CLI commands

**Files:**
- Modify: `stk/commands.py`
- Modify: `tests/test_backup.py`

- [ ] **Step 1: Write failing CLI tests**

Test the Click runner against `backup create`, `backup verify`, and overwrite refusal for `backup restore`. Patch service functions, and assert that configuration supplies `SQLALCHEMY_DATABASE_URI` and `current_app.instance_path`.

```python
def test_backup_create_reports_archive(self):
    result = self.runner.invoke(commands.backup, ["create", "--output", str(path)])
    self.assertEqual(result.exit_code, 0)
    self.assertIn(str(path), result.output)
```

- [ ] **Step 2: Run the focused tests**

Run: `uv run python -m unittest tests.test_backup.BackupCommandTests -v`
Expected: FAIL because the command group does not exist.

- [ ] **Step 3: Add thin Click wrappers**

Register a `backup` Click group with `create`, `verify`, and `restore` subcommands. `create` accepts an optional `--output PATH`; `verify` accepts one existing archive path; `restore` accepts one existing archive path and a boolean `--force` flag.

```python
@click.group("backup")
def backup():
    """Create, verify, and restore application backups."""
    pass
```

Convert `BackupError` into `click.ClickException`. Default output is `backups/ziglag-<UTC timestamp>.tar.gz` outside `instance/invoices/`.

- [ ] **Step 4: Pass CLI tests and expose command registration**

Run: `uv run python -m unittest tests.test_backup -v && uv run quart --help`
Expected: tests PASS and help lists `backup`.

- [ ] **Step 5: Commit**

```bash
git add stk/commands.py tests/test_backup.py
git commit -m "feat: expose backup management commands"
```

### Task 3: Number invoices at issuance

**Files:**
- Modify: `stk/invoicing/models.py`
- Modify: `stk/invoicing/views.py`
- Modify: `stk/templates/invoicing/settings.html`
- Modify: `stk/templates/invoicing/invoice_edit.html`
- Modify: `tests/test_invoicing.py`

- [ ] **Step 1: Write failing numbering tests**

Cover unnumbered draft creation, allocation exactly once at issuance, positive next-number validation, rejection below an issued number with the same prefix, and preservation of legacy numbered drafts.

```python
def test_new_draft_does_not_consume_number(self):
    settings = BusinessSettings(invoice_prefix="RSN", invoice_next_number=68)
    invoice = Invoice(status="draft")
    self.assertIsNone(invoice.invoice_number)
    self.assertEqual(settings.invoice_next_number, 68)

def test_issue_allocates_number_once(self):
    self.assertEqual(settings.allocate_invoice_number(), "RSN0068")
    self.assertEqual(settings.invoice_next_number, 69)
```

- [ ] **Step 2: Confirm focused failures**

Run: `uv run python -m unittest tests.test_invoicing.InvoiceNumberingTests -v`
Expected: FAIL because issuance allocation and settings validation are absent.

- [ ] **Step 3: Implement model and transaction rules**

Make `Invoice.invoice_number` nullable. Rename the mutating generator to `allocate_invoice_number()`. Add `BusinessSettings.set_numbering(prefix, next_number, issued_numbers)` that validates prefix, requires a positive integer, and rejects a next number less than or equal to the maximum issued numeric suffix for that prefix.

In draft creation, remove number allocation. In `_issue_invoice`, allocate only when `invoice.invoice_number is None`, before PDF generation, within the existing issuance transaction. On `IntegrityError`, roll back, remove the newly written archive, and return `Invoice number is already in use; retry issuance`.

- [ ] **Step 4: Update the UI**

Keep the existing Next Number field, submit it as an integer, and display `Draft` wherever a new invoice lacks a number. Do not show a fabricated preview number as the invoice's assigned number.

- [ ] **Step 5: Pass numbering and existing invoice tests**

Run: `uv run python -m unittest tests.test_invoicing -v`
Expected: all invoicing tests PASS.

- [ ] **Step 6: Commit**

```bash
git add stk/invoicing/models.py stk/invoicing/views.py stk/templates/invoicing/settings.html stk/templates/invoicing/invoice_edit.html tests/test_invoicing.py
git commit -m "fix: allocate invoice numbers at issuance"
```

### Task 4: Portable archived PDF paths

**Files:**
- Modify: `stk/invoicing/models.py`
- Modify: `stk/invoicing/views.py`
- Modify: `stk/invoicing/public.py`
- Modify: `tests/test_invoicing.py`

- [ ] **Step 1: Write failing path tests**

Test relative path generation, safe resolution, traversal rejection, current-instance legacy absolute paths, and rejection of unrelated absolute paths.

```python
def test_archive_resolver_rejects_escape(self):
    with self.assertRaisesRegex(ValueError, "outside invoice archive"):
        resolve_invoice_archive(instance, "../../etc/passwd")
```

- [ ] **Step 2: Confirm focused failures**

Run: `uv run python -m unittest tests.test_invoicing.InvoiceArchivePathTests -v`
Expected: FAIL because the resolver does not exist.

- [ ] **Step 3: Add one canonical resolver**

Add `invoice_archive_relative_path(user_id: int, invoice_id: int) -> Path`, returning `Path("invoices", str(user_id), str(invoice_id), f"invoice-{invoice_id}.pdf")`, and `resolve_invoice_archive(instance_path: str, stored_path: str) -> Path`.

Resolve and verify that the path is within `<instance>/invoices`. Permit a legacy absolute path only when it resolves within that root. Use the resolver for authenticated download, public download, email attachment, and issuance. Store only `relative_path.as_posix()` for new archives.

- [ ] **Step 4: Pass path and invoice tests**

Run: `uv run python -m unittest tests.test_invoicing -v`
Expected: all invoicing tests PASS.

- [ ] **Step 5: Commit**

```bash
git add stk/invoicing/models.py stk/invoicing/views.py stk/invoicing/public.py tests/test_invoicing.py
git commit -m "fix: make invoice archive paths portable"
```

### Task 5: Expiring and revocable share links

**Files:**
- Modify: `stk/invoicing/models.py`
- Modify: `stk/invoicing/views.py`
- Modify: `stk/invoicing/public.py`
- Modify: `stk/templates/invoicing/invoice_edit.html`
- Modify: `tests/test_invoicing.py`

- [ ] **Step 1: Write failing lifecycle tests**

Test 30-day expiry, rotation, revocation, and public rejection at the exact expiry instant.

```python
def test_share_token_rotation_and_expiry(self):
    first = invoice.rotate_share_token(now)
    second = invoice.rotate_share_token(now)
    self.assertNotEqual(first, second)
    self.assertTrue(invoice.share_is_active(now + timedelta(days=29)))
    self.assertFalse(invoice.share_is_active(now + timedelta(days=30)))
```

- [ ] **Step 2: Confirm focused failures**

Run: `uv run python -m unittest tests.test_invoicing.InvoiceShareTests -v`
Expected: FAIL because expiry fields and methods do not exist.

- [ ] **Step 3: Implement share lifecycle**

Add nullable `share_token_expires_at`. Replace `generate_share_token()` with `rotate_share_token(self, now=None, lifetime=timedelta(days=30)) -> str`, `revoke_share_token(self) -> None`, and `share_is_active(self, now=None) -> bool`.

POST `/share` always rotates. Add DELETE `/share` to revoke. Email sending rotates immediately before building the URL. Both public routes query by token then require `share_is_active()` and otherwise return the same 404 response.

- [ ] **Step 4: Add UI expiry and revoke action**

Show the expiry returned by POST `/share` and add a Revoke button that calls DELETE `/api/invoice/<id>/share`, closes the dialog, and clears the URL.

- [ ] **Step 5: Pass share and invoice tests**

Run: `uv run python -m unittest tests.test_invoicing -v`
Expected: all invoicing tests PASS.

- [ ] **Step 6: Commit**

```bash
git add stk/invoicing/models.py stk/invoicing/views.py stk/invoicing/public.py stk/templates/invoicing/invoice_edit.html tests/test_invoicing.py
git commit -m "feat: expire and revoke invoice share links"
```

### Task 6: Additive migration and local upgrade

**Files:**
- Create: `alembic/versions/20260712_0002_invoice_operations.py`
- Modify: `tests/test_invoicing.py`

- [ ] **Step 1: Write migration metadata assertions**

Assert the model permits null `invoice_number` and exposes nullable `share_token_expires_at`.

- [ ] **Step 2: Generate and review the migration**

Run: `uv run quart db revision -m "harden invoice operations"`
Expected: a new revision after `20260712_0001`.

Edit it to make `invoice.invoice_number` nullable and add `share_token_expires_at`. In `upgrade()`, set existing non-null share expiries to migration execution time plus 30 days using a portable Python-calculated timestamp. Downgrade removes the expiry column and restores non-null numbering only after assigning deterministic numbers to any remaining drafts, so downgrade cannot fail silently.

- [ ] **Step 3: Verify migration round trip on a temporary database**

Run: `DATABASE_URL=sqlite+aiosqlite:////tmp/ziglag-migration.db uv run quart db upgrade && DATABASE_URL=sqlite+aiosqlite:////tmp/ziglag-migration.db uv run quart db downgrade 20260712_0001 && DATABASE_URL=sqlite+aiosqlite:////tmp/ziglag-migration.db uv run quart db upgrade`
Expected: all three commands exit 0 and final revision is head.

- [ ] **Step 4: Apply the upgrade to the local development database**

Run: `uv run quart db current && uv run quart db upgrade && uv run quart db current`
Expected: final current revision equals the new head. This is local development only. Do not run against staging or production without naming the environment and receiving confirmation.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/20260712_0002_invoice_operations.py tests/test_invoicing.py
git commit -m "feat: migrate invoice operations lifecycle"
```

### Task 7: Operations documentation and final verification

**Files:**
- Modify: `docs/deployment.mdx`
- Modify: `docs/invoicing-compliance.mdx`
- Modify: `README.md`

- [ ] **Step 1: Document exact operator commands**

Document create, verify, and restore examples, the default backup location, required `pg_dump` compatibility, `--force` safety behavior, and this boundary: a local archive must be copied to independent storage to count as an offsite backup. Add a sample daily cron entry that creates a bundle but does not claim to provide offsite retention.

- [ ] **Step 2: Run complete verification**

Run:

```bash
uv run python -m unittest discover -s tests -v
uv run python checks.py
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Expected: 0 failures, all application checks pass, lint and formatting pass, and no whitespace errors.

- [ ] **Step 3: Verify backup recovery manually in a temporary directory**

Run `quart backup create`, `quart backup verify`, and `quart backup restore` against temporary SQLite and instance paths. Open the restored database and compare the restored invoice PDF SHA-256 with the source.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md docs/deployment.mdx docs/invoicing-compliance.mdx
git commit -m "docs: add invoicing backup operations"
```
