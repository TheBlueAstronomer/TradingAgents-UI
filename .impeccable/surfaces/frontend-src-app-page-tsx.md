---
version: 1
slug: "frontend-src-app-page-tsx"
primary_target: "frontend/src/app/page.tsx"
related_targets: ["frontend/src/app/analysis/[id]/page.tsx","frontend/src/app/history/page.tsx"]
---

# Dashboard and analysis workspace

Mode: Operate

Scope: `frontend/src/app/page.tsx`, with the live analysis and history routes as related surfaces.

Audience and job: Existing TradingAgents users configure an analysis, follow a long-running agent workflow, read the resulting evidence and decision, and retrieve earlier runs. The recurring action is starting a run; queued, running, completed, failed, reconnecting, loading, and empty states must remain unmistakable. TradingAgents upstream code and credentials remain outside the interface.

## Direction contract

THESIS: A TradingAgents run is a research docket assembled in public, from selected analyst exhibits to one signed decision. It refuses the generic SaaS card dashboard and the dark trading-terminal cliché.

OWN-WORLD: Cool archival stock, charcoal ink, deep institutional moss, and restrained docket amber. Square folios, ruled sections, indexed tabs, stamps, and graphite annotations form one consistent control language; familiar inputs and buttons remain unmistakable.

STORY: Complete the cover sheet, open the run immediately, watch each evidence tab become available inside its dossier, read the final memorandum, then return to the dashboard to resume active work or scan the latest filing.

FIRST VIEWPORT: A slim docket rail spans the top. A four-column cover sheet holds ticker, date, team, provider, models, depth, and the primary Start analysis action. An eight-column docket desk shows real queued/running analyses and the latest completed filing; it never displays illustrative progress or reports. Recent dockets form a compact indexed band below, all visible on a 1440px desktop. On mobile, these become one ordered column. In an individual dossier, the active team carries a restrained “Awaiting model” state cue and Docket Assembly files each completed report into its tab; reduced motion keeps these changes legible without positional movement.

FORM: Research Docket, the first and highest-resonance grounded direction, selected as Impeccable’s pick from direction seed `38da0d95`.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Memorable moment: The dashboard remains an honest operations desk while each live dossier shows the model handoff and evidence stack resolving into the final memorandum.

Unresolved decisions: None.
