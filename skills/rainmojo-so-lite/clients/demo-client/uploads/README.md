# Uploads - raw data from external tools (read-only)

Drop each tool's export into its matching subfolder. Agents auto-detect files here and never
modify them. Each folder maps to a metric family the report fills. The table below is that mapping:
drop a file in the wrong folder and its metrics stay empty.

| Folder | Tool / source | Drop these exports | Fills token families |
|---|---|---|---|
| `google-search-console/` | Google Search Console | Performance CSV, Coverage / Indexing, Sitemaps, current DisavowLinks TXT | `GSC_*`, `PAGES_INDEXED/NOT_INDEXED`, `IDX_*`, disavow baseline |
| `google-analytics/` | Google Analytics 4 | Acquisition / Traffic, Landing pages, Conversions (CSV) | `GA4_*`, `ANALYTICS*`, `ORGANIC_TRAFFIC` |
| `ahrefs/` | Ahrefs (or Semrush) | Site Explorer overview, Backlinks with referring page URL/title/spam flag, Organic keywords, DR (CSV / xlsx) | `DR`, `UR`, `BACKLINKS`, `REF_DOMAINS`, `ORGANIC_KEYWORDS`, `TOXIC_*`, disavow review, `KW_VOLUME/DIFFICULTY` |
| `screaming-frog/` | Screaming Frog SEO Spider | internal_all / page_titles / meta-description / h1 / images / response_codes (CSV) | `META_*`, `BRK_*`, `IMG_*`, `INT_*`, `*INLINKS`, `HEAD_*`, `SCHEMA_PRESENT*` |
| `pagespeed-insights/` | PageSpeed Insights / CrUX / Lighthouse | JSON, or a screenshot of Core Web Vitals (mobile + desktop) | `LCP/CLS/INP/FCP/TBT/TTFB*`, `PERF_*`, `PAGE_SIZE`, `CWV_*` |
| `google-business-profile/` | Google Business Profile | per-branch listing export, reviews, insights | `GBP_*`, `BING_PLACES*` |
| `brand-assets/` | Client-provided brand | logo, favicon, brand guide, exact colour values | brand logo / favicon / colour overrides |
| `other/` | Anything else | competitor reports, content drafts, manual research notes | `COMPETITOR*`, `AUDIENCE_*`, misc |

Naming: keep the tool's original export filename, or prefix with the export date `YYYY-MM-DD_`.
CSV / XLSX / JSON / PDF / PNG are all fine.

The remaining report content (exec summary, AISO analysis, schema map, keyword/content plan,
roadmap) is PROSE written by the audit skills - it is NOT uploaded. See the contract's
"amber ph-missing" list for which tokens are written vs sourced from a tool here.
