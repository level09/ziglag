# ZigLag: Self-Hosted Invoicing App

## Context

Build a self-hosted, open-source invoicing app inspired by InvoiceSimple, using the stk framework (`/Users/level09/projects/stk`) as the foundation. The stk framework provides auth, async SQLAlchemy, Vuetify 3 frontend (no build step), Alembic migrations, email, WebSockets, and background tasks. We add domain-specific invoicing models, blueprints, and pages on top.

Uses a neo-brutalist editorial design system (see `design-system/`).

**Dropped from InvoiceSimple** (to keep it simple):
- Expenses module
- Items catalog (type directly on invoices)
- Estimates (can add later)
- Client signatures
- Payment scheduling
- Photos on invoices

**Kept**:
- Invoices (core CRUD, line items, tax, discount, payments)
- Clients (name/email/address, autocomplete on invoices)
- Settings (business details, tax config, numbering, currency, labels)
- Reports (simple monthly summary)
- PDF generation
- Email invoices
- Shareable invoice links (public URL, no auth)

---

## Database Models

File: `ziglag/invoicing/models.py`

### BusinessSettings (singleton per user)

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| user_id | FK -> user.id | owner isolation |
| business_name | String(255) | |
| business_number | String(100) | |
| business_number_label | String(100) | default "Business Number" |
| owner_name | String(255) | |
| address_line1/2/3 | String(255) | |
| email, phone, mobile, website | String | |
| logo_path | String(500) | relative path to upload |
| tax_type | String(50) | "on_total", "per_line", "none" |
| tax_rate | Numeric(5,2) | |
| tax_label | String(50) | default "VAT" |
| tax_inclusive | Boolean | |
| invoice_prefix | String(20) | default "INV" |
| invoice_next_number | Integer | auto-incremented |
| default_invoice_notes | Text | |
| locale | String(10) | |
| currency_code/symbol | String | |
| date_format | String(20) | |
| invoice_title | String(100) | default "Invoice" |
| quantity_label, unit_cost_label | String(50) | |
| show_quantity_unit_cost | Boolean | |
| default_email_message | Text | |
| send_copy_to_self | Boolean | |
| payment_instructions, payment_paypal, payment_other | Text | |
| tax_year_begins | Integer | month 1-12 |
| created_at, updated_at | DateTime | |

Class method: `get_or_create(user_id)` returns the settings row, creating with defaults if none exists.
Method: `generate_invoice_number()` returns formatted number and increments counter.

### Client

| Column | Type |
|--------|------|
| id | Integer PK |
| user_id | FK -> user.id |
| name | String(255) not null |
| email | String(255) |
| address_line1/2/3 | String(255) |
| phone, mobile, fax | String(50) |
| notes | Text |
| created_at, updated_at | DateTime |
| invoices | relationship -> Invoice |

### Invoice

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| user_id | FK -> user.id | |
| client_id | FK -> client.id | |
| invoice_number | String(50) unique | |
| status | String(20) | draft, sent, viewed, paid, overdue, cancelled |
| date | Date | |
| due_date | Date | |
| terms | String(50) | on_receipt, net_15, net_30, net_60, custom |
| subtotal | Numeric(12,2) | |
| tax_amount | Numeric(12,2) | |
| discount_type | String(20) | percentage, fixed, or null |
| discount_value, discount_amount | Numeric(12,2) | |
| total | Numeric(12,2) | |
| amount_paid | Numeric(12,2) | |
| balance_due | Numeric(12,2) | |
| currency_code, currency_symbol | String | snapshot from settings |
| tax_type, tax_rate, tax_label, tax_inclusive | | snapshot from settings |
| notes | Text | |
| share_token | String(64) unique | for public link sharing |
| from_name, from_email, from_address, from_phone, from_business_number | | snapshot of business info |
| created_at, updated_at, sent_at, viewed_at, paid_at | DateTime | |

Key method: `recalculate()` computes subtotal from line items, applies tax (on_total or per_line, inclusive/exclusive), applies discount, computes balance_due from total minus payments.

Business details are **snapshotted** onto the invoice so old invoices stay correct if settings change later.

### InvoiceItem

| Column | Type |
|--------|------|
| id | Integer PK |
| invoice_id | FK -> invoice.id (cascade) |
| description | String(500) |
| detail | Text |
| quantity | Numeric(10,2) |
| unit_price | Numeric(12,2) |
| amount | Numeric(12,2) |
| taxable | Boolean (per-line tax toggle) |
| sort_order | Integer |

### Payment

| Column | Type |
|--------|------|
| id | Integer PK |
| invoice_id | FK -> invoice.id (cascade) |
| amount | Numeric(12,2) |
| method | String(50) (cash, bank_transfer, paypal, check, other) |
| notes | Text |
| payment_date | Date |
| created_at | DateTime |

---

## Blueprint Architecture

### `invoicing` blueprint (auth required)

**Page routes** (render templates):

| Route | Template |
|-------|----------|
| `/invoices/` | `invoicing/invoices.html` |
| `/invoices/new` | `invoicing/invoice_edit.html` |
| `/invoices/<id>` | `invoicing/invoice_edit.html` |
| `/clients/` | `invoicing/clients.html` |
| `/reports/` | `invoicing/reports.html` |
| `/settings/business/` | `invoicing/settings.html` |

**API routes** (JSON):

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/invoices` | GET | List (paginated, filter by status, search by client) |
| `/api/invoice/` | POST | Create |
| `/api/invoice/<id>` | POST | Update |
| `/api/invoice/<id>` | DELETE | Delete |
| `/api/invoice/<id>/send` | POST | Email invoice with PDF attachment |
| `/api/invoice/<id>/share` | POST | Generate share token, return URL |
| `/api/invoice/<id>/pdf` | GET | Download PDF |
| `/api/invoice/<id>/payment` | POST | Record payment |
| `/api/invoice/<id>/payment/<pid>` | DELETE | Remove payment |
| `/api/invoice/<id>/status` | POST | Update status |
| `/api/clients` | GET | List (paginated, searchable) |
| `/api/client/` | POST | Create |
| `/api/client/<id>` | POST | Update |
| `/api/client/<id>` | DELETE | Delete |
| `/api/client/search` | GET | Autocomplete (top 10 matches) |
| `/api/settings` | GET/POST | Get/update business settings |
| `/api/settings/logo` | POST | Upload logo (multipart) |
| `/api/reports/monthly` | GET | Monthly aggregates by tax year |

### `public_invoice` blueprint (no auth)

| Route | Method | Purpose |
|-------|--------|---------|
| `/i/<share_token>` | GET | Public invoice view (marks as viewed) |
| `/i/<share_token>/pdf` | GET | Public PDF download |

---

## PDF Generation

File: `ziglag/invoicing/pdf.py`

Use **WeasyPrint** (pure Python, pip-installable). Render `pdf_template.html` via Jinja2, convert to PDF bytes with `asyncio.to_thread()` to avoid blocking the event loop. Logo embedded as base64 data URI.

Template: standalone HTML/CSS (no Vuetify dependency), professional layout with header, line items table, totals, notes, payment instructions.

---

## Email

Reuse `ziglag/utils/email.py` (stk's async aiosmtplib). Invoice send endpoint generates PDF, builds email with attachment, sends via `run_in_background()`, updates status to "sent".

---

## Shareable Links

`share_token = secrets.token_urlsafe(32)` generated on first share request. Public route at `/i/<token>` renders read-only view, no auth. On first view, sets `viewed_at` and status "viewed". To revoke, null out the token.

---

## Design System

Reference: `design-system/DESIGN.md`, `design-system/code.html`, `design-system/screen.png`

### Creative Direction: "The Digital Atelier" meets Neo-Brutalism

The app uses a bold editorial aesthetic. Tonal depth, asymmetric breathing room, high-contrast typography. Not a standard Material Design look.

### Color Palette (Vuetify Theme Override in `config.js`)

| Token | Hex | Usage |
|-------|-----|-------|
| `primary` | `#353aaf` | Deep indigo-violet, brand anchor |
| `primary-container` | `#4e54c8` | Gradient partner, CTA fills |
| `surface` | `#fbf9f8` | Base canvas |
| `surface-container-low` | `#f6f3f2` | Subtle section shifts |
| `surface-container` | `#f0eded` | Card backgrounds |
| `surface-container-highest` | `#e4e2e1` | Input fills, utility areas |
| `surface-container-lowest` | `#ffffff` | Elevated cards |
| `on-surface` | `#1b1c1c` | Text (never pure black) |
| `on-surface-variant` | `#464653` | Secondary text |
| `outline-variant` | `#c6c5d5` | Ghost borders (15% opacity only) |
| `secondary` | `#4f53b6` | |
| `tertiary` | `#59454a` | |
| `error` | `#ba1a1a` | |

### Typography (Google Fonts, loaded in layout.html)

| Role | Font | Usage |
|------|------|-------|
| Display/Headline | **Plus Jakarta Sans** (700, 800) | Page titles, hero text, nav labels. Uppercase, tight tracking (-0.02em) |
| Body/Title | **Be Vietnam Pro** (400, 500, 700) | Body copy, form labels, descriptions |
| Label | **Inter** (400, 500, 600) | Micro-copy, metadata, table headers, timestamps |

High-contrast scale: jump from display-lg directly to body-md. Skip middle weights for visual drama.

### Core Rules

1. **No 1px borders.** Boundaries via tonal shifts (surface color changes between sections). Exception: neo-brutalist 4px black borders on key cards/CTAs.
2. **No pure black (#000).** Use `on-surface` (#1b1c1c) for deep contrast with warmth.
3. **No default drop shadows.** Depth via tonal nesting (white card on light-gray bg). Floating elements get primary-tinted ambient shadow: `box-shadow: 0 20px 40px rgba(53, 58, 175, 0.06)`.
4. **Neo-brutalist accents.** Key interactive elements get `border: 4px solid black` with offset shadow `box-shadow: Xpx Xpx 0 0 rgba(0,0,0,1)`. Hover: translate -y +x, remove shadow on active.
5. **Generous white space.** Double spacing when in doubt. No cramped grids.

### Component Styling (Vuetify overrides in `config.js` + `app.css`)

**Buttons:**
- Primary: gradient fill (primary -> primary-container), full roundedness or brutalist square, uppercase Plus Jakarta Sans
- Secondary: surface-container-highest bg, on-surface text, no border
- Tertiary: text-only, Inter label-md, uppercase, letter-spacing 0.1rem

**Cards:**
- `rounded-xl` (1.5rem), no borders by default
- Surface-container-lowest (#fff) on surface-container (#f0eded) for tonal lift
- Key feature cards: 4px black border + offset shadow (brutalist)

**Input Fields:**
- surface-container-highest fill, no visible border
- On focus: shift to surface-container-lowest bg + subtle primary glow (2px blur)
- No border thickening on focus

**Data Tables:**
- Font: Inter for headers, Be Vietnam Pro for cell data
- No row borders, use alternating tonal backgrounds (surface vs surface-container-low)
- Uppercase Plus Jakarta Sans for column headers

**Navigation:**
- Plus Jakarta Sans, uppercase, tight tracking, bold
- Active state: primary-container color + underline decoration
- Hover: subtle translate effect

### Applying to Vuetify (stk framework)

The stk framework loads Vuetify from static files with config in `config.js`. To apply this design system:

1. **`config.js`**: Override Vuetify theme colors with the palette above. Set component defaults:
   - `VCard: { elevation: 0, rounded: 'xl', color: 'surface-container-lowest' }`
   - `VBtn: { variant: 'elevated', rounded: 'xl' }`
   - `VTextField: { variant: 'solo-filled', bgColor: 'surface-container-highest', flat: true }`
   - `VDataTableServer: { density: 'comfortable' }`

2. **`layout.html`**: Add Google Fonts link for Plus Jakarta Sans, Be Vietnam Pro, Inter. Override Vuetify typography CSS vars.

3. **`app.css`**: Custom CSS for neo-brutalist accents, font assignments, input focus states, button gradients, shadow utilities. Keep these as utility classes that templates can apply selectively.

### Brand in UI

- App name in nav: **ZIGLAG** (Plus Jakarta Sans, black weight, uppercase, tight tracking)
- No Ø character (that was the InvoiceSimple-inspired mockup)

---

## Frontend

All pages extend `layout.html`, mount Vue 3 apps with Vuetify, use `${ }` delimiters, follow stk patterns exactly. Design system applied via Vuetify theme overrides + custom CSS.

**Navigation** (`navigation.js`):
- Dashboard, Invoices, Clients, Reports, Business Settings, Change Password

**Templates**:

| Template | Key Components |
|----------|---------------|
| `invoices.html` | v-data-table-server, tabs (All/Outstanding/Paid), search, "New Invoice" btn |
| `invoice_edit.html` | Two-column From/To, line items editor, summary, notes, sidebar with email/tax/discount/share/print |
| `clients.html` | v-data-table-server, dialog CRUD |
| `reports.html` | Monthly table by tax year, year selector |
| `settings.html` | Form sections: business details, tax, numbering, notes, region, labels, payment methods |
| `public_invoice.html` | Minimal layout, read-only invoice, Download PDF link |
| `pdf_template.html` | Standalone HTML/CSS for PDF rendering |

**New Vue component**: `InvoiceLineItems.js` for the dynamic line items editor (add/remove/reorder rows, auto-calculate amounts).

**Tax calculation**: JavaScript mirrors server logic for real-time UX. Server `recalculate()` is authoritative on save.

---

## File Structure

```
ziglag/
├── app.py                     # register invoicing + public_invoice blueprints
├── settings.py                # add UPLOAD_FOLDER, MAX_LOGO_SIZE
├── extensions.py              # unchanged
├── invoicing/
│   ├── __init__.py
│   ├── models.py              # BusinessSettings, Client, Invoice, InvoiceItem, Payment
│   ├── views.py               # all page + API routes
│   ├── public.py              # public share routes (no auth)
│   └── pdf.py                 # WeasyPrint PDF generation
├── user/                      # unchanged from stk
├── public/                    # unchanged from stk
├── portal/                    # redirect dashboard -> /invoices
├── utils/                     # unchanged
├── tasks/                     # unchanged
├── static/
│   ├── js/
│   │   ├── navigation.js      # updated with invoicing nav
│   │   └── components/
│   │       └── InvoiceLineItems.js  # NEW
│   ├── css/
│   │   └── invoice.css        # invoice-specific styles
│   └── uploads/               # logo uploads
├── templates/
│   └── invoicing/
│       ├── invoices.html
│       ├── invoice_edit.html
│       ├── clients.html
│       ├── reports.html
│       ├── settings.html
│       ├── public_invoice.html
│       ├── pdf_template.html
│       └── email_invoice.html
alembic/versions/
    └── xxxx_invoicing_models.py  # NEW migration
pyproject.toml                    # add weasyprint>=62.0
```

---

## Implementation Phases

### Phase 1: Project Setup + Models
- Copy stk -> ziglag, rename package in all imports
- Add weasyprint to pyproject.toml
- Create `invoicing/models.py` with all 5 models
- Generate + run Alembic migration
- Verify app starts with new tables

### Phase 2: Settings + Clients
- Create `invoicing/views.py` with blueprint + auth guard
- Settings API (GET/POST) + logo upload
- Client CRUD API + autocomplete search
- Update navigation.js
- Settings template + Clients template
- Register blueprint in app.py

### Phase 3: Invoice CRUD (core)
- Invoice list API (paginated, filtered, searchable)
- Invoice create/update/delete APIs
- Payment record/delete APIs
- Status update API
- `InvoiceLineItems.js` component
- Invoice list template (tabs, search, table)
- Invoice edit template (From/To, line items, summary, notes, sidebar)

### Phase 4: PDF Generation
- `invoicing/pdf.py` with WeasyPrint
- `pdf_template.html` standalone HTML/CSS
- PDF download API endpoint
- Logo embedding as base64

### Phase 5: Email + Sharing
- Email invoice template
- Send API (PDF attachment, fire-and-forget)
- Share token generation API
- `invoicing/public.py` blueprint
- Public invoice view template
- Public PDF download

### Phase 6: Reports + Dashboard
- Monthly report API (aggregate by month/year)
- Reports template with year selector
- Dashboard with stats cards + recent invoices

### Phase 7: Polish
- Activity logging on all CRUD operations
- Input validation, CSRF, user_id scoping
- Overdue status auto-detection
- Demo seed command

---

## Key stk Files to Reference

- `stk/user/models.py` -- model pattern (dataclass, Column, to_dict/from_dict, lazy="selectin")
- `stk/user/views.py` -- blueprint pattern (before_request auth, paginated API, CRUD, Activity logging)
- `stk/templates/cms/users.html` -- Vue template pattern (v-data-table-server, dialog CRUD, JSON script tags)
- `stk/app.py` -- app factory, blueprint registration
- `stk/tasks/__init__.py` -- run_in_background pattern
- `stk/utils/email.py` -- async email
- `stk/static/js/navigation.js` -- nav structure
- `stk/static/js/config.js` -- Vuetify config, delimiters

## Dependencies

Only one new dependency: `weasyprint>=62.0`

System requirements for WeasyPrint: cairo, pango, gdk-pixbuf (available via Homebrew on macOS, apt on Linux).

---

## Verification

After each phase, verify by:
1. `uv run quart run` -- app starts without errors
2. Navigate to each page in browser -- renders correctly
3. CRUD operations via UI -- data persists
4. PDF download -- professional layout with all data
5. Email send -- arrives with PDF attachment
6. Share link -- opens without login, shows read-only invoice
7. Reports -- shows correct monthly aggregates

---

## Architectural Decisions

1. **Server-side pagination throughout.** Following stk's v-data-table-server pattern. No client-side data loading.
2. **Snapshot business details on invoice.** Invoice stores its own from_name, from_address, etc. Old invoices stay correct if settings change.
3. **Tax calculation on both client and server.** JS calculates in real-time for UX. Server recalculate() is authoritative on save.
4. **Single blueprint for all invoicing routes.** One views.py file. Extract into sub-modules only if it exceeds 300+ lines.
5. **WeasyPrint for PDFs.** Pure Python, no external binary, works with Jinja2 templates.
6. **No template system for MVP.** One fixed PDF layout. Template customization can come later.
7. **Share token over signed URLs.** Random 32-byte token, stored on invoice, no expiry management. Null to revoke.
