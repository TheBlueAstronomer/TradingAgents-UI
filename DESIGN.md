---
name: "TradingAgents Research Office"
description: "An archival research docket that assembles streamed analyst evidence into a legible decision record."
colors:
  paper: "#e9ecec"
  paper-deep: "#dce1e0"
  ink: "#1d252b"
  graphite: "#53605e"
  moss: "#3f6257"
  moss-hover: "#29473f"
  amber: "#a96e18"
  line: "#aeb8b5"
  field-line: "#83918d"
  danger: "#982d2d"
  focus: "#75500d"
  open-folio: "#f7f8f7"
  field: "#f8faf9"
  filed-tab: "#e1e7e4"
  skeleton: "#cbd3d0"
  error-ink: "#721d1d"
  error-paper: "#f5dfda"
  error-line: "#c98c83"
  white: "#ffffff"
typography:
  display:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.65rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 700
    lineHeight: 1.45
    letterSpacing: "-0.015em"
  body:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
  body-compact:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
  label:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.79rem"
    fontWeight: 750
    lineHeight: 1.45
    letterSpacing: "0.025em"
  folio:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.7rem"
    fontWeight: 800
    lineHeight: 1.45
    letterSpacing: "0.12em"
  status:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 800
    lineHeight: 1.45
    letterSpacing: "0.06em"
rounded:
  square: "0"
  control: "2px"
  dot: "50%"
components:
  button-primary:
    backgroundColor: "{colors.moss}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
  button-primary-hover:
    backgroundColor: "{colors.moss-hover}"
    textColor: "{colors.white}"
  field:
    backgroundColor: "{colors.field}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "7px 9px"
  report-tab-active:
    backgroundColor: "{colors.filed-tab}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "8px 9px 7px"
  status-completed:
    backgroundColor: "{colors.field}"
    textColor: "{colors.moss}"
    typography: "{typography.status}"
    rounded: "{rounded.square}"
    padding: "4px 8px"
---

# Design System: TradingAgents Research Office

## Overview

**Creative North Star: "Research Docket"**

The interface behaves like an institutional research file assembled in public: cool archival stock holds charcoal ink, ruled divisions, graphite annotation, restrained docket amber, and deep moss marks of authority. Density is deliberate and legible rather than dashboard-like; the page shows the chain from configuration through evidence to decision without adopting a trading-terminal aesthetic.

Hierarchy comes from differentiated document roles. A bordered cover sheet contains configuration, the dashboard docket desk pairs an open-work ledger with the latest completed filing, the analysis-route folio gives reports a quieter reading field, and the pipeline and history index behave as ruled ledgers rather than repeated cards. Familiar inputs, buttons, links, tabs, tables, and status labels remain unmistakable inside that language.

**Key Characteristics:**

- Cool archival surfaces with charcoal, moss, and restrained amber.
- Square folios, fine rules, indexed tabs, stamps, and graphite annotations.
- Flat-at-rest hierarchy with one brief assembly lift when evidence arrives.
- Explicit state words, marks, and structure that never rely on color alone.
- Compact institutional typography built from the system sans-serif stack.

## Colors

The palette is cool and archival: neutral stock carries most of the interface, charcoal establishes the reading hierarchy, moss identifies durable actions and completed work, and amber is reserved for attention states.

### Primary

- **Institutional Moss**: Primary actions, links, folio labels, completed/open stamps, filed markers, and selected rules.
- **Deep Moss**: Hover state for the primary action, preserving the same institutional character with stronger contrast.

### Secondary

- **Docket Amber**: Queued and reconnecting states, HOLD and REVIEW signals, and text selection; its rarity makes attention meaningful.
- **Focus Ochre**: The dedicated keyboard focus outline, kept distinct from both completion and warning semantics.

### Tertiary

- **Failure Red**: Failed states and SELL or UNDERWEIGHT outcomes.
- **Error Ink, Error Paper, and Error Line**: A coordinated inline error treatment with readable text, tinted ground, and explicit boundary.

### Neutral

- **Cool Paper**: The application canvas.
- **Deep Paper**: A defined deeper archival neutral available within the current palette.
- **Charcoal Ink**: Primary text, navigation, headings, and strong rules.
- **Graphite**: Supporting copy, annotations, pending state text, and table labels.
- **Rule Line**: Dividers, ledger rows, stamps, and quiet container boundaries.
- **Field Line**: Stronger default input and select borders.
- **Open Folio**: The report reading sheet and route-state surface.
- **Field Stock**: Inputs, selects, connection stamps, and status stamps.
- **Filed Tab**: The selected report index tab and inline code/preformatted grounds.
- **Skeleton Grey**: Loading bars.
- **White**: Primary-button text and selected text.

### Named Rules

**The Ink-and-Moss Rule.** Charcoal carries information; moss marks action, access, or settled evidence. Amber and red remain semantic exceptions, never ambient decoration.

**The State-Plus-Signal Rule.** Every status color is paired with a word, border, dot, or positional state so completion, waiting, reconnecting, failure, and trade signals remain understandable without color.

## Typography

**Display Font:** `ui-sans-serif, system-ui, sans-serif`
**Body Font:** `ui-sans-serif, system-ui, sans-serif`
**Label/Mono Font:** No separate label or monospace family is used.

**Character:** One system sans-serif family keeps the research office direct and operational. Hierarchy comes from disciplined weight, scale, tracking, case, and compact annotation rather than ornamental type pairing.

### Hierarchy

- **Display** (700, 1.65rem, 1.1): Cover-sheet, analysis-record, and page titles; analysis and history titles reduce to 1.45rem on compact screens.
- **Headline** (700, 1.1rem, 1.45): Pipeline, evidence-file, and history-band headings.
- **Report headings** (browser bold, 1.5rem / 1.25rem / 1.05rem, 1.15): GFM levels one through three inside the evidence sheet.
- **Body** (400, 1rem, 1.45): Primary reading copy and rendered reports; reports stop at 75ch.
- **Compact body** (400, 0.9rem, 1.45): Introductory and supporting copy.
- **Label** (750, 0.79rem, 0.025em): Form labels and field legends.
- **Folio** (800, 0.7rem, 0.12em, uppercase): Document-role kickers such as “Open evidence file” and “Docket index.”
- **Status** (800, 0.72rem, 0.06em, uppercase): Connection and run stamps; tab sub-states reduce to 0.59rem.

### Named Rules

**The Indexed Voice Rule.** Uppercase, tracked type is reserved for folios, stamps, navigation, table headers, and state annotations; prose and report content remain sentence case.

## Layout

The application shell is centered at a maximum width of 1500px with 28px horizontal gutters and a 57px ruled navigation rail. Analysis and full-history routes use a narrower 1140px reading width. Spacing is compact and regular: neighboring controls generally use 9–16px gaps, document sections use 17–25px internal padding, and the major dashboard split uses a 22px gutter.

The dashboard alone uses the surface-specific four/eight composition: `minmax(300px, 4fr)` for the cover sheet beside `minmax(520px, 8fr)` for the docket desk. The desk stacks an open-sided active-work ledger over the latest completed filing; detailed agent progress and report tabs remain exclusive to an individual dossier. This composition is not a required grid for future screens. The history index spans beneath it as a ledger band.

At 800px and below, the work surface and filter grids become one ordered column, shell gutters reduce to 14px, the rail compresses to 51px, secondary rail notes disappear, and the pipeline becomes two columns. The ledger table becomes stacked label/value rows and report tabs wrap while retaining a 44px minimum touch height. At 430px and below, the pipeline becomes one column. Navigation links also retain a 44px minimum touch height on compact screens.

Keyboard focus is always visible as a 3px Focus Ochre outline with a 3px offset. The document may overflow only where its content requires it: activity is vertically capped and scrollable, report tables and preformatted blocks scroll horizontally, and long report content may wrap anywhere rather than break the viewport.

## Elevation & Depth

The system is flat at rest. The cover sheet and open folio are differentiated by borders, stock color, and moss top rules; pipeline and history ledgers remove left and right borders and sit directly on the paper. There are no resting surface shadows in the finished hierarchy.

### Shadow Vocabulary

- **Assembly lift** (`0 12px 22px rgba(29, 37, 43, 0.18)`): Appears only at the start of a newly filed report’s 180ms settling motion, then resolves to no shadow.

### Named Rules

**The Flat-at-Rest Rule.** Depth is structural, not decorative: use stock, rules, and document role at rest, and reserve shadow for the brief arrival of new evidence.

## Shapes

The form language is square and precise. Buttons, inputs, and selects use a restrained 2px corner radius; stamps, badges, tabs, folios, and document surfaces remain square. One-pixel rules organize most boundaries, while cover sheets and evidence folios receive a 2px moss top rule. Circular geometry is limited to 5–7px status and filed markers, where the dot represents a discrete state rather than decoration.

## Components

### Buttons

Buttons are compact, authoritative docket actions.

- **Shape:** Gently eased square control (2px radius), at least 42px high by default, with 9px × 14px padding.
- **Primary:** Institutional Moss ground with white, 800-weight text and a matching moss border.
- **Hover / Focus / Active:** Hover deepens to Deep Moss and lifts 1px over 180ms ease; active returns to rest. The shared 3px offset focus outline remains intact.
- **Ledger action:** Pagination reuses the button structure at a compact 31px minimum height with a transparent ground and Rule Line border.
- **Disabled:** 0.6 opacity and a not-allowed cursor, while the label continues to explain the unavailable action.

### Chips

Stamps and badges are explicit, outlined state labels.

- **Style:** Square, uppercase or compact bold text with a 1px semantic border; status stamps use 4px × 8px padding and signal badges use 2px × 6px.
- **State:** Open/completed and BUY/OVERWEIGHT use moss; queued/reconnecting and HOLD/REVIEW use amber; failed and SELL/UNDERWEIGHT use red. Each includes visible text and does not communicate by fill alone.

### Cards / Containers

Containers read as different document types, not interchangeable cards.

- **Cover sheet:** Cool translucent stock with a Rule Line border, 2px moss top rule, and 17–25px internal padding depending on viewport.
- **Open folio:** Open Folio stock with a Rule Line border, 2px moss top rule, 17–22px internal padding, and a report sheet constrained to 75ch.
- **Ruled ledgers:** Pipeline and history sections are transparent, flat, and open-sided; horizontal rules supply structure.
- **Route state:** A centered Open Folio panel with a Rule Line border and 30px padding for loading or unavailable routes.

### Inputs / Fields

Fields are familiar native controls set into archival stock.

- **Style:** Field Stock background, Charcoal Ink text, 1px Field Line border, 2px radius, 7px × 9px padding, and at least 40px height; the desktop cover sheet compacts them to 37px.
- **Hover / Focus:** Hover changes the border to Institutional Moss. Keyboard focus uses the shared Focus Ochre outline outside the control.
- **Error / Disabled:** Inline validation uses the coordinated error palette and `role="alert"`; disabled fields use 0.6 opacity and a not-allowed cursor.
- **Checkbox:** Native 17px square control with Institutional Moss accent, aligned with a bold analyst name and Graphite description.

### Navigation

The docket rail is a slim, uppercase index with Charcoal Ink links, simple line icons, a muted office descriptor, and a bottom rule. Links stay unboxed, gain their interaction affordance from weight and the shared focus outline, and preserve 44px touch height at 800px and below. The secondary wordmark and local-workspace note disappear when space is constrained, while New docket and Index remain visible.

### Report Tabs and GFM Sheet

Report tabs form a wrapping index above the evidence sheet. The active tab receives Filed Tab stock and a moss top rule; every completed report shows “Filed” plus a moss dot, while incomplete reports show “Awaiting.” The GFM sheet supports heading levels, lists, blockquotes with a moss rule, inline code and preformatted blocks on Filed Tab stock, ruled tables with horizontal overflow, dividers, external links opened with `noopener`, and aggressive wrapping for long generated content.

### Docket Assembly

Docket Assembly makes streamed completion tangible without obscuring the familiar report tabs. When a report first arrives, its tab changes from “Awaiting” to “Filed,” gains the filed dot, becomes selected, and its sheet settles from -8px with the temporary Assembly lift to its flat position in 180ms using `cubic-bezier(0.2, 0.9, 0.25, 1)`. If the final memorandum arrives in the same update, it takes selection priority. Under reduced-motion preference, animation and transitions collapse to 0.01ms so the same state change is immediate.

### Agent Record and Ledger

The agent record groups roles by team, gives each agent a named state, and pairs that word with a hollow or semantic 7px dot. Pending is hollow Graphite, in progress is filled Amber, completed is filled Moss, and error is filled Failure Red. While any agent in a team is in progress, that team shows an “Awaiting model” state with a small three-dot wave; it exists to communicate LLM latency, uses only transform and opacity, and becomes a steady mark under reduced motion. The activity ledger pins each event to its source and optional stage/time, caps the visible history at 11rem, and preserves polite live-region semantics. The history ledger uses sortable uppercase headers on wide screens and explicit label/value rows on compact screens.

### Dashboard Docket Desk

The dashboard never simulates an analysis. Active Dockets polls persisted running and queued work, orders running records before queued records, and links each row directly to its live dossier. Latest Filing presents the newest completed ticker, signal, filing time, analysis date, and a short final-memorandum excerpt with access to the full dossier. Both panels use explicit loading, error, and truthful empty states. Running marks pulse as state indication; pointer hover nudges linked rows and arrows by no more than 3px over 160ms with the shared strong ease-out, while press feedback scales to 0.97. Hover movement is limited to fine pointers and all positional motion is removed under reduced motion.

## Do's and Don'ts

### Do:

- **Do** differentiate cover sheets, open folios, and ruled ledgers through stock and border hierarchy rather than repeating one card treatment.
- **Do** keep status words, marks, and semantic borders visible alongside color.
- **Do** preserve 44px navigation and report-tab targets on compact screens and the shared 3px offset keyboard focus outline.
- **Do** keep generated report text readable at no more than 75ch, with safe wrapping and local overflow for GFM tables and code.
- **Do** use Docket Assembly only when a report newly becomes available, with immediate state change under reduced motion.

### Don't:

- **Don't** turn the surface-specific four/eight dashboard composition into a global layout mandate.
- **Don't** add generic floating cards or resting drop shadows to document surfaces.
- **Don't** spend amber or red as ambient decoration; they carry queued/reconnecting and failure/signal semantics.
- **Don't** hide standard report tabs behind a bespoke visualization or communicate progress through animation alone.
- **Don't** invent financial claims, performance decoration, or terminal-like market spectacle inside the research record.
