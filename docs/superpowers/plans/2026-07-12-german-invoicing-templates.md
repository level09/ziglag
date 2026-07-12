# German Invoicing Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add essential German PDF invoice fields, lifecycle safeguards, archived issued PDFs, and three selectable invoice templates.

**Architecture:** Extend the existing invoicing models and APIs without introducing a second invoice subsystem. Centralize legal validation and issuance on `Invoice`, use one presentation dictionary for all renderers, and preserve the exact PDF produced at issuance.

**Tech Stack:** Quart, async SQLAlchemy, Alembic, Vue 3 Options API, Vuetify 3, fpdf2, unittest.

---

## File Structure

- `stk/invoicing/models.py`: invoice fields, snapshots, validation, lifecycle state.
- `stk/invoicing/presentation.py`: shared labels, tax wording, and template definitions.
- `stk/invoicing/pdf.py`: one-page-aware A4 rendering for three templates.
- `stk/invoicing/views.py`: issuance, archive serving, mutation restrictions, cancellation.
- `stk/templates/invoicing/*.html`: template selector, legal fields, shared visual language.
- `alembic/versions/*_german_invoice_fields.py`: additive schema migration.
- `tests/test_invoicing.py`: model, validation, lifecycle, and PDF regression tests.

### Task 1: Domain fields and validation

- [ ] Add tests constructing standard, reverse-charge, and exempt invoices and assert validation errors for missing tax IDs or exemption reasons.
- [ ] Run `uv run python -m unittest tests.test_invoicing -v` and verify the new tests fail.
- [ ] Add settings, client, and invoice fields from the approved spec to `models.py`.
- [ ] Add `Invoice.validate_for_issue()`, `Invoice.is_issued`, snapshot fields, and tax-treatment calculation.
- [ ] Run the focused tests and verify they pass.

### Task 2: Additive migration

- [ ] Generate `uv run quart db revision -m "German invoice fields"`.
- [ ] Review the migration for only additive nullable columns with safe defaults.
- [ ] Run upgrade, downgrade one revision, and upgrade again against the local development database.

### Task 3: Shared presentation and PDF templates

- [ ] Add tests for tax wording and the three allowed template keys.
- [ ] Add `presentation.py` with `precision`, `branded`, and `editorial` definitions and legal wording.
- [ ] Refactor `pdf.py` to consume the shared presentation dictionary.
- [ ] Keep footer placement above the 20 mm page-break margin and test that a representative invoice has one page.
- [ ] Render all three templates and verify each produces a valid PDF.

### Task 4: Issuance and immutable archive

- [ ] Add route tests showing drafts remain editable/deletable and issued invoices reject update, reopen, and delete.
- [ ] Add an issue endpoint and make send/mark-sent use the same issuance function.
- [ ] Write issued PDFs once under `instance/invoices/<user_id>/<invoice_id>/<invoice_number>.pdf`.
- [ ] Serve the archived file for issued invoices and generated previews for drafts.
- [ ] Add cancellation that preserves invoice data and archived PDF.
- [ ] Log issue and cancellation through `Activity.register()`.

### Task 5: Editor and settings

- [ ] Add separate Steuernummer, USt-IdNr., default tax treatment, and default template controls to settings.
- [ ] Add customer VAT ID to client create/edit and search payloads.
- [ ] Add service period, tax treatment, exemption reason, and template selection to the draft editor.
- [ ] Hide editing and destructive controls for issued invoices.
- [ ] Add issue and cancel actions matching lifecycle state.

### Task 6: Public view, email, and visual parity

- [ ] Apply template-key classes and the Stitch palette and typography to preview, public invoice, and email.
- [ ] Keep legal field order and wording identical across HTML and PDF.
- [ ] Verify responsive public invoices and print styles.

### Task 7: Verification

- [ ] Run `uv run ruff check .` and `uv run ruff format --check .`.
- [ ] Run `uv run python -m unittest discover -s tests -v`.
- [ ] Run `uv run python checks.py`.
- [ ] Render representative domestic and reverse-charge PDFs and confirm field completeness and page count.
- [ ] Review the final diff for request-only changes and migration safety.
