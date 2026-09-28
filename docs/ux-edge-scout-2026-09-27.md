# ZigLag UX scout

Research date: 2026-09-27. This is a proposal, not an approved implementation plan.

## Recommendation

Make the invoice itself the main workspace. Paste work notes, review a populated
draft next to the source, correct missing facts in place, then issue it through
the existing validation path. The target is less time to a correct invoice.

Assumption: the main user is a freelancer or small business issuing invoices.
The repository supports this use, but no customer interviews were part of this scan.

The current editor switches between edit and preview and uses an explicit Save
action. The browser smoke screenshot shows a dashboard dominated by counts and
navigation. Both are clear opportunities for reducing movement between screens.

## Evidence and transferable ideas

| Source | Verified capability | Proposed use and decision |
| --- | --- | --- |
| [Midday Assistant](https://midday.ai/assistant/) | Its product page describes natural-language invoice creation and business actions. | Borrow the task-oriented entry point. Keep the editable invoice visible during review. The public README is stale on invoicing; do not treat it as current feature evidence or copy its stack. |
| [Linear, July 23](https://linear.app/changelog/2026-07-23-agent-assisted-editing) | Agent edits have separate highlights, author attribution, and version checkpoints. | Borrow the review mechanism: show which invoice fields changed and their source. Undo applies to drafts; it must not bypass issued-invoice locks. |
| [A2UI Vuetify renderer](https://github.com/alis-exchange/a2ui-vuetify-renderer) | JSONL messages create surfaces and update components/data through a controlled catalog. | Park direct adoption. It requires Vue 3.5.35+, Vuetify 4.1.1+, web_core, and a build integration. Existing Vue components can test a fixed set of invoice review cards first. |
| [AG-UI](https://github.com/ag-ui-protocol/ag-ui) | Typed events expose task progress, tool calls, and shared state. | Borrow the event model if drafting takes several steps. A plain Quart response is the simpler first version. A protocol does not provide persistence or permission checks by itself. |
| [Docling extraction](https://github.com/docling-project/docling/blob/main/docling/.agents/skills/docling/references/extraction.md) | Its beta DocumentExtractor returns typed fields, raw text, page results, and errors from PDFs/images. | Test later for importing an old invoice or contract. Begin with pasted text. Hardware cost, extraction accuracy, and reliable field-level source locations remain untested. |
| [CLI-Anything](https://github.com/HKUDS/CLI-Anything) | Generates structured command interfaces for existing software. | Borrow the procedure: expose narrow, validated business operations to agents. stk already supplies inspection and verification; build on that rather than add a second general harness. |

The weekly [GitHub Trending](https://github.com/trending?since=weekly) page was
checked on the research date. CLI-Anything, Univer, and several agent tooling
repos appeared. This is an observation of that page, not evidence of product fit.

Raw README files and Linear pages were retrieved. Midday's raw product-page
request returned 403; its indexed official page supplied that capability claim.
No product accounts or paid services were tested.

Repository metadata showed recent pushes for A2UI Vuetify (September 9), AG-UI
(September 25), and Docling (September 25). The first reports Apache-2.0 and the
other two MIT. Push dates establish activity, not a release date or reliability.
No new dependency is approved by this research. Integration examples, version
pins, and relevant open issues need checking before adoption.

## Three directions

| Direction | User experience | Cost and main weakness |
| --- | --- | --- |
| Fast manual workspace | Inline invoice editing, customer defaults, keyboard actions, continuous preview. | Smallest scope; still requires entry of work details. This is the baseline. |
| Assisted invoice workspace | Paste notes, inspect populated fields, resolve only missing facts, approve the draft. | Recommended. Adds extraction, source tracking, and review. It fails if checking guesses takes longer than typing. |
| Background billing desk | Connected timesheets and other sources prepare invoices and reminder drafts in an action queue. | Highest integration and operating cost. Needs durable jobs, source deduplication, and reliable ownership. Consider after the workspace succeeds. |

## Proposed interaction

Example: paste "Acme, September support, 12 hours at EUR 95, due in 14 days."
The app finds possible customer matches and fills only supported fields.
The invoice occupies the center of the screen. Source notes sit beside it.
Selecting an inferred field shows the source phrase or saved setting.
Missing information appears at the affected field, with a focused control.

Use a quiet document surface, clear type, aligned amounts, and one main action
that reflects the next valid step. Changes briefly highlight in place. Keep
stable layouts while work runs and support reduced motion. On small screens,
source evidence opens as a sheet. These are proposed design choices, not results
from usability tests.

The handoff is:

`notes -> typed field proposal -> existing customer/settings lookup -> editable draft -> existing issue validation`

Custom work: a proposal schema, source references, a preview adapter, and draft
revision checks. Calculations remain in application code. Customer matches must
be scoped to the signed-in user. Unknown facts remain unset. A stale proposal
must not overwrite a newer edit. Issuing and sending require explicit user action.
The model cannot choose tax treatment without review or bypass invoice locks.

The next home view can show ready-to-bill work, incomplete drafts, and overdue
invoices. Each item should contain the evidence and the next action. Without a
bank feed, show payment status from recorded payments; do not imply live cash
reconciliation.

## Smallest decision test

Propose a two-day prototype with 20 synthetic or explicitly approved examples:
simple hourly work, fixed fees, ambiguous customer names, missing rates, mixed
currencies, and conflicting dates. Compare against the current manual editor.
Start with pasted text and fixed Vue controls. No connectors or new UI protocol.

Measure total time from input to a correct reviewed draft, including corrections.
Proposed pass threshold: at least 40% lower median time, no increase in final
field errors, all unsupported facts visibly unresolved, and no unintended issue
or send action. Budget any model trial at EUR 10 maximum, subject to approval.
Stop if review is slower than manual entry or ambiguity is hidden. These are
targets; the experiment has not run.

## Framework fixes applied in this pass

Source: local `../stk`, HEAD `900779b7325af13500bbb312beb91ebd4d5675fc`
(2026-08-25), version 14.1.0. GitHub HEAD was not checked for stk.

- `8fe52e5`: detect real authentication guards and repair the recovery form.
- `c7374eb`: keep navigation filtering pure and filter nested items consistently.
- `bf14265`: preserve component link colors and add low-contrast browser checks.

The fixes were adapted to the existing `stk/commands.py` layout. This is a
selective backport, not a full 14.1 upgrade. The CLI split, shell, doctor/watch,
Vuetify 4 migration, asset refresh, and upstream dependency refresh remain separate.
The project still identifies its framework base as 13.4.1.
