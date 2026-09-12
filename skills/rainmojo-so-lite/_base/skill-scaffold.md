---
name: _base-skill-scaffold
kind: base-layer
---

# Shared Skill Scaffold

Shared scaffold. Every skill inherits these conventions. A skill's SKILL.md only
needs its unique workflow; these Brand Context, User Uploads, Output-naming, and
Reference rules apply to all.

This is the single canonical copy of the boilerplate that was previously duplicated
across each skill's SKILL.md. When migrating a skill, delete its local copies of the
sections below and rely on this scaffold instead. Each skill keeps only its own
unique workflow, its `# Title`, and any skill-specific scripts or rules.

---

## Brand Context (auto-load)

Before executing, check for client data at `./clients/{domain}/`:

1. Look for `./clients/{domain}/brand-guidelines.md`
2. Look for `./clients/{domain}/client-profile.md`
3. Look for `./clients/{domain}/site-config.md`
4. Look for `./clients/{domain}/content-pipeline.json`
5. If found, validate and apply brand voice, tone, site, production, image,
   adapter, and publishing context.
6. If not found, read-only analysis may continue with generic assumptions.
   Stateful content production, image mutation, and CMS writes must fail closed.

## Client Workspace Routing (mandatory before every write)

Before creating, editing, moving, or deleting a client artifact:

1. Read `./clients/{domain}/AGENTS.md` or `CLAUDE.md` and
   `workspace-routing.json`.
2. Resolve the most precise output route with
   `{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/client_workspace.py route`.
3. Write only to the returned client-confined path. Never write a generated
   file to the client root or the caller's working directory.
   Maintained identity/configuration files are the sole exception and may be
   created or edited only under an exact `root_policy.allowed_files` filename.
4. Treat `uploads/` as read-only user input. Derived files use an output route.
5. Reject symlinks, junctions, reparse points, absolute output paths, and path
   traversal.
6. If no registered route reasonably fits, use `create-work`. It creates only
   `work/<lowercase-kebab>/`, registers the folder in `work/registry.json`, and
   records owner, artifact classes, writable subpaths, source of truth,
   retention, description, and creation time. Resolve every novel artifact with
   `route-work` and write only to its returned target; never construct the work
   path directly. Record the event in `log.md`.
7. Run `client_workspace.py validate` after structural changes and before
   handoff.

## User Uploads (auto-detect)

Check `./clients/{domain}/uploads/` for user-provided files:

- .csv/.xlsx, keyword lists, analytics data
- .md/.txt, content drafts, competitor notes
- .html, existing markup for audit
- .json, schema markup, structured data

If files found, incorporate them into your analysis automatically.

## Output

### Naming convention

ไฟล์ที่สร้างต้องตั้งชื่อตาม pattern:

```
{domain}_{skillkey}_{YYYY-MM-DD}.{ext}
```

`{skillkey}` is the short slug for the skill (for example `technical-audit-lite`,
`meta-tags`, `report`, `link-map`). Use the key declared in each skill's own
SKILL.md.

ตัวอย่าง: `example.com_technical-audit_2026-03-28.md`

Resolve every generated file with `client_workspace.py route` and use the most
precise registered type below. The list describes resolver targets; never choose
or construct a destination path manually:

- `keywords/`, keyword research, clustering, trends
- `keywords/reports/`, compiled keyword-pipeline reports
- `content/drafts/`, standalone content drafts and outlines
- `content/planning/`, calendars, roadmaps, topic plans, and batch manifests
- `content/production/{slug}/`, stateful article packages and per-article reports
- `content/dashboards/`, regenerated mutable current content/publishing views only
- `content/reports/status/`, immutable run-scoped production status snapshots and batch manifests
- `content/reports/publishing/`, immutable run-scoped draft publishing snapshots
- `disavow/config/`, client-scoped disavow rules
- `disavow/data/decision-ledgers/`, immutable dated/run-scoped review decisions
- `disavow/reports/reviews/`, immutable dated/run-scoped backlink review evidence
- `disavow/dashboards/`, regenerated mutable current disavow view only
- `disavow/exports/search-console/`, immutable dated/run-scoped Search Console candidates
- `disavow/runs/`, run manifests and evidence
- `reports/`, general assessments and client deliverables
- `reports/data/`, unified-report inputs and working JSON only
- `reports/seo-audits/`, SEO, AISO, technical, and combined audits
- `schema/`, JSON-LD markup files
- `optimization/`, general meta tags and technical recommendations
- `optimization/images/`, image-optimization outputs and naming ledgers outside article packages
- `optimization/off-page/`, off-page strategies and reports
- `optimization/on-page/`, on-page audits, plans, and reports
- `internal-links/`, internal-link maps and plans
- `deploy/`, reviewed deployment artifacts
- `wiki/entities/`, durable client knowledge
- `work/<registered-type>/`, genuinely novel work only

Audit reports use the most precise registered report route. Unified-report
working data belongs only in `reports/data/`, never at the client root.

## Reference files

- Agent definition: `agent.json` (in the skill's own folder)
- Shared agent defaults: `_base/agent-common.json`
- For Google quality guidelines, see `reference/google/`
