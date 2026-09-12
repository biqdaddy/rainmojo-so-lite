#!/usr/bin/env python3
"""
present.py - Tier 1 presentation renderer for RAINMOJO SO.

Reads a summary.json (contract: templates/widget/summary.schema.json) and renders
the executive quick-glance card for the host the caller is running in:

  --target host     HTML fragment for an inline chat widget (host CSS variables,
                    Tabler outline icons, transparent outer background)
  --target html     single self-contained HTML card (inline CSS + SVG, zero
                    external requests) for artifacts, canvases, preview panes
  --target mermaid  Mermaid flowchart of the steps / actions / pipeline (only for
                    hosts that render fenced mermaid; others show raw code)
  --target ascii    pure ASCII tree diagram in a fenced text block, for any viewer
  --target md       rich Markdown for terminals and plain-text chat
  --target auto     pick from RAINMOJO_PRESENT_TARGET, then --host, else md

Also:
  --lint            check the summary text against the glyph and emoji policy,
                    em dash and pipe rules, and the schema; exit 1 on failure
  --validate        schema validation only

The generator is pure ASCII on purpose: every visible label lives in
templates/widget/labels.json, every glyph in reference/frameworks/presentation-modes.json,
every stylesheet in templates/widget/*.css. Standard library only; jsonschema is
used when installed, otherwise a minimal structural check runs.

Usage:
  python present.py --summary reports/data/x_summary.json --target auto --host claude-code
  python present.py --summary x.json --target html --out card.html
  python present.py --summary x.json --lint
"""

import argparse
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SCHEMA_PATH = os.path.join(ROOT, "templates", "widget", "summary.schema.json")
LABELS_PATH = os.path.join(ROOT, "templates", "widget", "labels.json")
MODES_PATH = os.path.join(ROOT, "reference", "frameworks", "presentation-modes.json")
CSS_STANDALONE = os.path.join(ROOT, "templates", "widget", "tier1-standalone.css")
CSS_HOST = os.path.join(ROOT, "templates", "widget", "tier1-host.css")
ICONS_PATH = os.path.join(ROOT, "templates", "widget", "icons.json")

HOST_TARGET = {
    "claude-desktop": "host", "cowork": "host",
    "artifact": "html", "chatgpt": "html", "gemini": "html", "cursor": "html",
    "vscode": "html", "preview": "html",
    "github": "mermaid", "obsidian": "mermaid",
    "claude-code": "md", "cli": "md", "terminal": "md", "email": "md",
}


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_summary(path):
    if path == "-":
        data = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
        return json.loads(data.decode("utf-8-sig"))
    return _load(path)


def labels_for(lang):
    all_labels = _load(LABELS_PATH)
    return all_labels.get(lang) or all_labels["en"]


def modes():
    return _load(MODES_PATH)


# ---------------------------------------------------------------------------
# validation and lint
# ---------------------------------------------------------------------------

def validate(summary):
    """Return a list of problems (empty = valid)."""
    schema = _load(SCHEMA_PATH)
    try:
        import jsonschema  # type: ignore
        v = jsonschema.Draft202012Validator(schema)
        return [e.message for e in sorted(v.iter_errors(summary), key=lambda e: list(e.path))]
    except ImportError:
        problems = []
        for key in schema.get("required", []):
            if key not in summary:
                problems.append("missing required field: %s" % key)
        if summary.get("schema") != schema["properties"]["schema"]["const"]:
            problems.append("schema id must be %s" % schema["properties"]["schema"]["const"])
        if summary.get("mode") not in schema["properties"]["mode"]["enum"]:
            problems.append("mode must be one of %s" % ", ".join(schema["properties"]["mode"]["enum"]))
        return problems


def _walk_strings(node, path="$"):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            for item in _walk_strings(v, "%s.%s" % (path, k)):
                yield item
    elif isinstance(node, list):
        for i, v in enumerate(node):
            for item in _walk_strings(v, "%s[%d]" % (path, i)):
                yield item


def _forbidden_ranges(policy):
    out = []
    for lo, hi in policy["forbidden_ranges"]:
        out.append((int(lo, 16), int(hi, 16)))
    return out


def lint(summary, allow_pipe_paths=("$.deployables", "$.diff", "$.mockup")):
    """Glyph, emoji, em dash and pipe policy for every visible string."""
    policy = modes()["glyph_policy"]
    allow = set(policy["chat_and_markdown_allowlist"])
    ranges = _forbidden_ranges(policy)
    em_dash = modes()["forbidden_text"]["em_dash"]
    problems = []
    for path, text in _walk_strings(summary):
        if path.startswith("$.next_steps") and path.endswith(".prompt"):
            continue
        for ch in text:
            cp = ord(ch)
            if ch in allow:
                continue
            for lo, hi in ranges:
                if lo <= cp <= hi:
                    problems.append("%s: forbidden pictograph U+%04X" % (path, cp))
                    break
        if em_dash in text:
            problems.append("%s: em dash is not allowed" % path)
        if "|" in text and not path.startswith(allow_pipe_paths):
            problems.append("%s: pipe character is not allowed in visible text" % path)
    return problems


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def esc(text):
    return html.escape("" if text is None else str(text), quote=True)


def fmt_num(value, digits=1):
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return ("%%.%df" % digits) % float(value)


def pct(value, maximum):
    try:
        return max(0, min(100, round(100.0 * float(value) / float(maximum))))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0




def resolve_target(target, host):
    if target != "auto":
        return target
    env = os.environ.get("RAINMOJO_PRESENT_TARGET")
    if env in ("host", "html", "mermaid", "ascii", "md"):
        return env
    if host:
        return HOST_TARGET.get(host, "md")
    return "md"


# ---------------------------------------------------------------------------
# Markdown renderer (rung 4)
# ---------------------------------------------------------------------------

def _bar(value, maximum, policy):
    width = policy["bar"]["width"]
    filled = int(round(width * pct(value, maximum) / 100.0)) if value is not None else 0
    return policy["bar"].get("open", "[") + policy["bar"]["filled"] * filled + policy["bar"]["empty"] * (width - filled) + policy["bar"].get("close", "]")


def _pill(status, policy):
    return policy["text_pills"].get(status, "[INFO]")


def _md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/") for c in r) + " |")
    return "\n".join(out)


def render_md(s):
    L = labels_for(s["meta"].get("lang", "en"))
    policy = modes()["glyph_policy"]
    circled = [chr(0x2460 + i) for i in range(10)]
    out = []
    head = s["headline"]
    if head.get("kicker"):
        out.append("*%s*" % head["kicker"])
    out.append("## %s" % head["title"])
    if head.get("subtitle"):
        out.append(head["subtitle"])
    out.append("")

    mode = s["mode"]
    if mode == "quick_fact":
        if s.get("tldr"):
            out.append("> [!TIP]")
            for line in s["tldr"]:
                out.append("> %s" % line)
            out.append("")
        for b in s.get("bullets", []):
            out.append("- %s" % b)
        out.append("")

    if s.get("score"):
        sc = s["score"]
        line = "**%s: %s/%s** %s %s" % (L["overall_score"], fmt_num(sc["value"]), fmt_num(sc["max"]),
                                      _pill(sc["status"], policy), sc["status_label"])
        if sc.get("grade"):
            line += " (%s %s)" % (L["grade"], sc["grade"])
        if sc.get("delta") is not None:
            arrow = chr(0x2191) if sc["delta"] >= 0 else chr(0x2193)
            line += "  %s %s %s" % (arrow, fmt_num(abs(sc["delta"])), L["vs_previous"])
        line += "  `%s` %s%%" % (_bar(sc["value"], sc["max"], policy), pct(sc["value"], sc["max"]))
        out.append(line)
        out.append("")
    if s.get("summary"):
        out.append(s["summary"])
        out.append("")

    if s.get("dimensions"):
        out.append("### %s" % L["dimensions"])
        width = max(len(d["label"]) for d in s["dimensions"])
        for d in s["dimensions"]:
            out.append("- `%s %s %s/%s` %s" % (d["label"].ljust(width), _bar(d["value"], d["max"], policy),
                                           fmt_num(d["value"]), fmt_num(d["max"]), _pill(d["status"], policy)))
        out.append("")

    if s.get("platforms"):
        out.append("### %s" % L["platforms"])
        rows = []
        for p in s["platforms"]:
            score = fmt_num(p["score"]) if p["score"] is not None else L["not_scored"]
            rows.append([p["label"], score, _pill(p["status"], policy),
                         L["access"].get(p["crawler_access"], p["crawler_access"]), p.get("note", "")])
        out.append(_md_table([L["platform"], L["score"], "", L["crawler"], L["note"]], rows))
        out.append("")

    if s.get("query_matrix"):
        out.append("### %s" % L["query_matrix"])
        rows = []
        for q in s["query_matrix"]:
            rows.append([q["query"], q.get("platform", ""), L["cited_values"].get(q["cited"], q["cited"]),
                         L["position_values"].get(q["position"], q["position"]),
                         L["sentiment_values"].get(q.get("sentiment", ""), q.get("sentiment", ""))])
        out.append(_md_table([L["query"], L["platform"], L["cited"], L["position"], L["sentiment"]], rows))
        out.append("")

    if s.get("competitors"):
        out.append("### %s" % L["competitors"])
        rows = []
        for c in s["competitors"]:
            name = c["name"] + (" (%s)" % L["you"] if c.get("is_client") else "")
            mx = c.get("max", 100)
            rows.append([name, c.get("tagline", ""), "%s/%s" % (fmt_num(c["score"]), fmt_num(mx)),
                         "`%s`" % _bar(c["score"], mx, policy)])
        out.append(_md_table(["", "", L["score"], ""], rows))
        out.append("")

    if s.get("root_cause"):
        rc = s["root_cause"]
        out.append("> [!CAUTION]")
        out.append("> **%s: %s**" % (L["root_cause"], rc["title"]))
        if rc.get("symptom"):
            out.append("> %s" % rc["symptom"])
        out.append("> %s" % rc["body"])
        out.append("")

    if s.get("key_risk"):
        kr = s["key_risk"]
        out.append("> [!WARNING]")
        out.append("> **%s**" % kr["title"])
        out.append("> %s" % kr["body"])
        out.append("")

    if s.get("comparison"):
        cp = s["comparison"]
        out.append("### %s" % L["comparison"])
        headers = [""] + list(cp["columns"])
        has_ie = any(r.get("impact") or r.get("effort") for r in cp["rows"])
        if has_ie:
            headers += [L["impact"], L["effort"]]
        rows = []
        for r in cp["rows"]:
            row = [r["label"]] + list(r["cells"])
            if has_ie:
                row += [L["impact_values"].get(r.get("impact", ""), r.get("impact", "")),
                        L["effort_values"].get(r.get("effort", ""), r.get("effort", ""))]
            rows.append(row)
        out.append(_md_table(headers, rows))
        out.append("")
        out.append("> [!IMPORTANT]")
        out.append("> **%s:** %s" % (L["recommendation"], cp["recommendation"]))
        out.append("")

    if s.get("steps"):
        out.append("### %s" % L["steps"])
        for i, st in enumerate(s["steps"]):
            n = circled[i] if i < len(circled) else "%d." % (i + 1)
            out.append("%s **%s**" % (n, st["title"]))
            out.append("   %s: %s" % (L["do"], st["do"]))
            if st.get("expect"):
                out.append("   %s: %s" % (L["expect"], st["expect"]))
            if st.get("owner"):
                out.append("   %s: %s" % (L["owner"], st["owner"]))
        out.append("")

    if s.get("actions"):
        out.append("### %s" % L["actions"])
        for i, a in enumerate(s["actions"]):
            n = circled[i] if i < len(circled) else "%d." % (i + 1)
            tags = [L["impact_values"].get(a["impact"], a["impact"])]
            if a.get("effort"):
                tags.append(L["effort_values"].get(a["effort"], a["effort"]))
            if a.get("owner"):
                tags.append("[%s]" % a["owner"])
            if a.get("eta"):
                tags.append(a["eta"])
            out.append("%s **%s**  %s" % (n, a["title"], "  ".join(tags)))
            out.append("   %s" % a["body"])
        out.append("")

    if s.get("checklist"):
        out.append("### %s" % L["checklist"])
        for c in s["checklist"]:
            box = "[x]" if c.get("done") else "[ ]"
            extra = " ".join(x for x in [c.get("priority", ""), c.get("eta", "")] if x)
            out.append("- %s [%s] %s %s" % (box, c["owner"], c["task"], extra))
        out.append("")

    if s.get("diff"):
        d = s["diff"]
        out.append("### %s: %s" % (L["diff"], d["label"]))
        out.append("```diff")
        out.append("- %s" % d["before"])
        out.append("+ %s" % d["after"])
        out.append("```")
        if d.get("score_before") is not None and d.get("score_after") is not None:
            out.append("%s %s, %s %s" % (L["before"], fmt_num(d["score_before"]), L["after"], fmt_num(d["score_after"])))
        out.append("")

    if s.get("mockup"):
        m = s["mockup"]
        out.append("### %s (%s)" % (L["mockup"], m["surface"]))
        out.append("> %s" % m["query"])
        out.append(">")
        out.append("> %s" % m["answer_excerpt"])
        if m.get("cited_sources"):
            out.append("> %s: %s" % (L["cited_sources"], ", ".join(m["cited_sources"])))
        out.append("")

    if s.get("deployables"):
        out.append("### %s" % L["deployables"])
        for d in s["deployables"]:
            out.append("**%s**" % d["filename"])
            out.append("```%s" % d["language"])
            out.append(d["content"].rstrip("\n"))
            out.append("```")
            if d.get("path"):
                out.append("%s `%s`" % (L["written_to"], d["path"]))
            out.append("")

    if s.get("roles"):
        out.append("### %s" % L["roles"])
        for key in ("executive", "developer", "content"):
            if s["roles"].get(key):
                out.append("**%s**" % L[key])
                for line in s["roles"][key]:
                    out.append("- %s" % line)
        out.append("")

    if s.get("transparency"):
        t = s["transparency"]
        bits = []
        if t.get("crawled_at"):
            bits.append("%s %s" % (L["crawled_at"], t["crawled_at"]))
        if t.get("user_agents"):
            bits.append("%s: %s" % (L["user_agents"], ", ".join(t["user_agents"])))
        if t.get("guidelines"):
            bits.append("%s: %s" % (L["guidelines"], ", ".join(t["guidelines"])))
        if t.get("sources"):
            bits.append("%s: %s" % (L["sources"], ", ".join(t["sources"])))
        out.append("*%s: %s*" % (L["transparency"], "; ".join(bits)))
        if t.get("could_not_verify"):
            out.append("")
            out.append("> [!NOTE]")
            out.append("> **%s:** %s" % (L["could_not_verify"], "; ".join(t["could_not_verify"])))
        out.append("")

    h = s["handoff"]
    target = h.get("tier2_url") or h.get("tier2_path") or ""
    line = "**%s:** %s" % (L["handoff"], h["tier2_label"])
    if target:
        line += " `%s`" % target
    if h.get("formats"):
        line += " (%s: %s)" % (L["formats"], ", ".join(h["formats"]))
    out.append(line)
    out.append("")
    out.append("### %s" % L["next_steps"])
    for n in s["next_steps"]:
        out.append("- %s: `%s`" % (n["label"], n["prompt"]))
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Mermaid renderer (rung 3)
# ---------------------------------------------------------------------------

def _mm(text, limit=60):
    text = re.sub(r"[\"\[\]{}()|]", " ", str(text)).strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text


def render_mermaid(s):
    L = labels_for(s["meta"].get("lang", "en"))
    lines = ["flowchart TD"]
    title = _mm(s["headline"]["title"])
    lines.append('    T["%s"]' % title)
    prev = "T"
    seq = s.get("steps") or s.get("actions") or []
    for i, item in enumerate(seq):
        node = "S%d" % (i + 1)
        label = _mm(item.get("title") or item.get("do", ""))
        lines.append('    %s["%d. %s"]' % (node, i + 1, label))
        lines.append("    %s --> %s" % (prev, node))
        prev = node
    if s.get("key_risk"):
        lines.append('    R{{"%s"}}' % _mm(s["key_risk"]["title"]))
        lines.append("    T --> R")
    if s.get("comparison"):
        for i, row in enumerate(s["comparison"]["rows"]):
            node = "C%d" % (i + 1)
            lines.append('    %s["%s"]' % (node, _mm(row["label"])))
            lines.append("    T --> %s" % node)
        lines.append('    REC["%s: %s"]' % (_mm(L["recommendation"]), _mm(s["comparison"]["recommendation"])))
        lines.append("    T --> REC")
    lines.append('    H["%s"]' % _mm(s["handoff"]["tier2_label"]))
    lines.append("    %s --> H" % prev)
    for i, n in enumerate(s.get("next_steps", [])):
        node = "N%d" % (i + 1)
        lines.append('    %s["%s"]' % (node, _mm(n["label"])))
        lines.append("    H --> %s" % node)
    return "```mermaid\n" + "\n".join(lines) + "\n```\n"


# ---------------------------------------------------------------------------
# ASCII renderer (rung 3 fallback): pure ASCII tree, safe in any font or console
# ---------------------------------------------------------------------------

def _tree(children, last_prefix="    ", mid_prefix="|   "):
    """children: list of (line, sub_children). Returns lines with +-- and | connectors."""
    lines = []
    for i, (label, subs) in enumerate(children):
        last = i == len(children) - 1
        lines.append("+-- " + label)
        sub_lines = _tree(subs) if subs else []
        pre = last_prefix if last else mid_prefix
        lines.extend(pre + sl for sl in sub_lines)
        if subs and not last:
            lines.append("|")
    return lines


def render_ascii(s):
    L = labels_for(s["meta"].get("lang", "en"))
    policy = modes()["glyph_policy"]
    head = s["headline"]
    top = [head["title"] + ((" (" + head["subtitle"] + ")") if head.get("subtitle") else "")]
    if s.get("score"):
        sc = s["score"]
        top.append("%s %s/%s %s %s  %s" % (L["overall_score"], fmt_num(sc["value"]), fmt_num(sc["max"]),
                                         _pill(sc["status"], policy), sc["status_label"], _bar(sc["value"], sc["max"], policy)))
    nodes = []
    if s.get("key_risk"):
        kr = s["key_risk"]
        nodes.append(("%s %s: %s" % (_pill("critical" if kr.get("severity") == "critical" else "warning", policy), L["key_risk"], kr["title"]), []))
    if s.get("root_cause"):
        nodes.append(("%s: %s" % (L["root_cause"], s["root_cause"]["title"]), []))
    seq = s.get("steps") or s.get("actions") or []
    if seq:
        items = []
        for i, item in enumerate(seq):
            label = "%d. %s" % (i + 1, item.get("title") or item.get("do", ""))
            meta = []
            if item.get("impact"):
                meta.append(L["impact_values"].get(item["impact"], item["impact"]) if isinstance(L.get("impact_values"), dict) else item["impact"])
            if item.get("owner"):
                meta.append(item["owner"])
            items.append((label + (("  [" + ", ".join(meta) + "]") if meta else ""), []))
        nodes.append((L["steps"] if s.get("steps") else L["actions"], items))
    if s.get("dimensions"):
        width = max(len(d["label"]) for d in s["dimensions"])
        nodes.append((L["dimensions"], [("%s %s %s/%s %s" % (d["label"].ljust(width), _bar(d["value"], d["max"], policy), fmt_num(d["value"]), fmt_num(d["max"]), _pill(d["status"], policy)), []) for d in s["dimensions"]]))
    if s.get("comparison"):
        c = s["comparison"]
        cols = c.get("columns") or []
        rows = []
        for r in c["rows"]:
            cells = r.get("cells") or []
            subs = [("%s: %s" % (cols[i], v) if i < len(cols) else str(v), []) for i, v in enumerate(cells)]
            rows.append((r["label"], subs))
        nodes.append((L["comparison"], rows + [("%s: %s" % (L["recommendation"], c["recommendation"]), [])]))
    h = s["handoff"]
    nodes.append(("%s: %s" % (L["handoff"], h["tier2_label"]), [(h["tier2_path"], [])] + ([(", ".join(h["formats"]), [])] if h.get("formats") else [])))
    if s.get("next_steps"):
        nodes.append((L["next_steps"], [("%s: %s" % (n["label"], n.get("prompt", "")), []) for n in s["next_steps"]]))
    body = top + ["|"] + _tree(nodes)
    return "```text\n" + "\n".join(body) + "\n```\n"


# ---------------------------------------------------------------------------
# HTML renderers (rungs 1 and 2) live in present_html.py
# ---------------------------------------------------------------------------

def render_html(s):
    from present_html import render_standalone  # noqa: E402
    return render_standalone(s, labels_for(s["meta"].get("lang", "en")), modes())


def render_host(s):
    from present_html import render_host_fragment  # noqa: E402
    return render_host_fragment(s, labels_for(s["meta"].get("lang", "en")), modes())


RENDERERS = {"md": render_md, "mermaid": render_mermaid, "ascii": render_ascii, "html": render_html, "host": render_host}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def self_test():
    """Lint every shipped widget sample and render it to every target."""
    import glob
    samples = sorted(glob.glob(os.path.join(ROOT, "templates", "widget", "samples", "*.json")))
    assert samples, "no widget samples found"
    rendered = 0
    for path in samples:
        s = load_summary(path)
        problems = validate(s) + lint(s)
        assert not problems, (path, problems)
        for target, fn in RENDERERS.items():
            text = fn(s)
            assert text and len(text) > 40, (path, target)
            rendered += 1
    print("SELF-TEST PASS: %d samples, %d renders, policy-clean" % (len(samples), rendered))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a RAINMOJO SO Tier 1 summary for the current host.")
    ap.add_argument("--summary", required=False, help="summary.json path, or - for stdin")
    ap.add_argument("--self-test", action="store_true", help="lint and render every widget sample to every target")
    ap.add_argument("--target", default="auto", choices=["auto", "host", "html", "mermaid", "ascii", "md"])
    ap.add_argument("--host", default=None, help="host hint for --target auto: " + ", ".join(sorted(HOST_TARGET)))
    ap.add_argument("--out", default=None, help="write here instead of stdout")
    ap.add_argument("--lint", action="store_true", help="policy lint + schema validation, no render")
    ap.add_argument("--validate", action="store_true", help="schema validation only")
    ap.add_argument("--no-validate", action="store_true", help="skip validation before rendering")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.self_test:
        return self_test()
    if not args.summary:
        ap.error("--summary is required")
    summary = load_summary(args.summary)

    if args.validate or args.lint:
        problems = validate(summary)
        if args.lint:
            problems += lint(summary)
        for p in problems:
            print("FAIL " + p)
        print("PASS summary is valid and policy-clean" if not problems else "RESULT: %d problem(s)" % len(problems))
        return 1 if problems else 0

    if not args.no_validate:
        problems = validate(summary) + lint(summary)
        if problems:
            for p in problems:
                sys.stderr.write("present.py: " + p + "\n")
            return 1

    target = resolve_target(args.target, args.host)
    text = RENDERERS[target](summary)
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        sys.stderr.write("present.py: wrote %s (%s, %d bytes)\n" % (args.out, target, len(text.encode("utf-8"))))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
