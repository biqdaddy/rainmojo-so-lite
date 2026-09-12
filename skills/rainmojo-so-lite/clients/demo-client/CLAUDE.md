# Client Workspace Routing Contract

This file tells every AI agent where client files belong. workspace-routing.json
is the machine-readable source of truth. Read both files before creating,
modifying, moving, or deleting any client artifact.

**Mandatory rule:** never write a generated deliverable to the client root or
caller's working directory. Maintained identity/configuration files may be
created or edited only under exact `root_policy.allowed_files` names. Resolve
the most precise registered route first.

## Required routing workflow

1. Load brand-guidelines.md, client-profile.md, site-config.md,
   content-pipeline.json, and workspace-routing.json.
2. Resolve the output type before writing:

       python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/client_workspace.py" route \
         --client ./clients/{domain} --type {output-type} --filename {filename}

3. Write only to the returned target. Treat uploads/ as read-only user input.
4. After a structural change, run client_workspace.py validate.
5. If no registered route reasonably fits, use create-work. It creates and
   registers work/{lowercase-kebab}/. Resolve every later artifact with
   route-work and write only to its returned target. Never create an ad hoc
   client-root folder or construct a work path directly.
6. Reject any path that crosses a symlink, junction, reparse point, or the client
   root boundary.

## Precise folder routing

| Output type | Folder | Filename pattern |
|---|---|---|
| General assessment, legal, or client-facing report without a more precise route | reports/ | {domain}_{type}_{YYYY-MM-DD}.{ext} |
| Unified-report inputs and working JSON | reports/data/ | client.json, audit-base.json, audit.json |
| SEO, AISO, technical, or combined search audit report | reports/seo-audits/ | {domain}_{type}_{YYYY-MM-DD}.{ext} |
| General optimization or technical recommendation | optimization/ | {domain}_{type}_{YYYY-MM-DD}.{ext} |
| Image optimization outputs and naming ledger outside an article package | optimization/images/ | {domain}_{type}_{YYYY-MM-DD}.{ext} |
| Off-page strategy or authority-development report | optimization/off-page/ | {domain}_off-page-strategy_{YYYY-MM-DD}.{ext} |
| On-page audit, plan, or implementation report | optimization/on-page/ | {domain}_on-page_{YYYY-MM-DD}.{ext} |
| Keyword research, cluster, or topical map | keywords/ | {domain}_{type}_{YYYY-MM-DD}.{ext} |
| Compiled keyword-pipeline report | keywords/reports/ | {domain}_keyword-report_{YYYY-MM-DD}.{ext} |
| Standalone article or outline outside a production package | content/drafts/ | {slug}.{ext} |
| Content plan, calendar, roadmap, topic cluster, or batch manifest | content/planning/ | {domain}_{type}_{YYYY-MM-DD}.{ext} |
| Stateful article package | content/production/{slug}/ | fixed package contract |
| Regenerated current content dashboard | content/dashboards/ | content-status.json and content-status.html |
| Immutable content status snapshot | content/reports/status/ | {YYYY-MM-DD}/content-status-{run-id}.json |
| Immutable batch-report manifest | content/reports/status/ | {YYYY-MM-DD}/batch-report-{run-id}-manifest.json |
| Immutable WordPress publishing snapshot | content/reports/publishing/ | {YYYY-MM-DD}/publishing-status-{run-id}.json |
| Per-article validation, image, or WordPress report | content/production/{slug}/reports/ | fixed package contract |
| Internal-link map or plan | internal-links/ | {domain}_link-map_{YYYY-MM-DD}.{ext} |
| Schema JSON-LD | schema/ | {page}_schema.json |
| General reviewed deployment artifact | deploy/ | exact filename |
| Disavow rules and review configuration | disavow/config/ | review-rules.json |
| Immutable disavow decision ledger | disavow/data/decision-ledgers/ | {client-slug}_disavow-decisions_{YYYY-MM-DD}_{run-id}.csv |
| Immutable disavow review report | disavow/reports/reviews/ | {client-slug}-disavow-review-{YYYY-MM-DD}-{run-id}.html |
| Regenerated current disavow dashboard | disavow/dashboards/ | disavow-review.html |
| Immutable Search Console candidate | disavow/exports/search-console/ | {client-slug}_{YYYYMMDD}_{run-id}_DisavowLinks.txt |
| Explicitly approved disavow deployment copy | deploy/disavow/ | {domain}_{YYYYMMDD}_DisavowLinks.txt |
| Disavow run manifest and evidence | disavow/runs/{run-id}/ | manifest.json |
| Wiki entity | wiki/entities/ | {entity-slug}.md |
| User-provided source or external-tool export | uploads/{tool}/ | read-only, preserve original filename |
| Genuinely novel work with no existing route | work/{registered-type}/ | defined in work/registry.json |

The two current dashboard files under `content/dashboards/` and the current
`disavow/dashboards/disavow-review.html` are the only mutable tracking views in
these workflows. Every dated/run-scoped snapshot, review, ledger, candidate,
and manifest is immutable. Managed disavow runs accept exactly one client and
one Search Console property per invocation. Optional report logo and favicon
files must be local read-only inputs below `uploads/brand-assets/`; remote URLs
and data URIs are forbidden.

Report generator working data is not a client-root configuration surface. Route
`client.json`, `audit-base.json`, and `audit.json` with `report-data` and keep them
under `reports/data/`; route the rendered client-facing report separately with
`client-report` or the more precise audit route.

## Upload protection

uploads/ is an intake boundary. Agents may read and cite files there but must
not rewrite, rename, normalize, move, or delete them. Derived data belongs in
the matching output route, never beside the source export.

## Novel work

Use an existing route whenever it reasonably fits. Otherwise run:

    python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/client_workspace.py" create-work \
      --client ./clients/{domain} \
      --name {lowercase-kebab} \
      --description "{why no existing route fits}" \
      --owner client-team \
      --artifact-class novel-work-output \
      --writable-subpath artifacts \
      --retention retain-until-explicit-closeout

The helper confines the folder to work/, creates its declared writable
subpaths, writes a registry entry, and appends the structural event to log.md.
Every entry records owner, artifact_classes, writable_subpaths,
source_of_truth, retention, and created_at. An explicit source of truth must be
an existing client-confined path; otherwise the work README is used. Write novel
artifacts only inside the declared writable subpaths. Do not manually add an
unregistered folder.

Then resolve each artifact before writing:

    python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/client_workspace.py" route-work \
      --client ./clients/{domain} \
      --name {lowercase-kebab} \
      --subpath artifacts \
      --filename {filename}

## Identity and maintained configuration

Only maintained identity and configuration files listed by root_policy may
exist at the client root. Generated deliverables are forbidden there.

## Wiki and timeline

- wiki/index.md catalogs client knowledge and sources ingested.
- wiki/entities/ stores one cross-linked page per durable entity.
- log.md is append-only. Record structural changes, audits, reports, and content
  production events.

## Closeout

Confirm every generated path, update wiki/log when applicable, then run:

    python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/client_workspace.py" validate \
      --client ./clients/{domain}
