---
name: _base-presentation-scaffold
kind: base-layer
version: 1.0
---

# Shared Presentation Scaffold (Two-Tier delivery, 7 response modes)

Every skill and agent inherits this layer the same way it inherits
`skill-scaffold.md`. A unit's own SKILL.md or agent file only names its mode and
the fields it fills; the rules below always apply. The machine-readable twin is
`reference/frameworks/presentation-modes.json`; the renderer is
`scripts/present.py`; the data contract is `templates/widget/summary.schema.json`.

## 1. Two-Tier delivery (mandatory for every run that produces a deliverable)

| Tier | What | Where it lives | Rule |
|---|---|---|---|
| Tier 1 | Executive quick-glance card: dimension bars (checks passed out of checks run), platform strip, query or competitor table, one key risk, 3-4 priority actions, transparency footer, hand-off card, 2-3 next steps | Rendered in the chat panel from `summary.json` | Always produced at the end of the run, after the Tier 2 file is written |
| Tier 2 | The full client deliverable: the single-page HTML report (`report-lite`), or the skill's own dated file under `work/{domain}/` or its registered client route | Client workspace, resolved with `client_workspace.py route` | Unchanged by this layer. Never truncated, never summarised in place, never replaced by the card |

Order of operations at the end of a run:

1. Write the Tier 2 deliverable through its registered route (existing rules).
2. Build `summary.json` (schema `rainmojo.tier1.summary/1`) from the same numbers
   the Tier 2 file carries. The card and the report must never disagree; every
   number on the card is copied from the deliverable, never re-estimated. Audit runs
   that used `agent_readiness_lite.py`, `page_analyzer.py` or `robots_generator.py`
   assemble it with `scripts/build_summary.py` (plus `--checklist` from
   `aiso-platform-lite` and `--sampling` from `aiso-brand-mentions-lite`) and only
   add the summary sentences by hand. Lite dimensions are counts of checks passed.
3. Resolve the working-data route `report-data` and save the summary next to the
   run's other working JSON (`reports/data/{domain}_{skillkey}_{YYYY-MM-DD}_summary.json`).
4. Render with `python {PLUGIN_ROOT}/skills/rainmojo-so-lite/scripts/present.py --summary <file> --target auto`
   and show the result to the user through the host capability ladder (section 2).
5. The hand-off card names the Tier 2 file (path or artifact URL) and its
   formats. The card is the door to the report, not a substitute for it.

## 2. Host capability ladder (Universal AI compatibility)

Pick the highest rung the current host can actually render. Never paste raw
HTML source into the chat as text.

| Rung | Host examples | Target flag | Output |
|---|---|---|---|
| 1 Host widget | Claude Desktop and Cowork inline widget tool, or any MCP Apps host with the plugin's card server connected (`scripts/mcp_server.py`: Claude web, Desktop, mobile, Cowork, Desktop Code tab, ChatGPT paid, Microsoft 365 Copilot, VS Code, Cursor, Goose, Postman) | `--target host` | HTML fragment using the host's CSS variables (MCP Apps `--color-*` tokens resolve as aliases) and Tabler outline icons, no outer background, 680 px wide, dark-mode safe |
| 2 Standalone HTML | Claude Artifacts, ChatGPT or Gemini canvas, Antigravity HTML artifact, Cursor or VS Code preview, browser preview pane. These hosts open a file; they do not embed a skill's HTML in the chat (inline cards in ChatGPT, Microsoft 365 Copilot, VS Code and Cursor come from the plugin's MCP server, see below) | `--target html` | Single self-contained file, inline CSS, inline SVG icons, zero external requests, reflows to 360 px |
| 3 Mermaid | Only a host that renders fenced `mermaid` blocks (GitHub, Claude, ChatGPT, Gemini, Cursor, Obsidian) | `--target mermaid` | Workflow, pipeline, decision tree or mindmap only. Never use Mermaid for score cards. A host that shows the block as raw code gets the ASCII rung instead |
| 3 ASCII | Plain-text viewers, Markdown previews without Mermaid, Windows consoles | `--target ascii` | Pure ASCII tree diagram (`+--`, `|`) of score, key risk, actions, dimensions, hand-off and next steps in a fenced `text` block |
| 4 Markdown | Terminal, CLI, plain-text chat, email | `--target md` | Rich Markdown: glyph progress bars, aligned tables, text status pills, GitHub alert blocks |

Detection order for `--target auto`: an explicit `RAINMOJO_PRESENT_TARGET`
environment variable wins; otherwise the calling unit passes the host it knows
(`--host` with one of claude-desktop, cowork, claude-code, claude-chrome, codex, gemini-cli,
artifact, chatgpt, gemini, cursor, vscode, antigravity, preview, github, obsidian, cli,
terminal, email); unknown hosts get Markdown. When a widget or artifact fails to render,
fall back one rung; never leave the user with nothing.

**No widget tool, no widget.** A skill can only call a widget tool the host lists in its
tool set. Codex, Gemini CLI, Antigravity and Claude Code expose none, and a plugin install
there ships skills only. On such a host: write the `html` target to the client report route
(Antigravity shows it as an artifact), put the `ascii` or `md` target in the reply, and name
the file. Never print HTML source as the reply.

**MCP Apps path (3.15.0).** `scripts/mcp_server.py` serves the same card as an MCP Apps
`ui://` resource (SEP-1865). When the `rainmojo-so-card` server is connected, call its
`present_card` tool with the summary object: the host draws the card inline (Claude web,
Desktop, mobile, Cowork, Desktop Code tab, ChatGPT paid plans, Microsoft 365 Copilot, VS Code,
Cursor, Goose, Postman) and text-only hosts show the tool's Markdown result. The card HTML is
fetched by the widget through the app-only tool `render_card_html`, so it never enters the
model context. Registered for Claude Code plugin installs by `.mcp.json`; Claude Desktop, Codex
and Antigravity users add the same stdio command to their MCP config; ChatGPT needs
`--http` behind HTTPS and OAuth 2.1 (Developer Mode privately, directory review publicly).

## 3. The seven response modes

Every reply that answers a question, not only report deliveries, uses one mode.
`next_steps` (mode 7) is a footer every mode carries.

| # | Mode | Trigger (th / en) | Structure the reader sees | summary.json fields |
|---|---|---|---|---|
| 1 | `quick_fact` | ถามสั้น, คืออะไร, ใช่ไหม, เท่าไร / what is, is it, how many, yes or no | Two-line answer box on top, then at most three bullets, no preamble | `tldr`, `bullets` |
| 2 | `howto` | ทำยังไง, ขั้นตอน, สอน / how do I, steps, guide, set up | Numbered steps (circled digits in Markdown), each with what to do and what result to expect, owner when known | `steps` |
| 3 | `comparison` | เปรียบเทียบ, เลือกอันไหน, ดีกว่า / compare, which should I, versus, pros and cons | Side-by-side table with impact and effort columns, then one decisive line "Recommendation for you" | `comparison` |
| 4 | `troubleshoot` | ทำไม, พัง, ไม่ขึ้น, แก้ยังไง / why, broken, not showing, error, fix | Root-cause callout (critical tint) naming the real cause, then three quick-fix steps | `root_cause`, `steps` |
| 5 | `audit` | ตรวจ, audit, วิเคราะห์, report, คะแนน / audit, analyse, score, visibility, report | Tier 1 card (section 1) with the hand-off to Tier 2 | `score`, `dimensions`, `platforms`, `query_matrix`, `competitors`, `key_risk`, `actions`, `transparency`, `handoff` |
| 6 | `deployable` | ขอไฟล์, generate, สร้าง schema, llms.txt, robots.txt / give me the file, generate, template, export | Clean code blocks with filename header and language, copy-ready, plus the client-confined path where the file was written and any CSV or Markdown export | `deployables` |
| 7 | `next_steps` | always | Two or three suggested next moves, each an exact slash command or message | `next_steps` |

Mode selection: the calling unit sets `mode` from the user's request; when a
request mixes modes, the primary deliverable decides (an audit that also ships a
robots.txt is `audit` with a `deployables` block, not two cards).

## 4. Advanced content extensions (optional blocks, any mode)

| Block | Use when | Field |
|---|---|---|
| Live AI or SERP mockup | Showing what an AI answer or AI Overview would look like with the client cited or missing | `mockup` |
| Before versus after diff | Rewritten title, description or passage; shows removed text, added text and score delta | `diff` |
| Role-based segmentation | The same finding read by an executive, a developer and a content writer | `roles` |
| Team checklist | Actions with department tags Dev, Content, Marketing, Client and dates | `checklist` |
| Data transparency badges | Every audit: crawl time, user agents used, guidelines applied, could-not-verify list | `transparency` |
| Sparklines | Any score or dimension with history from `compare` | `score.history`, `dimensions[].history` |

Component freedom: bento tiles, accordions, tooltips, tabbed views, sparklines
and any new component are welcome in Tier 1 as long as the hard rules in section
5 hold and the data comes from the schema. The shipped renderer uses a single
verdict-first column (the design panel judged it the most readable in 20 seconds),
sparklines and visible tooltip text; when a host adds accordions or tabs they ship
open in the HTML and collapse only after render, so nothing that matters is hidden
from a reader without JavaScript.

## 5. Hard rules (both tiers unless stated)

- No emoji or pictograph on any surface: chat, CLI, HTML, PDF, slides, files.
  Extended pictographic code points (U+1F000 to U+1FAFF, U+2600 to U+27BF except
  the glyph allowlist, U+FE0F, U+200D, U+1F1E6 to U+1F1FF) are rejected by
  `present.py --lint` and by the deep unit test gate.
- Typographic glyph allowlist, chat and Markdown only: `● ○ ◐ ◑ ■ □ ▲ ▼ ► ◄ ✓ ✗ ★ ☆ • → ← ↑ ↓ ↗ ↘ █ ▓ ▒ ░ ─ │ ┌ ┐ └ ┘ ├ ┤ ① ② ③ ④ ⑤ ⑥ ⑦ ⑧ ⑨ ⑩`.
  The HTML report and the standalone card use inline SVG icons only, never glyphs.
- No em dash and no pipe character in visible text (Markdown table delimiters
  are structural and exempt). Sentence case for headings and labels, never ALL CAPS.
- Status colours are semantic and fixed (`--status-critical #D64545`,
  `--status-warning #B9740B`, `--status-ok #2E9E6B`, `--status-info #2B6CB0`);
  only `--brand-primary`, `--brand-accent`, `--brand-accent-ink` follow the client.
- Anti-slop: no side accent strips, no gradients, no glow, no shadow stacked on a
  hairline, no icon tiles above headings, radius cap 14 px on cards, 999 px on pills.
- Every number on a card is copied from the deliverable. A value the run could not
  measure is shown as could not verify (`null` score, `unverifiable` access) with
  the reason in `transparency.could_not_verify`. Never estimate to fill a slot.
- Language (`meta.lang`) is decided in this order: an explicit language instruction in the
  user's request wins; otherwise the output language in the client profile; otherwise the
  language the user wrote the request in. The card and the Tier 2 deliverable use the same
  language. Shipped samples render in their own `meta.lang` (use the `-th` files to demo
  Thai). Thai output uses the plugin's Thai typography rules (Noto Sans Thai or Sarabun
  stack, 16 px body).
- The Markdown fallback is the only rendering that may use progress bars, and the
  bars are pure ASCII (`[########--] 8.0/10`) because block-shade glyphs fall back
  to another font in most previews and overflow the line; text pills (`[PASS]`, `[WARN]`, `[CRIT]`, `[INFO]`,
  `[N/A]`); GitHub alert blocks (`> [!WARNING]`, `> [!IMPORTANT]`, `> [!TIP]`)
  carry the key risk and the recommendation.

## 6. Installation marker

Units carry this block so the gate can verify adoption:

```
<!-- RAINMOJO_PRESENTATION_LAYER_V1 -->
## Presentation (Two-Tier, 7 modes)
Answer in the response mode that matches the request (`_base/presentation-scaffold.md`).
A run that writes a deliverable ends with a Tier 1 card built from
`summary.json` (`templates/widget/summary.schema.json`) and rendered with
`scripts/present.py --target auto`, then hands off to the Tier 2 file. Every card
number is copied from the deliverable; unmeasured values show as could not verify.
No emoji on any surface; glyph allowlist applies to chat and Markdown only.
```

`scripts/presentation_instruction_gate.py --apply` inserts it after the
routing block in every public SKILL.md and agent file; running the script with
no flag verifies and fails when any public unit lacks it.
