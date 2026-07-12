# German Invoicing and Template System

## Objective

Make Ziglag sufficient for the owner's current German PDF invoicing workflow while preserving a clear path to structured German E-Rechnung support later. Match the essential Invoice Simple workflow without copying its broader product surface.

## Scope

The change adds German invoice identity fields, service-period fields, explicit tax treatments, issued-invoice immutability, original PDF preservation, cancellation handling, activity history, and three selectable visual templates.

Structured XRechnung and ZUGFeRD output is outside this release. Existing historical invoices remain unchanged.

## Invoice Templates

Ziglag ships three templates:

1. **Precision**: restrained, information-dense layout inspired by modern payment platforms.
2. **Branded**: a stronger full-width brand header inspired by small-business invoicing products.
3. **Editorial**: precise invoice structure using the Newsreader, Work Sans, JetBrains Mono, warm neutral, charcoal, and orange vocabulary from `stitch_unified_design_system`.

Business settings store the default template. Draft invoices may override it. The invoice stores its selected template so later default changes do not affect it. Issuance freezes the selection with the rest of the invoice snapshot.

The selected template drives the editor preview, public invoice, email presentation, and PDF. The PDF remains A4-first and conservative enough for business and tax records.

## German Invoice Data

Business settings gain separate fields for:

- Steuernummer
- USt-IdNr.
- Default tax treatment
- Default invoice template

Clients gain a VAT ID field.

Invoices gain snapshot fields for:

- Supplier Steuernummer
- Supplier USt-IdNr.
- Customer VAT ID
- Service date from
- Service date to
- Tax treatment
- Template key
- Issued timestamp
- Cancelled timestamp
- Archived issued PDF path

The initial tax treatments are:

- `standard`: configured VAT rate and amount are displayed.
- `reverse_charge`: VAT is zero and the standard reverse-charge statement is printed.
- `exempt`: VAT is zero and a required exemption reason is printed.

The application rejects reverse-charge invoices without both supplier and customer VAT IDs. It rejects exempt invoices without an exemption reason. Standard invoices require a non-negative VAT rate.

## Invoice Lifecycle

Draft invoices remain editable and deletable.

An invoice becomes issued when the user explicitly issues it, sends it, or marks it sent. Issuance performs the following transaction:

1. Validate legal fields and invoice content.
2. Freeze business, client, tax, service-period, and template snapshots.
3. Generate the final PDF.
4. Store that exact PDF in an invoice archive owned by the application.
5. Set `issued_at` and the appropriate status.
6. Record the action in the activity log.

Issued invoices cannot be edited, reopened as drafts, or deleted. They may be marked paid, have payments recorded, or be cancelled. Cancellation preserves the invoice and archived PDF, sets its status to `cancelled`, records a timestamp, and logs the action. A later credit-note feature may build on this state but is not included here.

PDF download for an issued invoice serves the archived original. Draft PDF preview remains generated on demand.

## Rendering

Rendering uses a shared presentation dictionary so PDF, public HTML, editor preview, and email receive the same invoice facts and template key. Each surface may use native rendering appropriate to its medium, but field order, labels, totals, tax statements, and legal metadata remain consistent.

PDF blocks calculate required height before rendering. Totals, tax wording, payment instructions, and footer stay on the current page when they fit. The footer is placed above FPDF's automatic page-break margin, removing the current blank second page.

## User Interface

Settings provide a default-template selector with visual thumbnails. The invoice editor provides the same selector for draft overrides. Issued invoices show the frozen template without an editable control.

The editor separates legal identity from general contact details. Service period and tax treatment are first-class fields. Choosing reverse charge or exempt reveals only the fields required for that treatment.

Actions reflect lifecycle state:

- Draft: save, preview PDF, issue, send, delete.
- Issued: download original PDF, share, record payment, cancel.
- Cancelled: download original PDF and view history.

## Storage and Failure Handling

Archived PDFs use a deterministic per-user, per-invoice path and are never overwritten. Issuance fails without changing status if validation, PDF generation, or archive writing fails. Database changes commit only after the archived PDF is successfully written.

Application backups must include both the database and archived invoice directory. This release does not claim standalone GoBD certification.

## Verification

Tests cover:

- Standard German VAT calculation and required fields
- EU reverse charge validation and wording
- Tax exemption validation and wording
- Supplier and customer tax-ID snapshots
- Service date and service-period snapshots
- Default template and per-invoice override persistence
- Issued-invoice update, reopen, and delete rejection
- Cancellation preservation
- Archived PDF reuse after settings change
- Each template rendering successfully
- A representative one-item invoice remaining one A4 page
- Existing draft invoice creation and payment workflows

The acceptance check reproduces one Raisin-style domestic 19% invoice and one Polish reverse-charge invoice without using private production values in test fixtures.
