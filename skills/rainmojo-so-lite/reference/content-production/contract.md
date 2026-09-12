# Content Production Contract

This contract is client-neutral. Every production client must provide a
root-level `content-pipeline.json` that validates against
`content-pipeline.schema.json`. Missing production configuration fails closed.
Plugin-only defaults are available solely through an explicit `demo` or `test`
profile.

## Configuration and precedence

Package initialization resolves configuration in this order:

1. Plugin `defaults.json`
2. Client `content-pipeline.json`
3. Article `config_overrides`

Steps 1 and 2 are frozen into the package `resolved-config.json`. Its canonical
SHA-256 is recorded in `article.json`; later client-default changes do not alter
an existing package. Article overrides are applied last at read time, but may not
change `config_policy`, `engine`, or `site`. Every effective configuration is
validated again, including the draft-only publishing guard.

Each production package contains:

```text
content/production/<slug>/
  article.json
  article.md
  image-manifest.json
  sources.json
  resolved-config.json
  images/raw/
  images/optimized/
  reports/
```

## Engine modes and native adapters

`engine.mode` is either `generic` or `client_native`.

For `generic`, `engine.source_of_truth` must be exactly
`content/production`. Client-native adapters may declare a different
client-confined source file, but generic state may not be redirected to a
reports or dashboard folder.

Every engine declares `engine.capabilities` with exactly these keys:

```text
scope
content
images
wordpress_draft
content_review
image_source_review
image_visual_review
verify_only
draft_only
```

`scope` is `end_to_end`, `image_only`, or `partial`. `end_to_end` is derived
from every production boolean being true; there is no separate `end_to_end`
boolean. `image_only` requires `images`, `image_source_review`, and
`image_visual_review`, while content and WordPress capabilities remain false.
`draft_only` is always true, including image-only pipelines, as a global safety
invariant. Production `client_native` files must explicitly declare every
capability key rather than inheriting them silently from plugin defaults.

Entry points fail closed against these declarations:

```bash
content_pipeline.py config-check --require-capability end_to_end
content_pipeline.py config-check --require-capability images
content_pipeline.py config-check --require-capability wordpress_draft
```

`client_native` keeps the client's existing pipeline as the source of truth.
Logical operations are declared under `engine.adapter.operations`; argv arrays
are preferred, while command strings are parsed without a shell. Commands may
contain simple placeholders such as `{number}`, `{slug}`, or `{review_file}`.
`adapter-plan` and `adapter-run` receive their values as repeated
`--param name=value` arguments. `{client}` and `{client_root}` are supplied
automatically.

Native dispatch is fail closed:

- the executable must exactly match `adapter.allowed_commands`
- Python adapters must name a `.py` file inside the client root
- `python -c`, `python -m`, shell metacharacters, path traversal, and unresolved
  placeholders are rejected
- execution always uses `shell=False` and `cwd=<client-root>`
- every path-like argument must remain within the client root

All native adapters require `prepare`, `status`, and `self_test`. Other
operations are capability-derived:

- content: `init_article`, `approve_outline`, `validate_content`
- content review: `review_content`
- images: `image_spec`, `optimize_images`
- image source review: `review_image_sources`
- image visual review: `review_images`
- WordPress draft: `validate_publish`, `preflight`, `publish_draft`
- verify-only recovery: `verify_only`

An end-to-end adapter therefore includes every operation above. An image-only
adapter exposes only the base and image operations; it cannot be dispatched by
the end-to-end content-production-lite entry point.

`approve_outline` is a callable gate, not permission to self-approve. The
orchestrator must stop until the current native outline receives explicit
review approval, record concise approval notes through the adapter, and confirm
the resulting native status before content validation.
Generic initialization and batch commands refuse `client_native` clients so a
second, divergent package tree cannot be created accidentally.

## States and invalidation

Standard states advance one gate at a time:

```text
planned
outline_ready
research_ready
draft_ready
content_qa_passed
image_specs_ready
images_technical_ready
images_qa_passed
publish_ready
draft_uploaded
verified
```

Normal `set-status` rejects skips and backward movement. A reprocessed or changed
artifact must call `invalidate-status` or `invalidate_status(...)` with a
non-empty reason. Successful publish-stage validation may advance
`images_qa_passed` to `publish_ready`, which removes the former validation
deadlock while retaining the gate.

`content_qa_passed` is not a manually assertable label. Before that transition,
the package must contain `reports/content-review.json` with:

- a non-empty reviewer
- the SHA-256 of the current `article.md`
- every configured `quality_gates.content_review_checklist` item set to
  `passed`

Create the structured evidence file, then record it through:

```bash
content_pipeline.py review-content --client <client> --slug <slug> \
  --review-file reports/content-review-input.json
```

Use `content-review.example.json` as the neutral starter and replace its reviewer
and SHA-256 placeholders before recording it.

The input file is confined to the article package. Any later `article.md` edit
changes its SHA-256, invalidates the review evidence, fails validation, and
blocks later state transitions until the package is moved back to `draft_ready`
and reviewed again.

## Links and evidence

`article.links` is a load-bearing plan, not a note. Required product, pillar, and
related target lists must be non-empty for the article type, and every declared
URL must occur in `article.md`. Root-relative and other relative internal URLs
are resolved against the configured site base and count as internal links.
Markdown images do not count as links.

Every external content URL must:

- appear in `article.links.external_sources`
- have a matching `sources.json` external record
- include the configured provenance fields, neutral defaults require `url`,
  `claim`, and `accessed_at`
- pass the same allowlist and blocklist policy as the article link

Validation is deterministic and performs no live network checks. Connectivity
or HTTP-status evidence belongs in a separate explicit preflight report.

## Images and publishing

Image metadata fields remain distinct:

- `alt`: visible content and purpose without keyword stuffing
- `title`: concise WordPress media-library title
- `caption`: optional editorial caption, never copied from alt automatically
- `credit`: optional visible credit
- `provenance`: internal source/provider/license/generation notes stored in JSON

Before generic processing, each raw source requires a structured approval bound
to:

- exact relative source path, SHA-256, byte count, dimensions, and format
- reviewer identity and every configured
  `quality_gates.image_source_review_checklist` item
- a provenance snapshot containing source type, provider, source URL, rights
  record, license record, and generation notes
- the canonical SHA-256 of that provenance snapshot

Start from `image-source-review.example.json` and record each item with:

```bash
image_production.py review-source --client <client> --slug <slug> \
  --image-id <id> --review-file reports/<id>-source-review-input.json
```

`process` recalculates the raw identity and provenance hash. Changed bytes,
dimensions, path, format, source/provider, rights, license, or generation
evidence invalidate approval and stop processing.

Embedded file metadata and WordPress media fields are separate. Published files
are re-encoded and audited; WordPress alt/title/caption values are written through
the REST API and are not embedded in the image file.

Publishing is draft-only. A production skill must never publish publicly unless
a separate explicit user instruction and a separate public-publish capability
exist.

## Batch control plane and tracking reports

The generic control plane provides `batch-init`, `batch-status`,
`batch-report`, and `batch-validate`. Batch manifests must live inside the
client root. Batch validation remains read-only except for deterministic
validation reports.

`batch-report` reads every
`content/production/<slug>/article.json` and, when present, the matching
`reports/wordpress-publish.json`. It writes regenerated current JSON and HTML
to `content/dashboards/content-status.json` and `content-status.html`. Those two
files are mutable current views. Each run also writes immutable
`content/reports/status/<date>/content-status-<run-id>.json`,
`content/reports/status/<date>/batch-report-<run-id>-manifest.json`, and
`content/reports/publishing/<date>/publishing-status-<run-id>.json`. All
aggregate files are projections, not writable state. Correct an article package
or WordPress report and regenerate; never patch a dashboard or snapshot to
change production status.
