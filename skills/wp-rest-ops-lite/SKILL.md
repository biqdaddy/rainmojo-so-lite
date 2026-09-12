---
name: wp-rest-ops-lite
description: >
  WordPress REST API operations reference auth patterns, Cloudflare WAF
  workaround, rate limiting, Yoast canonical meta field, Redirection plugin API,
  batch vs single fetch bug. Use when executing any WP REST API bulk operation.
allowed-tools:
  - Read
  - Bash
  - Write
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


# WordPress REST API Operations

Reference skill for all WP REST bulk operations. See `references/powershell-scripts.md` for ready-to-run scripts.

For new content packages, media uploads, featured images, inline image binding,
and verified draft creation, use `wp-content-publisher-lite`. This skill remains the
low-level remediation reference.

## Authentication

### Standard (no WAF)
```python
from base64 import b64encode
token = b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
```

### Standard REST route fallback

Authenticated clients should first try `/wp-json/wp/v2/*`. When that route
returns an explicit WAF 403, retry the same request through WordPress's standard
`/?rest_route=/wp/v2/*` route and lock the session to the successful route.

Never retry a timed-out or otherwise ambiguous write.

### Legacy Cloudflare query-token workaround

Use only when both standard WordPress REST routes are unavailable and the site
owner explicitly approves a temporary query-token workaround. Prefer WAF rules,
Application Passwords, and `rest_route`; query tokens can leak through logs and
must be removed after the operation.

```php
add_filter('determine_current_user', function($user) {
    if (!empty($_GET['t']) && $_GET['t'] === 'YOUR_TOKEN') {
        $u = get_user_by('login', 'your-wp-username');
        if ($u) return $u->ID;
    }
    return $user;
}, 20);
add_filter('rest_authentication_errors', function($errors) {
    if (!empty($_GET['t']) && $_GET['t'] === 'YOUR_TOKEN') { return null; }
    return $errors;
}, 20);
```
Append `?t=YOUR_TOKEN` to every REST URL. **Deactivate snippet after all phases complete.**

## Rate limiting
- `time.sleep(25)` between every POST mandatory even with CF Skip rules
- Batches 50+: use background subprocess to avoid 300s MCP timeout

## Key endpoints

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Auth test | `/wp-json/wp/v2/users/me` | GET |
| All posts | `/wp-json/wp/v2/posts?per_page=100&page=N&status=any&context=edit` | GET |
| All pages | `/wp-json/wp/v2/pages?per_page=100&page=N&status=any&context=edit` | GET |
| Single post | `/wp-json/wp/v2/posts/{id}?context=edit` | GET |
| Update | `/wp-json/wp/v2/posts/{id}` | POST |
| Yoast canonical | POST with `{"meta":{"yoast_wpseo_canonical":"URL"}}` | POST |
| Redirection plugin | `/wp-json/redirection/v1/redirect` | POST |

## CRITICAL: batch fetch bug
**Never** read `content.raw` from a batch list endpoint it concatenates content across posts.
Always fetch individually: `GET /posts/{id}?context=edit`

## Elementor constraint
Elementor pages have empty `content.raw` via REST. Flag as `MANUAL` edit via WP Admin only.

## Error codes

| Code | Cause | Fix |
|------|-------|-----|
| 401 | Auth failed | Check Application Password; enable WPCode snippet |
| 403 | Cloudflare WAF | Retry through `/?rest_route=` first (see Authentication); legacy query-token snippet only with the site owner's explicit approval |
| 404 | Wrong post type | Check backup CSV for type (post vs page) |
| 429 | Rate limit | Increase sleep to 30s |
| 522 | CF timeout | Retry once after 60s |
| 400 | Bad JSON | Add `-Depth 2 -Compress` to ConvertTo-Json |
