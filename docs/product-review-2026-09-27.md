# ZigLag product review

Date: 2026-09-27. Scope: source review after the inline invoice editor work. Findings below describe the reviewed baseline. See the implementation status for changes made since the review.

## Implementation status: 2026-09-28

Release A is implemented locally. Shared styling, the dashboard, invoice list, report currency selection, and email result feedback are updated. Drafts no longer count as unpaid; overpaid invoices remain in Paid and reports. Reports retain the invoice-date basis and label it explicitly. Email waits for SMTP acceptance and reports failed or unknown outcomes without claiming delivery. No schema change, production migration, or real email was used for verification.

Verification: 113 unit tests, 26 sanity checks, Ruff, and the invoice-editor and workspace browser flows pass. Browser checks cover search races, retry, URL state, keyboard links, dark/light themes, narrow layouts, long unbroken text, mocked email feedback, reports, login, and issued PDF regression. Desktop and phone screenshots were inspected. Layouts were checked at 390, 720, and 1440 CSS pixels; a separate browser zoom-control test was not run.

Release B remains planned: setup guidance, customer/settings form recovery, public invoice escaping and snapshot behavior, and the recipient page redesign. The AI draft experiment and durable email history remain separate.

## Product direction

Make daily invoicing feel calm, fast, and dependable. The invoice is the centre of the product. The dashboard helps users choose their next task; lists help them find work; the editor keeps them in context; the customer receives a clear document and payment instructions.

Keep Quart, Vue Options API, and Vuetify. Use the existing invoice workspace as the visual reference. Avoid new dependencies for this pass.

## First release: a clear, trustworthy daily workspace

1. Give the shared shell and invoice list the same restrained appearance as the editor. Use one existing font family, tabular money figures, sentence-case buttons, thin borders, and a single action colour. Remove the hard offset shadows. Preserve light, dark, and system themes. Keep secondary account and administration tools out of the main work path.
2. Correct the dashboard's meaning before making its numbers more prominent. Separate drafts from issued balances. Show amounts by currency. Label fully paid invoice totals precisely; use payment records if the intended metric is cash received. Give each summary a link to the matching invoice filter.
3. Make the invoice list useful under real conditions. Search invoice number and customer name; encode query parameters; reset pagination on search; discard stale responses. Add due dates and clear draft, unpaid, overdue, and paid filters. Define overdue from the canonical due date and remaining balance. Use real links and labelled action buttons. Show loading, empty, no-results, and retry states.

Acceptance: a user can find a draft, change it, return to a filtered list, and open an overdue invoice with a keyboard or phone. Drafts do not inflate outstanding balances. EUR and USD never appear as one total. A failed request gives a visible recovery action.

## Trust issues to resolve

| Observation | Source | Required outcome |
| --- | --- | --- |
| Outstanding totals and the outstanding list include drafts. | `stk/portal/views.py`, `stk/invoicing/views.py` | Draft value and issued debt have distinct labels and filters. |
| Dashboard and report aggregates combine currencies under the business currency symbol. | `stk/portal/views.py`, `api_reports_monthly` | Group by invoice currency; do not imply conversion. |
| Reports group fully paid invoices by invoice date and sum yearly amounts with floats. | `api_reports_monthly` | State the reporting basis. If reporting receipts, use payment dates and amounts; retain decimal arithmetic. |
| Email API returns success and sets sent status before the background SMTP operation finishes. | `api_invoice_send` | Distinguish issued, submitted to the mail server, and failed. SMTP acceptance must not be described as confirmed delivery. |
| Public invoice address, notes, and payment text bypass escaping with `safe`. | `stk/templates/invoicing/public_invoice.html` | Escape plain text and preserve line breaks with CSS; verify with markup-shaped input. |

For email, there are two real choices: await SMTP with a bounded timeout for a small, honest first version, or add durable delivery records and a worker for retries and restart recovery. The latter costs schema and operations work. Choose explicitly before implementation.

## Next workflow pass

- Customers: keep the edit dialog open on save failure, focus invalid fields, format amounts with currency, and use labelled controls. Make saved-customer edits in the invoice editor easy to understand.
- Settings and onboarding: guide users through business identity, invoice defaults, and payment details, then the first invoice. Group the current long form by task. Keep save state visible and warn before leaving unsaved edits. Readiness should use the same validation as issuing.
- Recipient experience: lead with amount due, due date, invoice reference, payment instructions, and PDF download. Check narrow screens and long names. Provide a useful expired-link page. Preserve issued snapshots and archived PDFs.
- Reports: settle the reporting basis and currency handling, then improve the presentation. A polished chart must not conceal ambiguous data.
- Accessibility and resilience: visible focus, meaningful button names, keyboard access, reduced-motion support, sufficient contrast, and explicit network failure states on each core screen.

## Later differentiator

Add a small draft assistant only after the core flow is dependable. Let a user describe work or attach a source document, review suggested customer and line items, then apply them to a draft. Show where extracted values came from and leave uncertain values unresolved. Keep issuing and sending explicit user actions. Provider, cost, privacy, and document retention need a separate decision.

## Verification

Use focused automated checks for money aggregation, currency separation, status transitions, escaping, and tenant boundaries. Extend the existing browser flow for invoice search, failures, keyboard operation, and mobile layouts. Inspect dashboard, list, editor, customer dialog, settings, and public invoice in both themes. Keep this as a sequence of small changes with an observable outcome for each.
