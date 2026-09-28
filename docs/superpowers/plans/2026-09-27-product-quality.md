# ZigLag Product Quality Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. Steps use checkbox syntax for tracking. This document is a plan, not authorization to deploy, migrate a live database, or send email to real customers.

**Execution status (2026-09-28):** Releases A and B implemented and verified locally. Actual browser zoom remains an explicit verification limit. Route tests are consolidated in `tests/test_product_workspace.py`; Release B browser coverage is in `tests/browser_release_b.py`, instead of duplicating the original fixture. Paid includes non-positive balances to match the model, including overpayments. See `docs/product-review-2026-09-27.md` for verification and limits.

**Goal:** Make the full path from business setup to a paid invoice clear, consistent, and dependable.

**Architecture:** Keep the current server-rendered Quart pages, request-scoped SQLAlchemy sessions, Vue Options API, and Vuetify components. Share invoice selection rules between the dashboard and list. Extend existing templates and configuration; add no frontend build system or general-purpose component framework.

**Tech stack:** Python with uv, Quart, SQLAlchemy 2, Alembic, Vue 3, Vuetify 3, fpdf2, unittest, Playwright.

**Spec:** [Product review](../../product-review-2026-09-27.md), informed by the [UX scout](../../ux-edge-scout-2026-09-27.md). Source review completed on 2026-09-27; the implementation status above records the completed scope.

## Global constraints

- Keep Quart, Vue Options API, and Vuetify. Use the existing invoice workspace as the visual reference. Avoid new dependencies for this pass.
- Preserve `${}` delimiters, request-scoped sessions, role checks, and user ownership checks.
- Issued content stays locked. Serve its archived PDF and legal snapshots.
- Amounts remain Decimal values on the server and decimal strings in JSON. Never add different currencies into one displayed amount.
- Preserve light, dark, and system themes. Use plain, sentence-case labels and no em or en dashes in product copy.
- Changes remain local until a separate commit, push, or deployment instruction. Check current changes before editing; preserve the editor and stk fixes already present.
- No full stk upgrade, Vuetify 4 migration, new hosting service, background worker, or paid model integration in these releases.

## Design decisions

The visual direction is a quiet document workspace: warm neutral background, white document surfaces, dark ink, and one primary action style. Keep the current logo. Use Plus Jakarta Sans, already loaded, as the shared interface font with a system fallback. Use tabular numerals for money. Use the accepted navy navigation and teal primary colour, with distinct blue drafts, amber overdue, green paid, and cyan issued states. See `docs/color-direction-2026-09-28.md` for the colour pass.

Use 4, 8, 12, 16, 24, and 32 px spacing; 1 px borders; 8 px control and panel corners; and shadows only for floating menus or dialogs. Use 14-16 px body text, 24-28 px page titles, and at least 44 px touch targets for primary mobile controls. Keep the invoice document visually distinct from surrounding controls. Check contrast in the rendered themes before accepting colours.

Primary navigation: Dashboard, Invoices, Customers, Reports, Business settings. Keep password and security actions in the account menu. Keep administration accessible to admins in a separate group. Page headers have a title, brief context when useful, and one main action.

At narrow widths, close the navigation drawer, stack editor regions, and show the invoice list as a readable compact layout. Avoid hiding the amount, due date, or next action. Motion is limited to short state transitions and respects reduced-motion preferences.

### Choices with real costs

| Area | Recommended small version | Larger alternative and cost |
| --- | --- | --- |
| Email | Await SMTP with a bounded timeout; show accepted, failed, or outcome unknown for that attempt. | Durable delivery records and a worker allow restart recovery and retries, but require a schema change and worker operations. |
| Reports | Preserve the current basis, label it “Paid invoices by invoice date”, and separate currencies. | Cash receipts by payment date is a different report. It requires explicit rules for refunds, cancellations, and historical payment records. |
| AI | After these releases, test pasted notes to a reviewed draft. | Document import or connected billing sources add extraction, retention, provider, and deduplication work. |

The plan uses the small versions. No delivery history or cash accounting claim is added. A change to these choices changes the scope before implementation.

## Review focus

1. Mixed currencies and partial payments must not produce misleading totals. Covered by Tasks 1 and 5.
2. Slow or failed requests must not replace newer input or close a form with unsaved work. Covered by Tasks 3 and 6.
3. Legacy sent/viewed records do not prove an email was delivered. Covered by Task 4.
4. Long text, markup-shaped text, and missing optional fields must render safely on a phone. Covered by Tasks 2 and 7.
5. Another user's records and revoked invoice links must remain inaccessible. Covered by Tasks 1, 3, 7, and 8.

## Release A: the daily workspace

Tasks 1-5 form the first release. They can be reviewed separately, but the release is complete only when the shared visual style and all correctness changes below pass together.

### Task 1: shared invoice filters and accurate dashboard totals

**Files:** create `stk/invoicing/queries.py` and `tests/test_invoice_queries.py`; modify `stk/portal/views.py`, `stk/invoicing/views.py`, and `stk/templates/dashboard.html`.

**Interfaces:** add `invoice_conditions(user_id: int, status: str, today: date) -> list[ColumnElement[bool]]`. Both dashboard aggregates and list/count queries consume these SQL expressions. Supported filters: `all`, `draft`, `outstanding`, `overdue`, `paid`, `cancelled`. Unknown filters return a 400 response at the endpoint.

- [ ] Add database-backed tests with a temporary database and two users. Use this fixture for user A: draft EUR 100; issued unpaid EUR 200 due yesterday; issued partially paid EUR 300 with EUR 50 recorded and due tomorrow; fully paid EUR 400; cancelled EUR 500; issued unpaid USD 600. Give user B a separate EUR invoice. Create records through normal APIs where possible; use isolated ORM fixtures only to pin query edge cases.
- [ ] Define draft from `issued_at IS NULL` and non-cancelled state. Outstanding requires issued, non-cancelled, positive balance. Overdue adds `due_date < today`; no due date and due today are not overdue. Paid requires issued, non-cancelled, zero balance, and the existing paid state. Preserve the `outstanding` API name while labelling it “Unpaid”. Use the same server date convention as the existing model, passed explicitly for tests.

```python
# Shared SQL predicate for outstanding; add ownership in every case.
conditions = [
    Invoice.user_id == user_id,
    Invoice.issued_at.is_not(None),
    Invoice.status != "cancelled",
    Invoice.balance_due > 0,
]
if status == "overdue":
    conditions.append(Invoice.due_date < today)
```

- [ ] Run `uv run python -m unittest tests.test_invoice_queries -v` against the initial tests; confirm the current draft-inclusive behavior fails.
- [ ] Group outstanding amounts by `Invoice.currency_code`. Dashboard context contains `draft_count`, `outstanding_by_currency`, `overdue_count`, and recent invoice rows with `currency_code` and `due_date`. Each currency row has `currency_code`, `amount` as a decimal string, and `count`. Order currencies by code. Do not show a paid-invoice total as cash received.
- [ ] Replace the four generic dashboard cards with drafts to finish, unpaid amounts by currency, and overdue work. Each links to the matching list filter. Keep recent invoices below these actions; use per-row currency. An empty account offers business setup and its first invoice.

```python
# Required fixture results after user scoping.
self.assertEqual(outstanding, {"EUR": Decimal("450.00"), "USD": Decimal("600.00")})
self.assertEqual(draft_count, 1)
self.assertEqual(overdue_count, 1)
```

- [ ] Verify the list IDs and dashboard counts agree, user B is absent, and due-today/no-due-date cases stay out of overdue. Re-run the query tests.

### Task 2: shared visual system and navigation

**Files:** modify `stk/static/css/app.css`, `stk/static/css/layout.css`, `stk/static/js/config.js`, `stk/static/js/navigation.js`, `stk/templates/layout.html`, and the dashboard/editor styles where global changes conflict.

**Interfaces:** use the existing Vuetify theme tokens as the colour source and existing navigation role filtering. Add shared `.page-header` and `.money` classes; do not create a new UI library.

- [ ] Apply the visual decisions above to configuration and shared styles. Remove hard offset shadows and forced uppercase from ordinary controls. Remove duplicate font loading from the layout as part of selecting one font.

```css
.money { font-variant-numeric: tabular-nums; white-space: nowrap; }
.page-header { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
@media (prefers-reduced-motion: reduce) {
  .page-header, .invoice-paper { transition: none; }
}
```

- [ ] Keep navigation destinations and admin role restrictions. Move duplicate account actions into the existing account menu. Label icon buttons, add logo alternative text, and make focus visible on links and actions.
- [ ] Use page-specific document titles. Preserve authentication page readability because they inherit the same shell. Bring mobile drawer behavior into the shared shell and remove only the editor-specific duplication made unnecessary by that change.
- [ ] Inspect dashboard, invoice editor, login, account menu, and navigation at 390 px and 1440 px, in both themes and at 200% browser zoom. Test a long customer name, blocked font request, keyboard navigation, and reduced motion. Fix clipped controls and unreadable text before moving on.

### Task 3: invoice list that stays useful under failure

**Files:** modify `stk/invoicing/views.py` and `stk/templates/invoicing/invoices.html`; create `tests/browser_product_workspace.py` using the temporary server pattern in `tests/browser_invoice_editor.py`; extend `tests/test_invoice_queries.py` for search.

**Interfaces:** retain `/api/invoices?page=1&per_page=25&status=outstanding&search=...`. Add `due_date` and `issued_at` to list rows. Use Task 1 conditions for both results and counts. Page URL query parameters hold the same filter, search, and page values.

- [ ] Test number-only search for a draft with no customer, customer names containing `&`, literal `%` and `_`, and another user's matching customer. Search with an outer join, use escaped SQL wildcard characters, and match invoice number plus the appropriate saved customer name. For issued invoices, prefer the legal name snapshot.
- [ ] Provide All, Drafts, Unpaid, Overdue, and Paid filters, plus a Cancelled choice. Show invoice number as a real link, customer, date/due date, status, and amount. Keep fixed newest-first sorting and disable unsupported sortable headers.
- [ ] Use Axios `params` rather than URL interpolation. Reset page on search/filter change. Increment a request sequence; only the latest sequence may update rows, error, or loading state. Preserve the URL state with browser history and restore it on Back.

```javascript
const requestId = ++this.requestId;
const response = await axios.get('/api/invoices', {params: {
    page: this.page, per_page: this.itemsPerPage,
    status: this.statusFilter, search: this.search
}});
if (requestId !== this.requestId) return;
this.items = response.data.items;
this.total = response.data.total;
```

- [ ] Give initial loading a stable layout. Distinguish “No invoices yet” from “No matching invoices”. Keep previous rows on refresh failure with a visible error and Retry button; never imply stale rows match a new filter. The latest request owns the final loading state, including errors.
- [ ] In the browser test, delay the first search response and return the second first. Assert the latest query remains visible. Inject 503, retry, open a row with the keyboard, then use Back and assert the filter/page remain. Check mobile width and a long invoice number.

### Task 4: honest email results

**Files:** modify `stk/invoicing/views.py` and `stk/templates/invoicing/invoice_edit.html`; add `tests/test_invoice_email.py`; adjust status text in list and public templates.

**Interfaces:** keep the send endpoint. A success response means SMTP acceptance, not delivery. Retain existing persisted status values for compatibility; display `sent` as “Issued” and `viewed` as “Link opened”. Explain that a link request is not proof of a person reading it. Do not infer delivery from legacy `sent_at`, which is currently also set during issuance.

- [ ] Add async endpoint tests that mock `aiosmtplib.send`; no real email. Cover acceptance, SMTP rejection, timeout, paid invoice resend, cancelled invoice, and wrong owner.
- [ ] Replace fire-and-forget scheduling with an awaited call bounded by 30 seconds. Disable the send button while pending. Do not automatically retry a timeout: the server may have accepted the message before the connection failed.
- [ ] On acceptance, return “Email accepted by the mail server”. On an explicit SMTP failure, return a recoverable error. On timeout or loss of the HTTP response, show “Email status could not be confirmed. Check before sending again.” Keep the invoice issued and its PDF unchanged after any send attempt. Resending a paid invoice must not change its paid status.

```python
# Assertions on the endpoint result, with SMTP mocked by the test.
self.assertEqual(response.status_code, 200)
self.assertEqual((await response.get_json())["message"], "Email accepted by the mail server")
self.assertEqual(invoice_after.status, "paid")  # paid invoice resend
self.assertEqual(pdf_bytes_after, pdf_bytes_before)
```

- [ ] Return a useful error without SMTP credentials or internal exception text. Keep diagnostic detail in existing server logging. Do not add persistent delivery badges, automatic retries, or reinterpret old timestamps. Durable delivery history remains the separate larger option.
- [ ] Run `uv run python -m unittest tests.test_invoice_email -v` and verify pending/error/success feedback in the browser using intercepted responses.

### Task 5: precise reports

**Files:** modify `api_reports_monthly` in `stk/invoicing/views.py` and `stk/templates/invoicing/reports.html`; create `tests/test_invoice_reports.py`.

**Interfaces:** retain the monthly endpoint; add a `currency` query parameter and `currencies` response list. Return one selected currency's months and yearly total, plus `currency_code`. Use settings currency if available in the result, otherwise the first available code; when there are no results, use the settings currency and zero totals. The UI displays the selected code.

- [ ] Test paid EUR and USD invoices in the same month, a partial payment, a draft, cancelled invoices, user isolation, and a December invoice paid in January. The report groups eligible fully paid issued invoices by invoice date and currency. Include a partial invoice only after it becomes fully paid, under its invoice month. State this behavior beneath the title.
- [ ] Title the page “Paid invoices” with “By invoice date, calendar year”. Remove “Tax year” claims from this report. Do not change the saved fiscal-year setting or invent accounting rules.
- [ ] Use database decimal sums and Decimal yearly arithmetic. Currency selection, year selection, loading, no-data, and Retry states are explicit. Prevent stale year/currency responses from replacing a newer selection.

```python
# Endpoint fixture: EUR 0.10 and EUR 0.20 paid invoices, plus USD 9.00.
self.assertEqual(report["currency_code"], "EUR")
self.assertEqual(report["yearly_total"], "0.30")
```

- [ ] Run `uv run python -m unittest tests.test_invoice_reports -v`; check report controls and totals in both themes. Do not add charts until the table and labels are correct.

## Release B: setup, customers, and the recipient

### Task 6: forms that keep users in control

**Files:** modify `stk/templates/invoicing/clients.html`, `stk/templates/invoicing/settings.html`, `stk/templates/invoicing/email_invoice.html`, `stk/invoicing/models.py`, relevant client/settings endpoints in `stk/invoicing/views.py`, and `stk/templates/dashboard.html`; extend `tests/browser_product_workspace.py` and `tests/test_invoice_email.py`.

**Interfaces:** keep existing create/update routes and business profile validation. Replace the customer list's misleading single “Total billed” figure with paid-invoice totals grouped by currency, labelled “Paid invoices”; expose them as `paid_totals_by_currency` rows with `currency_code` and decimal-string `amount`. Preserve `total_billed` in API responses for compatibility during this release, but stop using it in the UI.

- [x] Keep the customer dialog open while saving and on failure. Disable duplicate submission, show the server error beside the form, and close only after success. Use real labelled buttons for edit/delete. Add loading, no-results, and Retry states to customer search.
- [x] Apply issued, paid, non-cancelled predicates to customer totals and group by invoice currency. Verify EUR and USD render separately. Do not change customer records when only searching in the invoice editor.
- [x] Group settings into Business identity, Invoice defaults, Payment instructions, and Email preferences. Keep primary save feedback visible, track dirty state from a stable snapshot, and warn before leaving unsaved edits. Restore pending controls after failed saves.
- [x] Use `default_email_message` as the plain-text introduction in both email variants, followed by the existing invoice link. Escape it in HTML and preserve line breaks. When `send_copy_to_self` is enabled, include the authenticated account email as an additional envelope recipient without exposing it in recipient headers; deduplicate it if it matches the customer. Mock SMTP and assert the introduction, escaping, and recipient list. Audit the remaining settings controls against their read paths and report unsupported behavior before expanding scope. Avoid changing invoice numbering, tax, or currency defaults during presentation work.
- [x] Add a dashboard setup checklist backed by the existing `business_profile_missing` validation. Required fields block issue as before; optional payment details remain optional. Each item links to its settings section. Once the profile is ready, link directly to creating the first invoice.
- [x] Browser checks: reject customer save with 503 and assert typed values remain; retry successfully; edit settings and test navigation protection; complete required setup through the UI and issue through the normal editor. Assert the checklist and issue validation agree.

### Task 7: safe, clear recipient experience

**Files:** modify `stk/templates/invoicing/public_invoice.html` and `stk/invoicing/public.py`; create `stk/templates/invoicing/invoice_unavailable.html` and `tests/test_public_invoice.py`; extend `tests/browser_product_workspace.py`.

**Interfaces:** keep `/i/<token>` and `/i/<token>/pdf`. Preserve the same generic 404 result for invalid, expired, and revoked tokens. The page may explain that the link is unavailable without revealing invoice identity or customer information.

- [x] Render addresses, notes, and payment instructions as escaped text with CSS line-break handling. Remove `safe` from plain user text. Test an HTML-shaped value and assert it is visible text, not an element.

```html
<div class="invoice-text">{{ invoice.notes }}</div>
<style>.invoice-text { white-space: pre-line; overflow-wrap: anywhere; }</style>
```

- [x] Lead with invoice reference, amount due, currency code, due date, and Download PDF. Keep payment instructions next to these details. Retain template variants but align spacing, focus states, and responsive behavior with the product direction.
- [x] For issued invoices, use snapshots even when a snapshot is intentionally empty. Do not substitute current customer data for empty issued fields. Keep draft fallback behavior separate. Never regenerate an issued PDF to recover from a missing archive; report an error without leaking its path.
- [x] Use the generic unavailable template for link failures. Test invalid, expired, and revoked tokens, archived PDF bytes, missing archive, long addresses, empty optional fields, and markup-shaped notes.
- [x] Browser check at 390 px in light/dark system settings: no page overflow, payment details remain readable, download works, keyboard focus is visible. Verify another user's authenticated endpoints remain unavailable even when a public token is known.

## Release gate

### Task 8: prove the full path

**Files:** extend `tests/browser_product_workspace.py`, update `docs/product-review-2026-09-27.md` with actual completed scope, and update the project run documentation if a new command is needed.

- [x] Use temporary SQLite and an isolated instance directory, following `tests/browser_invoice_editor.py`. Create the business and customer through their normal UI/API paths. Issue invoices through normal validation so snapshots, access state, and archived PDFs exist. Send only mocked email; never contact real recipients.
- [x] Exercise setup, customer creation, draft editing, review/issue, list search, recorded partial/full payment, dashboard filters, reports, and public PDF. Assert real amounts and state transitions. Include the failure cases assigned above; do not rely on row counts or source-string checks alone.
- [x] Run the existing editor browser test to protect autosave, in-flight edits, retry, and issued locks. Capture desktop/mobile screenshots of changed screens and inspect them; screenshots alone are not a pass.

```bash
uv run ruff check .
uv run ruff format --check stk/invoicing/models.py stk/invoicing/views.py stk/invoicing/public.py stk/invoicing/queries.py stk/portal/views.py tests/test_product_workspace.py tests/browser_product_workspace.py tests/browser_release_b.py
uv run python -m unittest discover -s tests -v
uv run python checks.py
uv run python -m tests.browser_invoice_editor
uv run python -m tests.browser_product_workspace
uv run python -m tests.browser_release_b
git diff --check
```

Local tests may use `UV_CACHE_DIR=/tmp/ziglag-uv-cache` if needed. Check current migration heads before any migration proposal; do not rely on the older chain in project notes. These releases do not require a planned schema change.

- [ ] Confirm no browser console errors, no horizontal page overflow at 390 px, and useful focus order at 200% zoom. Confirm role restrictions, both themes, and the server-owned date/currency values.
- [x] Review the diff against task scope, record the commands actually run and any unverified areas, then present the release for review. No production deployment or external publication is part of this gate.

## Finish line and later work

The product pass is finished when Releases A and B pass Task 8: a new user can configure the business, create a customer, draft and issue an invoice, share its immutable PDF, record payments, and find the result again without losing work or seeing misleading amounts or delivery claims.

The later AI experiment remains separate: pasted notes produce proposed draft fields with source text, unresolved values stay blank, and the user applies the proposal. Calculations and issue/send actions stay in existing application code. Measure total time to a correct reviewed draft against manual entry on synthetic examples before choosing a provider or adding document upload. No AI feature is required to finish this plan.

## Plan self-review

The first-release visual, workflow, money, and email requirements map to Tasks 1-5. Customer editing, setup/settings, and public invoice requirements map to Tasks 6-7. Accessibility and failure handling are assigned to their owning screens and checked again in Task 8. AI and durable email delivery are explicitly separate scope. Proposed interfaces are named above; no deployed behavior is claimed by this document.
