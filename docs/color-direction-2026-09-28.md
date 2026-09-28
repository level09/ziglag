# ZigLag colour direction

The first visual pass made navigation, actions, and data too similar. This pass restores their hierarchy with a consistent use of colour in the existing application.

- Deep navy identifies the navigation area in both themes. The active destination has a mint edge and contrasting fill.
- Teal identifies primary actions and invoice links. The unpaid summary uses a stronger teal surface because it is the main monetary summary, not a paid-success indicator.
- Blue identifies drafts, amber overdue items, green paid invoices, and cyan issued/link-opened records. Each status also has a text label.
- Tinted page and table-header surfaces separate controls from records. White or dark raised panels hold the data.
- Light and dark modes use separate foreground/background pairs from the central Vuetify configuration.

Applied to the shared shell, dashboard, list, report surfaces, and editor status. No business rules or user data were changed in this pass. Preview screenshots use fictional records in an isolated database.

## Current references

[Linear's March 2026 UI refresh](https://linear.app/changelog/2026-03-12-ui-refresh) distinguishes navigation from content and makes controls consistent. [Atlassian's colour foundations](https://atlassian.design/foundations/color) separate semantic meaning from decorative accents. These informed the hierarchy and colour roles; this is an original ZigLag palette, not a copy of either product.

## Verification

The workspace browser flow passes in light and dark modes and at phone widths. Measured rendered light-mode status text contrast: Draft 5.67:1, Paid 5.31:1, Overdue 5.55:1, Issued 5.43:1. These measurements cover the badges, not a full accessibility audit. Desktop, dark-mode, invoice-list, and mobile previews were inspected. The full unit suite passes (113 tests).

Release B follows this visual direction: customer/settings form recovery, business setup guidance, and the public invoice experience. The colour pass does not claim those features are complete.
