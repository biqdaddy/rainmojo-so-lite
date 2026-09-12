#!/usr/bin/env python3
"""
present_html.py - HTML renderers for the Tier 1 card (used by present.py).

  render_standalone(summary, labels, modes)   rung 2: one self-contained HTML file
  render_host_fragment(summary, labels, modes) rung 1: fragment for an inline chat widget

Both share the same block builders; a small Theme object decides how icons and
section headings are emitted and which stylesheet is inlined:

  standalone  templates/widget/tier1-standalone.css, inline SVG icons from icons.json,
              light palette on :root with a full dark override, three brand tokens
              applied on the root element, zero external requests.
  host        templates/widget/tier1-host.css written against the host's CSS variables
              (--text-primary, --surface-1, --border, --bg-danger ...), Tabler outline
              webfont icons the host already loads, transparent outer background,
              two font weights only, no display:none and no fixed positioning.

Pure ASCII by design: every visible label comes from labels.json and every glyph
from presentation-modes.json. Standard library only.
"""

import html as _html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
WIDGET = os.path.join(ROOT, "templates", "widget")


def esc(text):
    return _html.escape("" if text is None else str(text), quote=True)


def fmt_num(value, digits=1):
    if value is None:
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return esc(value)
    if f.is_integer():
        return str(int(f))
    return ("%%.%df" % digits) % f


def pct(value, maximum):
    try:
        return max(0, min(100, round(100.0 * float(value) / float(maximum))))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


class Theme(object):
    def __init__(self, kind, icons):
        self.kind = kind
        self.icons = icons

    def icon(self, name, cls="i", label=None):
        spec = self.icons["icons"].get(name)
        if not spec:
            return ""
        aria = ' role="img" aria-label="%s"' % esc(label) if label else ' aria-hidden="true"'
        if self.kind == "host":
            return '<i class="ti %s %s"%s></i>' % (spec["host"], cls, aria)
        return '<svg class="%s" viewBox="%s" %s%s>%s</svg>' % (cls, self.icons["viewBox"], self.icons["attrs"], aria, spec["svg"])

    def sh(self, text, right=None):
        """Section heading: muted small label, optional right-aligned count."""
        r = ' <span class="shr">%s</span>' % esc(right) if right else ""
        if self.kind == "host":
            return '<div class="rm-sh">%s%s</div>' % (esc(text), r)
        return '<h2>%s%s</h2>' % (esc(text), r)


def _status(status):
    return status if status in ("ok", "warning", "critical", "info") else "info"


def _pill(L, status, text=None):
    st = _status(status)
    return '<span class="pill pill--%s">%s</span>' % (st, esc(text if text is not None else L["status_values"][st]))


def _dot(status, L):
    st = _status(status)
    return '<i class="dot dot--%s" aria-hidden="true"></i><span class="sr">%s. </span>' % (st, esc(L["status_values"][st]))


def _sparkline(points, caption, T, w=72, h=22):
    pts = [float(p) for p in points if p is not None]
    if len(pts) < 2:
        return ""
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1.0
    coords = []
    for i, p in enumerate(pts):
        x = 2 + (w - 4) * i / float(len(pts) - 1)
        y = h - 3 - (h - 6) * (p - lo) / span
        coords.append("%.1f,%.1f" % (x, y))
    last = coords[-1].split(",")
    svg = ('<svg viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s"><polyline points="%s"/>'
           '<circle cx="%s" cy="%s" r="2"/></svg>' % (w, h, w, h, esc(caption), " ".join(coords), last[0], last[1]))
    return '<span class="spark">%s<span>%s</span></span>' % (svg, esc(caption))


# ---------------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------------

def block_header(s, L, T):
    head = s["headline"]
    meta = s["meta"]
    out = []
    kicker = head.get("kicker")
    if kicker and not head["title"].lower().startswith(kicker.lower()):
        out.append('<div class="kicker">%s</div>' % esc(kicker))
    out.append('<h1>%s</h1>' % esc(head["title"]))
    if head.get("subtitle"):
        out.append('<div class="sub">%s</div>' % esc(head["subtitle"]))
    bits = [esc(meta.get("skill", ""))]
    mode_label = {"quick_fact": "Quick fact", "howto": "How-to", "comparison": "Comparison",
                  "troubleshoot": "Troubleshoot", "audit": "Audit", "deployable": "Deployable"}.get(s["mode"], s["mode"])
    bits.append(esc(mode_label))
    if meta.get("run_id"):
        bits.append("Run " + esc(meta["run_id"]))
    bits.append(esc(meta.get("generated_at", "")))
    out.append('<div class="meta">%s</div>' % "".join("<span>%s</span>" % b for b in bits if b))
    return "\n".join(out)


def block_hero(s, L, T):
    sc = s.get("score")
    if not sc:
        return ('<p class="summary">%s</p>' % esc(s["summary"])) if s.get("summary") else ""
    p = pct(sc["value"], sc["max"])
    r = 40.0
    circ = 2 * 3.14159265 * r
    offset = circ * (1 - p / 100.0)
    ring = ('<div class="ring"><svg viewBox="0 0 96 96" aria-hidden="true"><circle class="tr" cx="48" cy="48" r="%d"/>'
            '<circle class="fl" cx="48" cy="48" r="%d" stroke-dasharray="%.2f" stroke-dashoffset="%.2f"/></svg>'
            '<div class="val">%s<small>/%s</small></div></div>' % (r, r, circ, offset, fmt_num(sc["value"]), fmt_num(sc["max"])))
    hb = [_pill(L, sc["status"], sc["status_label"])]
    if sc.get("grade"):
        hb.append('<span class="grade">%s %s</span>' % (esc(L["grade"]), esc(sc["grade"])))
    if sc.get("delta") is not None:
        up = float(sc["delta"]) >= 0
        hb.append('<span class="delta">%s%s%s %s</span>' % (
            T.icon("trend-up" if up else "trend-down"), "+" if up else "-", fmt_num(abs(float(sc["delta"]))), esc(L["vs_previous"])))
    if sc.get("history"):
        hist = [fmt_num(x) for x in sc["history"]]
        cap = "%d runs, %s to %s" % (len(hist), hist[0], hist[-1])
        hb.append(_sparkline(sc["history"], cap, T))
    right = ['<div class="hb">%s</div>' % " ".join(hb)]
    right.append('<p class="summary"><span class="sr">%s. </span>%s</p>' % (esc(L["overall_score"]), esc(s.get("summary", ""))))
    return '<div class="hero">%s<div>%s</div></div>' % (ring, "".join(right))


def block_quick(s, L, T):
    out = []
    if s.get("tldr"):
        out.append('<div class="tldr">%s</div>' % "<br>".join(esc(x) for x in s["tldr"]))
    if s.get("bullets"):
        out.append('<ul class="bul">%s</ul>' % "".join("<li>%s</li>" % esc(b) for b in s["bullets"]))
    return "\n".join(out)


def block_callout(item, L, T, kind, heading):
    if not item:
        return ""
    sev = item.get("severity", "critical")
    cls = "callout" + (" is-warning" if sev == "warning" else "")
    pill = _pill(L, "critical" if sev == "critical" else "warning", L["status_values"]["critical"] if sev == "critical" else L["status_values"]["warning"])
    title = item["title"]
    body = item["body"]
    extra = ('<p><b>%s</b></p>' % esc(item["symptom"])) if item.get("symptom") else ""
    return ('<div class="%s" role="note"><div class="ch">%s<span>%s</span>%s</div>%s<p>%s</p></div>'
            % (cls, T.icon("alert"), esc(title), pill, extra, esc(body)))


def block_actions(s, L, T):
    acts = s.get("actions") or []
    if not acts:
        return ""
    items = []
    for i, a in enumerate(acts):
        tags = ['<span class="pill pill--%s">%s</span>' % ({"high": "ok", "medium": "warning", "low": "neutral"}.get(a["impact"], "neutral"), esc(L["impact_values"].get(a["impact"], a["impact"])))]
        if a.get("effort"):
            tags.append('<span class="tag">%s</span>' % esc(L["effort_values"].get(a["effort"], a["effort"])))
        if a.get("owner"):
            tags.append('<span class="tag">%s%s</span>' % (T.icon("user"), esc(a["owner"])))
        if a.get("eta"):
            tags.append('<span class="tag">%s%s</span>' % (T.icon("clock"), esc(a["eta"])))
        items.append('<li><span class="n">%d</span><div><h3>%s</h3><p>%s</p><div class="tags">%s</div></div></li>'
                     % (i + 1, esc(a["title"]), esc(a["body"]), "".join(tags)))
    return T.sh(L["actions"], "%d" % len(acts)) + '<ol class="acts">%s</ol>' % "".join(items)


def block_steps(s, L, T):
    steps = s.get("steps") or []
    if not steps:
        return ""
    items = []
    for i, st in enumerate(steps):
        kv = ['<div class="kv"><b>%s:</b> %s</div>' % (esc(L["do"]), esc(st["do"]))]
        if st.get("expect"):
            kv.append('<div class="kv"><b>%s:</b> %s</div>' % (esc(L["expect"]), esc(st["expect"])))
        if st.get("owner"):
            kv.append('<div class="kv"><b>%s:</b> %s</div>' % (esc(L["owner"]), esc(st["owner"])))
        items.append('<li><span class="n">%d</span><div><h3>%s</h3>%s</div></li>' % (i + 1, esc(st["title"]), "".join(kv)))
    return T.sh(L["steps"], "%d" % len(steps)) + '<ol class="steps acts">%s</ol>' % "".join(items)


def block_dimensions(s, L, T):
    dims = s.get("dimensions") or []
    if not dims:
        return ""
    rows = []
    for d in dims:
        st = _status(d["status"])
        desc = ('<div class="dd">%s</div>' % esc(d["tooltip"])) if d.get("tooltip") else ""
        spark = _sparkline(d["history"], "%d runs" % len(d["history"]), T, w=48, h=16) if d.get("history") else ""
        rows.append('<div class="dim"><div><div class="dn">%s</div>%s</div>'
                    '<div class="bar bar--%s" role="img" aria-label="%s %s of %s"><i style="width:%d%%"></i></div>'
                    '<div class="dv">%s%s<small>/%s</small>%s</div></div>'
                    % (esc(d["label"]), desc, st, esc(d["label"]), fmt_num(d["value"]), fmt_num(d["max"]), pct(d["value"], d["max"]),
                       _dot(st, L), fmt_num(d["value"]), fmt_num(d["max"]), spark))
    return T.sh(L["dimensions"], "%s %s" % ("/", fmt_num(dims[0]["max"])) if dims else "") + '<div class="dims">%s</div>' % "".join(rows)


def block_competitors(s, L, T):
    comps = s.get("competitors") or []
    if not comps:
        return ""
    cards = []
    for c in comps:
        mx = c.get("max", 100)
        cls = "cc is-client" if c.get("is_client") else "cc"
        bar = "bar--brand" if c.get("is_client") else "bar--neutral"
        you = (' <span class="pill pill--neutral">%s</span>' % esc(L["you"])) if c.get("is_client") else ""
        cards.append('<div class="%s"><div class="cn">%s%s</div><div class="ct">%s</div>'
                     '<div class="bar %s"><i style="width:%d%%"></i></div>'
                     '<div class="cs"><span>%s</span><b>%s / %s</b></div></div>'
                     % (cls, esc(c["name"]), you, esc(c.get("tagline", "")), bar, pct(c["score"], mx), esc(L["score"]), fmt_num(c["score"]), fmt_num(mx)))
    return T.sh(L["competitors"], "%d" % len(comps)) + '<div class="comp">%s</div>' % "".join(cards)


def block_platforms(s, L, T):
    plats = s.get("platforms") or []
    if not plats:
        return ""
    access_icon = {"allowed": ("circle-check", "ok"), "blocked": ("circle-x", "critical"), "partial": ("circle-half", "warning"),
                   "unverifiable": ("circle-dashed", "na"), "not_checked": ("help", "na")}
    chips = []
    for p in plats:
        st = _status(p["status"])
        # a missing score never sits in the narrow score column: the pill moves to the full-width
        # access row so long platform names and long pill labels (Thai) cannot collide
        scored = p.get("score") is not None
        score = ('%s<small>/100</small>' % fmt_num(p["score"])) if scored else ""
        na_pill = "" if scored else ('<span class="pill pill--info">%s</span>' % esc(L["not_scored"]))
        icon, _ = access_icon.get(p["crawler_access"], ("help", "na"))
        access = esc(L["access"].get(p["crawler_access"], p["crawler_access"]))
        note = ('<div class="pnote">%s</div>' % esc(p["note"])) if p.get("note") else ""
        chips.append('<div class="pc"><div class="pn">%s%s</div><div class="ps">%s</div>'
                     '<div class="pa">%s%s<span>%s: %s</span></div>%s</div>'
                     % (_dot(st, L), esc(p["label"]), score, na_pill, T.icon(icon), esc(L["crawler"]), access, note))
    legend = '<div class="legend"><span>%s %s</span><span>%s %s</span><span>%s %s</span><span>%s %s</span></div>' % (
        T.icon("circle-check"), esc(L["access"]["allowed"]), T.icon("circle-half"), esc(L["access"]["partial"]),
        T.icon("circle-x"), esc(L["access"]["blocked"]), T.icon("circle-dashed"), esc(L["access"]["unverifiable"]))
    return T.sh(L["platforms"], "%d" % len(plats)) + '<div class="plat">%s</div>%s' % ("".join(chips), legend)


def block_query_matrix(s, L, T):
    qm = s.get("query_matrix") or []
    if not qm:
        return ""
    cite_icon = {"yes": ("check", "ok"), "partial": ("minus", "warning"), "context": ("minus", "info"), "no": ("x", "critical")}
    rows = []
    for q in qm:
        icon, st = cite_icon.get(q["cited"], ("minus", "info"))
        pos = q["position"]
        pos_st = "ok" if pos == "#1" else "info" if pos.startswith("#2") else "warning" if pos.startswith("#") else "critical"
        pos_label = L["position_values"].get(pos, pos)
        sent = q.get("sentiment", "")
        rows.append('<tr><td class="q">%s</td><td>%s</td><td><span class="cite">%s%s</span></td>'
                    '<td><span class="pill pill--%s">%s</span></td><td class="sent--%s">%s</td></tr>'
                    % (esc('"%s"' % q["query"]), esc(q.get("platform", "")), T.icon(icon), esc(L["cited_values"].get(q["cited"], q["cited"])),
                       pos_st, esc(pos_label), esc(sent or "neutral"), esc(L["sentiment_values"].get(sent, sent))))
    head = '<tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>' % tuple(esc(L[k]) for k in ("query", "platform", "cited", "position", "sentiment"))
    return T.sh(L["query_matrix"], "%d" % len(qm)) + '<div class="tw"><table class="qm"><thead>%s</thead><tbody>%s</tbody></table></div>' % (head, "".join(rows))


def block_comparison(s, L, T):
    cp = s.get("comparison")
    if not cp:
        return ""
    has_ie = any(r.get("impact") or r.get("effort") for r in cp["rows"])
    head = "<th></th>" + "".join("<th>%s</th>" % esc(c) for c in cp["columns"])
    if has_ie:
        head += "<th>%s</th><th>%s</th>" % (esc(L["impact"]), esc(L["effort"]))
    rows = []
    for r in cp["rows"]:
        cells = "".join("<td>%s</td>" % esc(c) for c in r["cells"])
        if has_ie:
            cells += "<td>%s</td><td>%s</td>" % (
                _pill(L, {"high": "ok", "medium": "warning", "low": "neutral"}.get(r.get("impact", ""), "info"), L["impact_values"].get(r.get("impact", ""), r.get("impact", ""))) if r.get("impact") else "",
                ('<span class="tag">%s</span>' % esc(L["effort_values"].get(r.get("effort", ""), r.get("effort", "")))) if r.get("effort") else "")
        rows.append("<tr><td>%s</td>%s</tr>" % (esc(r["label"]), cells))
    rec = '<div class="rec"><b>%s%s</b>%s</div>' % (T.icon("bulb"), esc(L["recommendation"]), esc(cp["recommendation"]))
    return T.sh(L["comparison"]) + '<div class="tw"><table class="cmp"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>%s' % (head, "".join(rows), rec)


def block_deployables(s, L, T):
    deps = s.get("deployables") or []
    if not deps:
        return ""
    blocks = []
    for d in deps:
        path = ('<div class="path">%s %s</div>' % (esc(L["written_to"]), esc(d["path"]))) if d.get("path") else ""
        blocks.append('<div class="code"><div class="fh">%s<span>%s</span><span class="lang">%s</span>'
                      '<button type="button" class="btn copy" data-copy="1" title="%s">%s%s</button></div><pre>%s</pre>%s</div>'
                      % (T.icon("file"), esc(d["filename"]), esc(d["language"]), esc(L.get("copy", "Copy")), T.icon("copy"), esc(L.get("copy", "Copy")),
                         esc(d["content"].rstrip("\n")), path))
    return T.sh(L["deployables"], "%d" % len(deps)) + "".join(blocks)


def block_diff(s, L, T):
    d = s.get("diff")
    if not d:
        return ""
    delta = ""
    if d.get("score_before") is not None and d.get("score_after") is not None:
        delta = '<div class="sd">%s %s, %s %s</div>' % (esc(L["before"]), fmt_num(d["score_before"]), esc(L["after"]), fmt_num(d["score_after"]))
    return T.sh("%s: %s" % (L["diff"], d["label"])) + ('<div class="diff"><div class="d before"><b>%s</b>%s</div><div class="d after"><b>%s</b>%s</div>%s</div>'
                                                     % (esc(L["before"]), esc(d["before"]), esc(L["after"]), esc(d["after"]), delta))


def block_mockup(s, L, T):
    m = s.get("mockup")
    if not m:
        return ""
    srcs = "".join('<span class="tag">%s</span>' % esc(x) for x in m.get("cited_sources", []))
    cited = ""
    if m.get("client_cited") is not None:
        cited = _pill(L, "ok" if m["client_cited"] else "critical", L["cited_values"]["yes"] if m["client_cited"] else L["cited_values"]["no"])
    return T.sh("%s (%s)" % (L["mockup"], m["surface"])) + ('<div class="mock"><div class="mq">%s%s</div><div class="ma">%s</div><div class="ms">%s%s</div></div>'
                                                          % (T.icon("search"), esc(m["query"]), esc(m["answer_excerpt"]), srcs, cited))


def block_roles(s, L, T):
    roles = s.get("roles")
    if not roles:
        return ""
    cols = []
    for key, icon in (("executive", "user"), ("developer", "terminal"), ("content", "file")):
        if roles.get(key):
            cols.append('<div class="role"><h3>%s%s</h3><ul>%s</ul></div>' % (T.icon(icon), esc(L[key]), "".join("<li>%s</li>" % esc(x) for x in roles[key])))
    return T.sh(L["roles"]) + '<div class="roles">%s</div>' % "".join(cols)


def block_checklist(s, L, T):
    chk = s.get("checklist") or []
    if not chk:
        return ""
    items = []
    for c in chk:
        box = '<span class="box done">%s</span>' % T.icon("check", "i", "done") if c.get("done") else '<span class="box"></span>'
        extra = " ".join(esc(x) for x in [c.get("priority", ""), c.get("eta", "")] if x)
        items.append('<li>%s<span>%s</span><span class="own">%s</span>%s</li>' % (box, esc(c["task"]), esc(c["owner"]), (' <span class="tag">%s</span>' % extra) if extra else ""))
    return T.sh(L["checklist"], "%d" % len(chk)) + '<ul class="chk">%s</ul>' % "".join(items)


def block_transparency(s, L, T):
    t = s.get("transparency")
    if not t:
        return ""
    rows = []
    if t.get("crawled_at"):
        rows.append("<dt>%s</dt><dd>%s</dd>" % (esc(L["crawled_at"]), esc(t["crawled_at"])))
    for key in ("user_agents", "guidelines", "sources"):
        if t.get(key):
            rows.append("<dt>%s</dt><dd>%s</dd>" % (esc(L[key]), esc(", ".join(t[key]))))
    if t.get("could_not_verify"):
        rows.append("<dt>%s</dt><dd><ul>%s</ul></dd>" % (esc(L["could_not_verify"]), "".join("<li>%s</li>" % esc(x) for x in t["could_not_verify"])))
    return T.sh(L["transparency"]) + '<dl class="trans">%s</dl>' % "".join(rows)


def block_handoff(s, L, T):
    h = s["handoff"]
    fmts = "".join('<span class="tag">%s</span>' % esc(f) for f in h.get("formats", []))
    target = h.get("tier2_url") or h.get("tier2_path") or ""
    href = h.get("tier2_url") or ""
    # a real link whenever a target exists: the artifact URL, else the client-confined path
    # (relative links work when the card is saved next to the report; hosts intercept clicks)
    link = href or h.get("tier2_path", "")
    btn_open = '<a class="btn btn--primary" href="%s" data-path="%s">' % (esc(link), esc(h.get("tier2_path", ""))) if link else '<span class="btn btn--primary">'
    btn_close = "</a>" if link else "</span>"
    path = ('<div class="hp">%s</div>' % esc(target)) if target and not href else ""
    nexts = "".join('<button type="button" class="btn" title="%s" data-prompt="%s">%s%s</button>' % (esc(n["prompt"]), esc(n["prompt"]), esc(n["label"]), T.icon("arrow-right")) for n in s["next_steps"])
    return ('<div class="handoff"><div class="hh">%s%s</div><div class="fmts">%s</div>%s%s%s%s%s</div>'
            % (T.icon("file"), esc(L["handoff"]), fmts, path, btn_open, esc(h["tier2_label"]), btn_close, ""),
            T.sh(L["next_steps"]) + '<div class="next">%s</div>' % nexts)


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def body_blocks(s, L, T):
    mode = s["mode"]
    blocks = [block_header(s, L, T)]
    if mode == "quick_fact":
        blocks.append(block_quick(s, L, T))
        blocks.append(block_hero(s, L, T) if s.get("score") else "")
    else:
        blocks.append(block_hero(s, L, T))
    blocks.append(block_callout(s.get("root_cause"), L, T, "critical", L["root_cause"]))
    blocks.append(block_callout(s.get("key_risk"), L, T, "critical", L["key_risk"]))
    blocks.append(block_actions(s, L, T))
    blocks.append(block_steps(s, L, T))
    blocks.append(block_comparison(s, L, T))
    blocks.append(block_diff(s, L, T))
    blocks.append(block_dimensions(s, L, T))
    blocks.append(block_competitors(s, L, T))
    blocks.append(block_platforms(s, L, T))
    blocks.append(block_query_matrix(s, L, T))
    blocks.append(block_mockup(s, L, T))
    blocks.append(block_deployables(s, L, T))
    blocks.append(block_checklist(s, L, T))
    blocks.append(block_roles(s, L, T))
    handoff, nexts = block_handoff(s, L, T)
    blocks.append(handoff)
    blocks.append(nexts)
    blocks.append(block_transparency(s, L, T))
    return "\n".join(b for b in blocks if b)


def _icons():
    with open(os.path.join(WIDGET, "icons.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _css(name):
    with open(os.path.join(WIDGET, name), "r", encoding="utf-8") as f:
        return f.read()


# window.sendPrompt is the Claude widget tool bridge; window.rmPromptBridge is the hook an MCP Apps
# wrapper defines (ext-apps App -> ui/message) so the same fragment works as a ui:// resource.
COPY_SCRIPT = ('<script>(function(){var b=document.querySelectorAll("button[data-prompt]");for(var i=0;i<b.length;i++){'
               'b[i].addEventListener("click",function(e){var p=e.currentTarget.getAttribute("data-prompt");'
               'var s=window.sendPrompt||window.rmPromptBridge;if(s){s(p);return;}'
               'if(navigator.clipboard){navigator.clipboard.writeText(p);}});}'
               'var c=document.querySelectorAll("button[data-copy]");for(var j=0;j<c.length;j++){'
               'c[j].addEventListener("click",function(e){var pre=e.currentTarget.closest(".code").querySelector("pre");'
               'if(pre&&navigator.clipboard){navigator.clipboard.writeText(pre.textContent);}});}'
               'var o=document.querySelectorAll("a[data-path]");for(var k=0;k<o.length;k++){'
               'o[k].addEventListener("click",function(e){var s=window.sendPrompt||window.rmPromptBridge;if(s){e.preventDefault();s("Open the full report at "+e.currentTarget.getAttribute("data-path"));}});}})();</script>')


def render_standalone(s, L, modes):
    T = Theme("standalone", _icons())
    brand = s["meta"].get("brand") or {}
    style = ""
    if brand:
        parts = []
        if brand.get("primary"):
            parts.append("--brand-primary:%s" % esc(brand["primary"]))
        if brand.get("accent"):
            parts.append("--brand-accent:%s" % esc(brand["accent"]))
        if brand.get("accent_ink"):
            parts.append("--brand-accent-ink:%s" % esc(brand["accent_ink"]))
        style = ' style="%s"' % ";".join(parts)
    lang = s["meta"].get("lang", "en")
    title = esc(s["headline"]["title"])
    return ("<!DOCTYPE html>\n<html lang=\"%s\"%s>\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta name=\"color-scheme\" content=\"light dark\">\n<title>%s</title>\n<style>\n%s</style>\n</head>\n<body>\n<main class=\"rm-card\" data-mode=\"%s\">\n%s\n</main>\n%s\n</body>\n</html>\n"
            % (lang, style, title, _css("tier1-standalone.css"), esc(s["mode"]), body_blocks(s, L, T), COPY_SCRIPT))


def render_host_fragment(s, L, modes):
    T = Theme("host", _icons())
    brand = s["meta"].get("brand") or {}
    style = ""
    if brand.get("primary") or brand.get("accent"):
        parts = []
        if brand.get("primary"):
            parts.append("--rm-brand:%s" % esc(brand["primary"]))
        if brand.get("accent"):
            parts.append("--rm-accent:%s" % esc(brand["accent"]))
        style = ' style="%s"' % ";".join(parts)
    return ("<style>\n%s</style>\n<h2 class=\"sr-only\">%s</h2>\n<div class=\"rm-card\" data-mode=\"%s\"%s>\n%s\n</div>\n%s\n"
            % (_css("tier1-host.css"), esc(s.get("summary") or s["headline"]["title"]), esc(s["mode"]), style, body_blocks(s, L, T), COPY_SCRIPT))
