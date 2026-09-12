---
name: wp-content-publisher-lite
description: >
  Publish a validated article package to WordPress as a verified draft. Uploads
  media, writes alt/title/caption fields, assigns featured media, binds inline
  placeholders, writes SEO fields, handles explicit WAF 403 REST fallback,
  throttles writes, preserves idempotency, and fetches every result for verification.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
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


# WordPress Content Publisher

Use only after content and image QA have passed.

Read and execute [agent.json](agent.json). Also read:

- `../rainmojo-so-lite/_base/skill-scaffold.md`
- `../rainmojo-so-lite/reference/content-production/contract.md`
- `../wp-rest-ops-lite/SKILL.md`
- The target client's `site-config.md` and `content-pipeline.json`

## Capability and engine branch

```bash
python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/content_pipeline.py" config-check \
  --client ./clients/<domain> \
  --require-capability wordpress_draft
```

This must fail cleanly for image-only clients. Read `engine.mode` after it
passes.

### Generic engine

Run the shared publisher only for `engine.mode=generic`.

#### Preflight

```bash
python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/wordpress_publisher.py" preflight \
  --client ./clients/<domain>
```

Credentials must come from `clients/<domain>/.env`.

#### Dry run

```bash
python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/wordpress_publisher.py" publish-draft \
  --client ./clients/<domain> \
  --slug <slug> \
  --dry-run
```

#### Draft upload

```bash
python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/wordpress_publisher.py" publish-draft \
  --client ./clients/<domain> \
  --slug <slug>
```

#### Verify-only recovery

When a write completed but verification failed or timed out:

```bash
python "{PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/wordpress_publisher.py" verify-draft \
  --client ./clients/<domain> \
  --slug <slug>
```

### Client-native engine

Do not invoke `wordpress_publisher.py` or assume a generic article package.
Invoke only these declared adapter operations:

1. `preflight`
2. `publish_draft`
3. `verify_only`

Use `content_pipeline.py adapter-plan` before the first execution of each
operation, followed by `adapter-run`. `verify_only` is the only recovery action
after an ambiguous or incompletely observed write.

## Mandatory safety rules

- Validate the article package at publish stage before any network write.
- Check slug identity and reject a non-draft collision before the first media write.
- Write WordPress `alt_text`, media title, and caption separately.
- Assign exactly one featured image and replace every inline placeholder.
- Use slug-based idempotency. Reuse matching media and update an existing draft.
- Refuse to overwrite a non-draft post.
- Default and final status remain `draft`.
- Use one process-safe serial writer and wait for the configured interval between
  all client writes, including separate CLI invocations.
- A confirmed HTTP 403 may switch from `/wp-json/` to `rest_route`.
- Never retry a timed-out or otherwise ambiguous write.
- Fetch and compare the individual post and every media item after writes,
  including title, content, links, taxonomy, caption, credit, dimensions, and SEO fields.
- Report verification failures instead of claiming success.

## Output

`content/production/<slug>/reports/wordpress-publish.json`

After a generic publish or verify operation, regenerate client-level tracking
with `content_pipeline.py batch-report --client ./clients/<domain>`. This writes
mutable current JSON and HTML views to `content/dashboards/` and immutable
run-scoped status, publishing, and batch-manifest evidence below
`content/reports/`. Never edit any aggregate file as publishing state.
