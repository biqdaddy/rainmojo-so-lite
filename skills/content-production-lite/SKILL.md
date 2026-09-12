---
name: content-production-lite
description: >
  Run the client-configured SEO content factory from validated article planning
  through content QA, image production, internal and external linking, and a
  verified WordPress draft. Supports the shared generic engine and declared
  client-native adapters.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
  - Skill
---
<!-- RAINMOJO_CLIENT_WORKSPACE_ROUTING_V1 -->
## Client workspace routing (mandatory for file changes)

Every generated file has exactly one home. Audit, keyword and comparison
outputs live under `work/{domain}/` created by `new-workspace-lite`
(`00-baseline/` first run, `01-current/` later runs, `02-fixes/`, `03-content/`,
`04-reports/`, `uploads/` read-only for user files); never invent another
top-level folder there. Content production and WordPress publishing use the
client workspace `clients/<client>/` created by `new-client-lite`: read
`workspace-routing.json` first, resolve every artifact with
`{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/client_workspace.py route`, use the
most precise registered route, edit root files only when their exact filename is
in `root_policy.allowed_files`, treat `uploads/` as read-only, and when no route
fits use `create-work` then `route-work`; never construct a `work/<name>/...`
path by hand inside a client workspace. Never write generated files to the
plugin tree or the caller's working directory. Append one line to the
workspace's `CHANGELOG.md` or `log.md` after every write. Run
`client_workspace.py validate` before handing a client workspace over. Direct
CMS/API operations retain their own safety and verification gates.

<!-- RAINMOJO_PRESENTATION_LAYER_V1 -->
## Presentation (Two-Tier, 7 modes)

Answer in the response mode that matches the request
(`{PLUGIN_ROOT}/skills/rainmojo-so-lite/_base/presentation-scaffold.md`): quick fact,
how-to, comparison, troubleshoot, audit, deployable, always closing with next
steps. A run that writes a deliverable ends with a Tier 1 card built from
`summary.json` (`templates/widget/summary.schema.json`) and rendered with
`{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --target auto`, then hands
off to the Tier 2 file, which stays complete and unchanged. Lite cards carry
counts of checks passed, never a weighted score. Every card value is copied
from the deliverable; unmeasured values show as could not verify. No emoji on
any surface; the glyph allowlist applies to chat and Markdown only.


# Content Production

Use this as the callable entry point for a complete article-production workflow.
Read [agent.json](agent.json), then:

- `{PLUGIN_ROOT}/skills/rainmojo-so-lite/_base/skill-scaffold.md`
- `{PLUGIN_ROOT}/skills/rainmojo-so-lite/reference/content-production/contract.md`
- `{PLUGIN_ROOT}/skills/rainmojo-so-lite/reference/content-production/content-review.example.json`
- `clients/<domain>/CLAUDE.md`
- `clients/<domain>/brand-guidelines.md`
- `clients/<domain>/client-profile.md`
- `clients/<domain>/site-config.md`
- `clients/<domain>/content-pipeline.json`
- `clients/<domain>/workspace-routing.json`

Resolve `{PLUGIN_ROOT}` to the real installed plugin root before invoking any
plugin script.

## Start

```bash
python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/client_workspace.py" validate \
  --client ./clients/<domain>

python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/content_pipeline.py" config-check \
  --client ./clients/<domain> \
  --require-capability end_to_end
```

This command intentionally rejects `image_only` and `partial` clients. Use the
image-production entry point for a declared image-only adapter.

After configuration passes, use the `content-production-orchestrator-lite` agent.
The orchestrator must dispatch according to `engine.mode`:

- `generic`: shared article packages under `content/production/<slug>/`
- `client_native`: only the capability-backed adapter operations declared in
  the client config; never generic package or publisher paths

## Review guidance for model-drafted sections (decision layer)

This section is judgement inside the review record that `content_qa_passed` already requires.
It adds no pipeline state, no ledger column and no new gate; where it appears to disagree with the
safeguards above, the safeguards win. Full procedure and record shapes:
`{PLUGIN_ROOT}/skills/rainmojo-so-lite/reference/frameworks/content-production-model-draft-gates.json`

- **Two-pass verification on every model-drafted section.** Pass 1 walks every factual claim and marks
  it verified (source named), wrong, or could not verify. Pass 2 writes what a subject-matter expert would
  insist the piece must contain, before rereading, then lists what is absent. Pass 2 outranks pass 1:
  a draft that states nothing false while omitting half the brief does not pass. A named human signs off
  on both passes with a date; a role title or a model-generated approval is not a sign-off.
- **Topic blocklist: a generative model is never the source of record** for current product pricing,
  directions and routing, weather and other real-time data, live scores, YMYL topics, and news. A block in
  these classes fails the gate no matter how confident the draft reads; it clears only when the values are
  replaced by feed-supplied or human-supplied values and the record says which.
- **Record which engine produced each draft** beside the class check. If the engine cannot be established,
  write could not verify; never assume the currently configured engine produced an older draft.
- **Outbound link qualification.** Assign rel by reason, never as a blanket default: advertising or any
  compensated placement gets `sponsored` (or `nofollow`); anything inside a user-generated area gets `ugc`
  (or `nofollow`); a link the page must carry but does not endorse gets `nofollow`; an editorially chosen,
  trustworthy, topically related source gets no rel, because the endorsement is intended. Record target URL,
  reason class, rel assigned and topical-relation verdict for every outbound link.

Boundaries: off-site link acquisition belongs to `seo-backlink-strategy-lite`; E-E-A-T scoring stays with
`seo-content-audit-lite`; the drafting-side method for running the two passes belongs to `seo-content-creation-lite`.

## Required safeguards

- Missing client configuration fails closed.
- Production placeholder domains and visual-style modes fail validation.
- `content_qa_passed` requires a structured reviewer/checklist record bound to
  the current `article.md` SHA-256.
- Editing the article after review invalidates later gates.
- Article state transitions are validated and auditable.
- Required product, pillar, related-content, and external-source links are
  checked against the article plan.
- Image generation and content drafting may run in parallel.
- WordPress media and post writes use one serial worker per client.
- Draft-only is mandatory.
- A non-draft slug is rejected before the first media write.
- Verification failures use verify-only recovery.
- Public publication requires a separate capability and explicit instruction.
- Generic package state is confined to `content/production/<slug>/`. The
  aggregate dashboard is regenerated from package state and publish evidence;
  it is never edited as a second state store.
- At batch checkpoints and before handoff, run `content_pipeline.py batch-report
  --client ./clients/<domain>`. Current JSON and HTML go to
  `content/dashboards/`; immutable run-scoped status, publishing, and batch
  manifest files go to `content/reports/status/<date>/` and
  `content/reports/publishing/<date>/`. The current dashboards are the only
  mutable aggregate views.

## Host image capability

If the host exposes an image-generation capability, use it to create the approved
raw asset from the manifest prompt. If it does not, stop after the brief/source
intake stage and report that a raw source asset is required. Never claim that the
image-production script itself generated an image.
