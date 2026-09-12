#!/usr/bin/env python3
"""
agent_readiness_lite.py - AI agent readiness checklist (semantic HTML and accessibility tree).

Lite edition for the BIQDADDY AI Visibility Course. Reports how well a site's
pages can be perceived and operated by autonomous web agents as a checklist of
14 checks, each PASS, FAIL, N/A, COULD NOT VERIFY or INFO. No points, no
weights, no site score, no gate: the learner reads the list and fixes what failed.

Agent perception classes (verified 2026-09; do not overclaim):
  accessibility tree  Playwright MCP, Claude in Chrome and the Anthropic browser
                      tool, Perplexity Comet, ChatGPT Atlas, Stagehand
  DOM plus screenshot Browser Use, Google Project Mariner
  screenshot only     OpenAI Operator / CUA, Anthropic computer use, Gemini
                      Computer Use, Amazon Nova Act, Edge Copilot Actions
Semantic HTML decides what the first two classes can see; the third class still
benefits from visible text and stable layout. No agent listens for aria-live
events and none times out on INP; they re-observe a moment after acting.

Two tiers, one honest list:
  static    requests + BeautifulSoup on every sampled page (cheap, all templates)
  rendered  Playwright Chromium on a few key pages when Playwright is installed:
            CDP Accessibility.getFullAXTree (unnamed interactive nodes),
            computed cursor:pointer generics, open dialogs, closed shadow hosts
Checks a tier could not run are reported as COULD NOT VERIFY; nothing is estimated.

This script owns the accessibility-tree and ARIA/form-semantics reading. It
cites, never re-judges: heading hierarchy (seo-heading-matrix-lite), SSR verdict
(aiso-technical-lite), robots access (aiso-crawlers-lite), llms.txt
(aiso-llmstxt-lite), JSON-LD (aiso-schema-lite).

Usage:
  python agent_readiness_lite.py https://example.com/ --scope representative_templates --output json
  python agent_readiness_lite.py https://example.com/ --urls urls.txt --render off --output md
  python agent_readiness_lite.py --html page.html --url https://example.com/ --output json
  python agent_readiness_lite.py --self-test
"""

import argparse
import datetime as dt
import json
import re
import sys
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None
try:
    from bs4 import BeautifulSoup, Comment
except ImportError:  # pragma: no cover
    sys.exit("Missing dependency: pip install beautifulsoup4 lxml")


# agent tool surface probes: (path, note). declared when 200 with JSON, or 401/405 (exists, needs auth or POST)
TOOL_PROBES = [
    ("/.well-known/ucp", "Google Universal Commerce Protocol discovery profile (Jan 2026)"),
    ("/.well-known/mcp/server-card.json", "MCP server card (SEP-1649, draft)"),
    ("/.well-known/mcp", "MCP discovery (SEP-1960, draft)"),
    ("/wp-json/mcp/mcp-adapter-default-server", "WordPress MCP Adapter (core 6.9 Abilities API, official plugin Feb 2026)"),
    ("/wp-json/wp/v2/abilities", "WordPress Abilities API listing (6.9+)"),
    ("/api/mcp", "Shopify Storefront MCP"),
    ("/.well-known/api-catalog", "API catalog (RFC 9727)"),
    ("/.well-known/oauth-authorization-server", "OAuth authorization server metadata (RFC 8414)"),
    ("/.well-known/oauth-protected-resource", "OAuth protected resource metadata (RFC 9728)"),
    ("/.well-known/agent-card.json", "A2A agent card (v1.0, Mar 2026)"),
    ("/.well-known/agent.json", "A2A agent card (legacy path)"),
    ("/openapi.json", "OpenAPI document"),
    ("/.well-known/openapi.json", "OpenAPI document (well-known)"),
    ("/ask", "NLWeb ask endpoint (Microsoft, May 2025)"),
    ("/.well-known/ai-plugin.json", "OBSOLETE: ChatGPT plugin manifest, plugins ended 2024-04-09"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "th,en;q=0.9",
}
TIMEOUT = 20
SCOPE_CAPS = {"homepage_only": (1, 1), "representative_templates": (60, 12), "full_site_crawl": (500, 18)}

ARIA_ROLES = set("""alert alertdialog application article banner blockquote button caption cell checkbox code
columnheader combobox complementary contentinfo definition deletion dialog directory document emphasis feed
figure form generic grid gridcell group heading img insertion link list listbox listitem log main marquee math
menu menubar menuitem menuitemcheckbox menuitemradio meter navigation none note option paragraph presentation
progressbar radio radiogroup region row rowgroup rowheader scrollbar search searchbox separator slider
spinbutton status strong subscript superscript switch tab table tablist tabpanel term textbox time timer
toolbar tooltip tree treegrid treeitem""".split())
INTERACTIVE_ROLES = {"button", "link", "checkbox", "radio", "switch", "tab", "menuitem", "menuitemcheckbox",
                     "menuitemradio", "combobox", "slider", "spinbutton", "textbox", "searchbox", "option",
                     "treeitem", "listbox"}
AUTOCOMPLETE_TOKENS = set("""name honorific-prefix given-name additional-name family-name honorific-suffix nickname
username new-password current-password one-time-code organization-title organization street-address address-line1
address-line2 address-line3 address-level4 address-level3 address-level2 address-level1 country country-name
postal-code cc-name cc-given-name cc-additional-name cc-family-name cc-number cc-exp cc-exp-month cc-exp-year
cc-csc cc-type transaction-currency transaction-amount language bday bday-day bday-month bday-year sex url photo
tel tel-country-code tel-national tel-area-code tel-local tel-local-prefix tel-local-suffix tel-extension email
impp off on""".split())
PRIMARY_TOKENS = {"checkout", "addtocart", "cart", "buy", "purchase", "book", "booking", "reserve", "pay", "payment", "submit", "order", "subscribe", "enquire", "enquiry", "inquiry"}
IDENTITY_FIELD_RE = re.compile(r"e-?mail|phone|tel|mobile|first|last|full|name|address|zip|postal|city|country|province|card|company|organization", re.I)
TEMPLATE_RULES = [
    ("checkout", re.compile(r"/(cart|checkout|booking|book|reserve|order|payment)(/|$)", re.I)),
    ("contact", re.compile(r"/(contact|enquir|inquir|quote|appointment)", re.I)),
    ("article", re.compile(r"/(blog|article|news|post|knowledge|guide|tips)(/|$)", re.I)),
    ("category", re.compile(r"/(category|categories|collections?|tag|archive)(/|$)", re.I)),
    ("product", re.compile(r"/(product|products|shop|item|sku|p)(/|$)", re.I)),
    ("service", re.compile(r"/(service|services|treatment|solutions?|program)(/|$)", re.I)),
]
CHECK_LABELS = {
    "CTL-01": "Clickable generics (div or span with a click handler and no role)",
    "CTL-02": "ARIA conformance (valid roles, resolvable IDREFs)",
    "CTL-03": "Interactive controls carry an accessible name",
    "CTL-04": "Controls show visible text or a labelled icon",
    "FRM-01": "Form fields have a programmatic label",
    "FRM-02": "Identity fields carry valid autocomplete tokens",
    "FRM-03": "Field name, type and required parity",
    "STR-01": "Landmark skeleton (one main, navigation, banner, contentinfo)",
    "STR-02": "Content sits inside landmarks",
    "DYN-01": "Live region for status messages",
    "DYN-02": "Modal dialogs use dialog or aria-modal with containment",
    "DYN-03": "No closed Shadow DOM around interactive content",
    "ACC-01": "Headless render integrity (200, real DOM, no bot wall)",
    "ACC-02": "Agent tool surface (informational)",
}



# ---------------------------------------------------------------------------
# fetch and discovery
# ---------------------------------------------------------------------------

def _session():
    if requests is None:
        sys.exit("Missing dependency: pip install requests")
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _get(session, url):
    try:
        return session.get(url, timeout=TIMEOUT, allow_redirects=True)
    except Exception:
        return None


def classify_template(url):
    path = urlparse(url).path or "/"
    if path in ("", "/"):
        return "home"
    for name, rx in TEMPLATE_RULES:
        if rx.search(path):
            return name
    return "page"


def discover_urls(session, start_url, static_cap):
    """Homepage plus sitemap URLs plus homepage nav links, sampled per template."""
    parsed = urlparse(start_url)
    base = "%s://%s" % (parsed.scheme, parsed.netloc)
    found = [start_url]
    sm = _get(session, base + "/sitemap.xml")
    locs = []
    if sm is not None and sm.status_code == 200:
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm.text)
        # sitemap index: follow child sitemaps (cap 5)
        children = [l for l in locs if l.endswith(".xml")][:5]
        for child in children:
            r = _get(session, child)
            if r is not None and r.status_code == 200:
                locs.extend(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text))
    home = _get(session, start_url)
    if home is not None and home.status_code == 200:
        soup = BeautifulSoup(home.text, "lxml")
        for a in soup.find_all("a", href=True):
            href = urljoin(start_url, a["href"])
            if urlparse(href).netloc == parsed.netloc:
                locs.append(href.split("#")[0])
    seen = set(found)
    per_template = {}
    for u in locs:
        if u.endswith(".xml") or u in seen or not u.startswith(base):
            continue
        t = classify_template(u)
        per_template.setdefault(t, [])
        if len(per_template[t]) >= max(2, static_cap // 6):
            continue
        per_template[t].append(u)
        seen.add(u)
        found.append(u)
        if len(found) >= static_cap:
            break
    return found


# ---------------------------------------------------------------------------
# static inspection
# ---------------------------------------------------------------------------

def _soup(html):
    soup = BeautifulSoup(html or "", "lxml")
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()
    return soup


def _is_hidden(el):
    style = (el.get("style") or "").replace(" ", "").lower()
    return el.get("hidden") is not None or el.get("aria-hidden") == "true" or "display:none" in style or "visibility:hidden" in style


def _visible_text(el):
    parts = []
    for node in el.descendants:
        if isinstance(node, str):
            parent = node.parent
            skip = False
            while parent is not None and parent is not el:
                if getattr(parent, "get", None) and parent.get("aria-hidden") == "true":
                    skip = True
                    break
                parent = parent.parent
            if not skip:
                parts.append(node.strip())
    return " ".join(p for p in parts if p).strip()


def _accessible_name(el, soup):
    if el.get("aria-label", "").strip():
        return el["aria-label"].strip()
    if el.get("aria-labelledby"):
        names = []
        for ref in el["aria-labelledby"].split():
            target = soup.find(id=ref)
            if target:
                names.append(target.get_text(" ", strip=True))
        if any(names):
            return " ".join(n for n in names if n)
    if el.name in ("input", "select", "textarea"):
        iid = el.get("id")
        if iid:
            lab = soup.find("label", attrs={"for": iid})
            if lab and lab.get_text(strip=True):
                return lab.get_text(" ", strip=True)
        wrap = el.find_parent("label")
        if wrap and wrap.get_text(strip=True):
            return wrap.get_text(" ", strip=True)
        if el.name == "input" and el.get("type", "").lower() in ("submit", "button", "reset", "image"):
            return (el.get("value") or el.get("alt") or "").strip()
    text = _visible_text(el)
    if text:
        return text
    for img in el.find_all("img"):
        if (img.get("alt") or "").strip():
            return img["alt"].strip()
    for svg in el.find_all("svg"):
        t = svg.find("title")
        if t and t.get_text(strip=True):
            return t.get_text(strip=True)
    return (el.get("title") or "").strip()


def inspect_static(html, url):
    soup = _soup(html)
    body = soup.find("body") or soup
    out = {"url": url, "template": classify_template(url)}
    ids = {el.get("id") for el in soup.find_all(id=True)}

    # STR-01 landmarks
    mains = [m for m in soup.find_all(["main"]) + soup.find_all(attrs={"role": "main"}) if not _is_hidden(m)]
    navs = soup.find_all("nav") + soup.find_all(attrs={"role": "navigation"})
    banners = [h for h in soup.find_all("header") if h.find_parent(["article", "section", "main", "aside"]) is None] + soup.find_all(attrs={"role": "banner"})
    footers = [f for f in soup.find_all("footer") if f.find_parent(["article", "section", "main", "aside"]) is None] + soup.find_all(attrs={"role": "contentinfo"})
    out["landmarks"] = {"main": len(set(id(x) for x in mains)), "navigation": len(navs), "banner": len(banners), "contentinfo": len(footers)}

    # STR-02 landmark coverage
    content_nodes = body.find_all(["p", "li", "h1", "h2", "h3", "h4", "table", "figure"])
    covered = 0
    for n in content_nodes:
        if n.find_parent(["main", "nav", "header", "footer", "aside", "section", "article", "form"]) is not None or n.find_parent(attrs={"role": re.compile(r"^(main|navigation|banner|contentinfo|complementary|region|form|search)$")}) is not None:
            covered += 1
    out["content_nodes"] = len(content_nodes)
    out["content_covered"] = covered

    # controls
    controls = []
    for el in body.find_all(["button", "a", "select", "textarea", "summary"]) + body.find_all("input"):
        if el.name == "a" and not el.get("href"):
            continue
        if el.name == "input" and (el.get("type") or "text").lower() == "hidden":
            continue
        if _is_hidden(el):
            continue
        controls.append(el)
    for el in body.find_all(attrs={"role": True}):
        if el.get("role", "").lower() in INTERACTIVE_ROLES and el.name not in ("button", "a", "input", "select", "textarea") and not _is_hidden(el):
            controls.append(el)
    unnamed = []
    no_affordance = []
    for el in controls:
        if el.name in ("input", "select", "textarea") and (el.get("type") or "text").lower() not in ("submit", "button", "reset", "image"):
            continue  # fields are judged by FRM-01
        name = _accessible_name(el, soup)
        if not name:
            unnamed.append(_selector(el))
        elif not _visible_text(el) and not any((img.get("alt") or "").strip() for img in el.find_all("img")) and not el.get("aria-label") \
                and not (el.name == "input" and (el.get("value") or el.get("alt") or "").strip()):
            no_affordance.append(_selector(el))
    out["controls_total"] = len([c for c in controls if not (c.name in ("input", "select", "textarea") and (c.get("type") or "text").lower() not in ("submit", "button", "reset", "image"))])
    out["controls_unnamed"] = unnamed
    out["controls_no_affordance"] = no_affordance

    # primary action gate: submit buttons and checkout-like controls
    primary_unnamed = []
    for el in controls:
        tokens = set(re.split(r"[^a-z0-9]+", (" ".join(el.get("class", [])) + " " + (el.get("id") or "")).lower()))
        is_primary = (el.name == "button" and (el.get("type") or "submit").lower() == "submit") or \
                     (el.name == "input" and (el.get("type") or "").lower() == "submit") or \
                     bool(tokens & PRIMARY_TOKENS)
        if is_primary and not _accessible_name(el, soup):
            primary_unnamed.append(_selector(el))
    out["primary_unnamed"] = primary_unnamed

    # CTL-01 clickable generics (static approximation: onclick attribute or cursor:pointer inline style)
    generics = []
    for el in body.find_all(["div", "span", "li", "img", "i"]):
        if el.get("role") or el.get("tabindex") is not None:
            continue
        style = (el.get("style") or "").replace(" ", "").lower()
        if el.get("onclick") or "cursor:pointer" in style:
            if el.find(["a", "button", "input", "select", "textarea"]) is None and el.find(attrs={"role": True}) is None:
                generics.append(_selector(el))
    out["clickable_generics"] = generics
    out["interactive_total"] = out["controls_total"] + len(generics)

    # CTL-02 aria conformance
    aria_violations = []
    for el in body.find_all(attrs={"role": True}):
        for r in el.get("role", "").split():
            if r.lower() not in ARIA_ROLES:
                aria_violations.append("%s role=%s" % (_selector(el), r))
    for attr in ("aria-labelledby", "aria-describedby", "aria-controls", "aria-owns", "aria-activedescendant"):
        for el in body.find_all(attrs={attr: True}):
            for ref in el.get(attr, "").split():
                if ref not in ids:
                    aria_violations.append("%s %s=%s unresolved" % (_selector(el), attr, ref))
    out["aria_violations"] = aria_violations

    # FRM-01..03 forms
    fields = []
    for el in body.find_all(["input", "select", "textarea"]):
        t = (el.get("type") or "text").lower()
        if el.name == "input" and t in ("hidden", "submit", "button", "image", "reset"):
            continue
        if _is_hidden(el):
            continue
        fields.append(el)
    unlabeled, placeholder_only, identity, identity_missing_ac, invalid_ac, type_misfit, required_mismatch, nameless = [], [], [], [], [], [], [], []
    for el in fields:
        iid = el.get("id")
        labelled = bool(iid and soup.find("label", attrs={"for": iid})) or bool(el.find_parent("label")) or bool(el.get("aria-label", "").strip()) or bool(el.get("aria-labelledby"))
        if not labelled:
            if (el.get("placeholder") or "").strip():
                placeholder_only.append(_selector(el))
            else:
                unlabeled.append(_selector(el))
        t = (el.get("type") or "text").lower()
        hint = " ".join([el.get("name") or "", iid or "", el.get("placeholder") or "", el.get("autocomplete") or ""])
        ac = (el.get("autocomplete") or "").strip().lower()
        if ac:
            toks = [x for x in ac.split() if x not in ("shipping", "billing") and not x.startswith("section-")]
            if not all(x in AUTOCOMPLETE_TOKENS or x in ("home", "work", "mobile", "fax", "pager") for x in toks):
                invalid_ac.append("%s autocomplete=%s" % (_selector(el), ac))
        if t in ("email", "tel", "password") or IDENTITY_FIELD_RE.search(hint):
            identity.append(_selector(el))
            if not ac or ac == "off":
                identity_missing_ac.append(_selector(el))
        if t == "text" and re.search(r"e-?mail", hint, re.I):
            type_misfit.append("%s should be type=email" % _selector(el))
        if t == "text" and re.search(r"phone|tel|mobile", hint, re.I):
            type_misfit.append("%s should be type=tel" % _selector(el))
        if not (el.get("name") or "").strip():
            nameless.append(_selector(el))
        if el.get("required") is not None and el.get("aria-required") == "false":
            required_mismatch.append(_selector(el))
    out["fields_total"] = len(fields)
    out["fields_unlabeled"] = unlabeled
    out["fields_placeholder_only"] = placeholder_only
    out["identity_fields"] = identity
    out["identity_missing_autocomplete"] = identity_missing_ac
    out["autocomplete_invalid"] = invalid_ac
    out["type_misfit"] = type_misfit
    out["fields_nameless"] = nameless
    out["required_mismatch"] = required_mismatch

    # DYN-01 live regions and action pattern
    live = body.find_all(attrs={"aria-live": True}) + body.find_all(attrs={"role": re.compile(r"^(status|alert|log)$")})
    action_pattern = bool(body.find("form")) or bool(re.search(r"add-to-cart|addtocart|cart|booking|subscribe", html or "", re.I))
    out["live_regions"] = len(live)
    out["action_pattern"] = action_pattern

    # DYN-02 modal patterns
    native_dialogs = body.find_all("dialog")
    role_dialogs = body.find_all(attrs={"role": re.compile(r"^(dialog|alertdialog)$")})
    div_modals = [el for el in body.find_all(["div", "section"], class_=re.compile(r"modal|popup|lightbox|overlay", re.I)) if not el.get("role") and el.find_parent("dialog") is None]
    out["dialogs"] = {"native": len(native_dialogs), "role": len(role_dialogs), "div_modals": len(div_modals),
                      "aria_modal": len([d for d in role_dialogs if d.get("aria-modal") == "true"]),
                      "unnamed": len([d for d in native_dialogs + role_dialogs if not d.get("aria-label") and not d.get("aria-labelledby")])}

    # DYN-03 closed shadow DOM (static signals)
    closed = len(body.find_all("template", attrs={"shadowrootmode": "closed"})) + len(re.findall(r"attachShadow\(\s*\{\s*mode\s*:\s*['\"]closed", html or ""))
    out["shadow_closed_signals"] = closed
    out["custom_elements"] = len([el for el in body.find_all() if "-" in el.name])

    # citations only
    out["h1_count"] = len(soup.find_all("h1"))
    out["tables_without_th"] = len([t for t in body.find_all("table") if not t.find("th") and t.get("role") != "presentation"])
    out["webmcp_signal"] = bool(re.search(r"(?:navigator|document)\.modelContext", html or ""))
    out["dom_elements"] = len(body.find_all())
    return out


def _selector(el):
    parts = [el.name]
    if el.get("id"):
        parts.append("#" + el["id"])
    elif el.get("class"):
        parts.append("." + ".".join(el.get("class")[:2]))
    text = _visible_text(el)[:30] if el.name in ("a", "button") else ""
    s = "".join(parts)
    return s + (' "%s"' % text if text else "")


# ---------------------------------------------------------------------------
# rendered inspection (Playwright optional)
# ---------------------------------------------------------------------------

def playwright_available():
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except Exception:
        return False


AX_JS = """() => {
  const generics = [];
  const all = document.querySelectorAll('div, span, li, img, i, svg');
  for (const el of all) {
    if (el.closest('a, button, input, select, textarea, [role]')) continue;
    const cs = getComputedStyle(el);
    if (cs.cursor === 'pointer' && !el.querySelector('a, button, input, [role]')) {
      generics.push((el.tagName.toLowerCase()) + (el.id ? '#' + el.id : (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).slice(0,2).join('.') : '')));
    }
  }
  const closedHosts = [];
  for (const el of document.querySelectorAll('*')) {
    if (el.tagName.includes('-') && customElements.get(el.tagName.toLowerCase()) && el.shadowRoot === null) closedHosts.push(el.tagName.toLowerCase());
  }
  const dialogs = [];
  for (const d of document.querySelectorAll('dialog[open], [role=dialog], [role=alertdialog]')) {
    const cs = getComputedStyle(d);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    dialogs.push({tag: d.tagName.toLowerCase(), modal: d.getAttribute('aria-modal') === 'true' || (d.tagName === 'DIALOG' && d.matches(':modal')), named: !!(d.getAttribute('aria-label') || d.getAttribute('aria-labelledby')), focusInside: d.contains(document.activeElement)});
  }
  return {generics: generics.slice(0, 200), closedHosts: closedHosts.slice(0, 50), dialogs, domElements: document.querySelectorAll('*').length, title: document.title};
}"""


def inspect_rendered(url, timeout_ms=45000):
    from playwright.sync_api import sync_playwright  # type: ignore
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, user_agent=HEADERS["User-Agent"], locale="th-TH")
        page = ctx.new_page()
        resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(1000)
        status = resp.status if resp else None
        js = page.evaluate(AX_JS)
        client = ctx.new_cdp_session(page)
        tree = client.send("Accessibility.getFullAXTree")
        nodes = tree.get("nodes", [])
        live = [n for n in nodes if not n.get("ignored")]
        roles = {}
        unnamed_interactive = []
        for n in live:
            role = (n.get("role") or {}).get("value", "")
            roles[role] = roles.get(role, 0) + 1
            if role in INTERACTIVE_ROLES:
                name = ((n.get("name") or {}).get("value") or "").strip()
                if not name:
                    unnamed_interactive.append(role)
        generic = roles.get("generic", 0)
        interactive = sum(v for k, v in roles.items() if k in INTERACTIVE_ROLES)
        # bot wall heuristics
        bot_wall = bool(re.search(r"just a moment|verify you are human|access denied|attention required", (js.get("title") or "") + page.content()[:3000], re.I))
        result = {
            "status": status,
            "dom_elements": js["domElements"],
            "ax_nodes_total": len(nodes),
            "ax_nodes_live": len(live),
            "ax_generic": generic,
            "ax_generic_share": round(100.0 * generic / len(live), 1) if live else None,
            "ax_interactive": interactive,
            "ax_unnamed_interactive": len(unnamed_interactive),
            "ax_unnamed_roles": unnamed_interactive[:50],
            "clickable_generics_rendered": js["generics"],
            "closed_shadow_hosts": js["closedHosts"],
            "dialogs_rendered": js["dialogs"],
            "bot_wall": bot_wall,
        }
        browser.close()
        return result




# ---------------------------------------------------------------------------
# checklist (PASS / FAIL / N/A / COULD NOT VERIFY / INFO, no points)
# ---------------------------------------------------------------------------

def checklist_page(st, rd=None, tools=None):
    """Return the page checklist. st = static inspection, rd = rendered inspection or None."""
    checks = {}
    defects = []
    cnv = []

    def add(cid, verdict, note):
        checks[cid] = {"verdict": verdict, "note": note, "label": CHECK_LABELS[cid]}

    if st.get("dom_elements", 0) < 8 or (st["controls_total"] == 0 and st["fields_total"] == 0 and st["content_nodes"] == 0):
        return {"url": st["url"], "template": st["template"], "checks": {}, "defects": [],
                "could_not_verify": ["static tier: page has no usable DOM (empty shell, bot wall or client-rendered without a server response); rendered tier or a browser fetch is required"],
                "unnamed": 0, "unlabeled": 0, "rendered": rd is not None, "passed": 0, "failed": 0, "applicable": 0}
    # CTL-01 clickable generics
    gen = st["clickable_generics"]
    if rd is not None:
        gen = list(dict.fromkeys(gen + rd.get("clickable_generics_rendered", [])))
    add("CTL-01", "PASS" if not gen else "FAIL", "%d clickable generics among %d interactive elements (%s)" % (len(gen), st["controls_total"] + len(gen), "rendered" if rd else "static approximation"))
    for s in gen[:20]:
        defects.append({"check": "CTL-01", "selector": s, "fix": "Replace the clickable div or span with a button (or an a href for navigation) so the role and name reach the accessibility tree"})
    # CTL-02 aria
    v = len(st["aria_violations"])
    add("CTL-02", "PASS" if v == 0 else "FAIL", "%d ARIA conformance issues" % v)
    for s in st["aria_violations"][:20]:
        defects.append({"check": "CTL-02", "selector": s, "fix": "Use a valid ARIA 1.2 role and make every aria-* IDREF point at an existing id"})
    # CTL-03 named controls
    unnamed = st["controls_unnamed"]
    if rd is not None and rd.get("ax_interactive"):
        bad = rd["ax_unnamed_interactive"]
        note = "%d of %d interactive AX nodes have no accessible name (browser accname)" % (bad, rd["ax_interactive"])
    else:
        bad = len(unnamed)
        note = "%d of %d controls have no accessible name (static approximation)" % (bad, st["controls_total"])
    add("CTL-03", "PASS" if bad == 0 else "FAIL", note)
    for s in unnamed[:20]:
        defects.append({"check": "CTL-03", "selector": s, "fix": "Give the control a name: visible text, aria-label, or an img alt inside it; decorative icons get aria-hidden=true"})
    # CTL-04 affordance
    add("CTL-04", "PASS" if not st["controls_no_affordance"] else "FAIL", "%d controls rely on an unlabelled icon" % len(st["controls_no_affordance"]))
    # forms
    if st["fields_total"] > 0:
        bad = len(st["fields_unlabeled"]) + len(st["fields_placeholder_only"])
        add("FRM-01", "PASS" if bad == 0 else "FAIL", "%d unlabeled, %d placeholder-only of %d fields" % (len(st["fields_unlabeled"]), len(st["fields_placeholder_only"]), st["fields_total"]))
        for s in st["fields_unlabeled"][:20]:
            defects.append({"check": "FRM-01", "selector": s, "fix": "Add a label for=id pair (or aria-labelledby); placeholder text disappears once the agent types"})
        for s in st["fields_placeholder_only"][:20]:
            defects.append({"check": "FRM-01", "selector": s, "fix": "Placeholder is the only name; add a visible label bound with for=id"})
        if st["identity_fields"]:
            bad = len(st["identity_missing_autocomplete"]) + len(st["autocomplete_invalid"])
            add("FRM-02", "PASS" if bad == 0 else "FAIL", "%d of %d identity fields lack autocomplete; %d invalid tokens" % (len(st["identity_missing_autocomplete"]), len(st["identity_fields"]), len(st["autocomplete_invalid"])))
            for s in st["identity_missing_autocomplete"][:20]:
                defects.append({"check": "FRM-02", "selector": s, "fix": "Add the WHATWG autocomplete token (name, email, tel, street-address, postal-code, cc-number) so agents and browsers fill it without guessing"})
        else:
            add("FRM-02", "N/A", "no identity fields on this page")
        bad = len(st["type_misfit"]) + len(st["fields_nameless"]) + len(st["required_mismatch"])
        add("FRM-03", "PASS" if bad == 0 else "FAIL", "%d type or name or required issues" % bad)
        for s in st["type_misfit"][:10]:
            defects.append({"check": "FRM-03", "selector": s, "fix": "Set the input type to match the data (email, tel) and inputmode where relevant"})
    else:
        for cid in ("FRM-01", "FRM-02", "FRM-03"):
            add(cid, "N/A", "no form fields on this page")
    # structure
    lm = st["landmarks"]
    ok = lm["main"] == 1 and lm["navigation"] >= 1 and lm["banner"] >= 1 and lm["contentinfo"] >= 1
    add("STR-01", "PASS" if ok else "FAIL", "main=%d navigation=%d banner=%d contentinfo=%d" % (lm["main"], lm["navigation"], lm["banner"], lm["contentinfo"]))
    if not ok:
        defects.append({"check": "STR-01", "selector": "body", "fix": "Wrap the primary content in exactly one main element; add nav, header and footer landmarks"})
    if st["content_nodes"]:
        outside = st["content_nodes"] - st["content_covered"]
        add("STR-02", "PASS" if outside == 0 else "FAIL", "%d of %d content nodes inside a landmark" % (st["content_covered"], st["content_nodes"]))
        if outside:
            defects.append({"check": "STR-02", "selector": "content outside landmarks", "fix": "Move every content block inside main, nav, header, footer or aside so agents can locate it by landmark"})
    else:
        add("STR-02", "N/A", "no content nodes")
    # dynamic
    if st["action_pattern"]:
        add("DYN-01", "PASS" if st["live_regions"] else "FAIL", "%d live regions with a state-changing action present" % st["live_regions"])
        if not st["live_regions"]:
            defects.append({"check": "DYN-01", "selector": "form or cart action", "fix": "Announce results in a role=status (polite) or role=alert (assertive) container so the message carries a role in the accessibility tree; agents do not listen for live regions, they re-observe a moment later, so the message must also stay in the DOM long enough to be seen"})
    else:
        add("DYN-01", "N/A", "no state-changing action detected")
    d = st["dialogs"]
    rendered_dialogs = rd.get("dialogs_rendered", []) if rd else []
    if d["native"] or d["role"] or d["div_modals"] or rendered_dialogs:
        bad = d["div_modals"] + len([x for x in rendered_dialogs if not x.get("modal")])
        add("DYN-02", "PASS" if bad == 0 else "FAIL", "native=%d role=%d div_modals=%d unnamed=%d rendered_open=%d" % (d["native"], d["role"], d["div_modals"], d["unnamed"], len(rendered_dialogs)))
        if bad:
            defects.append({"check": "DYN-02", "selector": "div.modal", "fix": "Use the dialog element with showModal() (or role=dialog plus aria-modal=true and inert on the background) so focus and perception stay inside"})
    else:
        add("DYN-02", "N/A", "no modal pattern on this page")
    closed = st["shadow_closed_signals"] + (len(rd.get("closed_shadow_hosts", [])) if rd else 0)
    if st["custom_elements"] or closed:
        add("DYN-03", "PASS" if closed == 0 else "FAIL", "%d closed shadow hosts among %d custom elements" % (closed, st["custom_elements"]))
        if closed:
            defects.append({"check": "DYN-03", "selector": "custom element", "fix": "Open the shadow root (mode open) or expose the control through ElementInternals so its role and name are readable"})
    else:
        add("DYN-03", "N/A", "no custom elements")
    # render integrity
    if rd is not None:
        ok = rd.get("status") == 200 and rd.get("dom_elements", 0) >= 50 and not rd.get("bot_wall")
        add("ACC-01", "PASS" if ok else "FAIL", "status=%s dom=%s bot_wall=%s" % (rd.get("status"), rd.get("dom_elements"), rd.get("bot_wall")))
        if not ok:
            defects.append({"check": "ACC-01", "selector": "page", "fix": "Headless Chromium did not get a real page (bot wall or empty DOM); whitelist documented agent user agents or fix the render"})
    else:
        add("ACC-01", "COULD NOT VERIFY", "rendered tier not run")
        cnv.append("ACC-01 headless render integrity (Playwright not run)")
        if not st["clickable_generics"]:
            cnv.append("CTL-01 rendered click listeners (static approximation only)")
    declared = sorted(k for k, v in (tools or {}).items() if v == "declared")
    obsolete = sorted(k for k, v in (tools or {}).items() if v == "obsolete")
    add("ACC-02", "INFO", "webmcp=%s declared=%s obsolete=%s probed=%d" % (st.get("webmcp_signal"), ",".join(declared) or "none", ",".join(obsolete) or "none", len(tools or {})))
    verdicts = [c["verdict"] for c in checks.values()]
    return {"url": st["url"], "template": st["template"], "checks": checks, "defects": defects, "could_not_verify": cnv,
            "passed": verdicts.count("PASS"), "failed": verdicts.count("FAIL"),
            "applicable": verdicts.count("PASS") + verdicts.count("FAIL"),
            "unnamed": rd["ax_unnamed_interactive"] if rd and rd.get("ax_interactive") else len(st["controls_unnamed"]),
            "unlabeled": len(st["fields_unlabeled"]) + len(st["fields_placeholder_only"]),
            "rendered": rd is not None}


def probe_tools(session, base):
    """Agent tool surface inventory (zero weight). declared = 200 with JSON, or 401/405 (exists,
    needs auth or POST); obsolete = a dead standard still served; markdown = content negotiation."""
    out = {}
    for path, note in TOOL_PROBES:
        r = _get(session, base + path)
        if r is None:
            out[path] = "not declared"
            continue
        ctype = (r.headers.get("Content-Type") or "").lower()
        # 401/405 prove the route exists only when the server answers like an API (JSON body,
        # WWW-Authenticate or Allow header); an HTML 401 from a WAF is not a declaration
        api_like = "json" in ctype or bool(r.headers.get("WWW-Authenticate")) or bool(r.headers.get("Allow"))
        exists = (r.status_code == 200 and "json" in ctype) or (r.status_code in (401, 405) and api_like)
        if path == "/ask":
            exists = (r.status_code == 405 and api_like) or (r.status_code == 200 and "json" in ctype)
        if exists and note.startswith("OBSOLETE"):
            out[path] = "obsolete"
        else:
            out[path] = "declared" if exists else "not declared"
    try:
        r = session.get(base + "/", headers=dict(HEADERS, Accept="text/markdown, text/html;q=0.5"), timeout=TIMEOUT, allow_redirects=True)
        out["accept:text/markdown"] = "declared" if r is not None and (r.headers.get("Content-Type") or "").lower().startswith("text/markdown") else "not declared"
    except Exception:
        out["accept:text/markdown"] = "not declared"
    return out




def audit(start_url=None, urls=None, scope="representative_templates", render="auto", html=None):
    session = _session()
    static_cap, render_cap = SCOPE_CAPS.get(scope, SCOPE_CAPS["representative_templates"])
    fetched_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if html is not None:
        pages_src = [(start_url or "file://local", html)]
        tools = {}
    else:
        targets = urls or discover_urls(session, start_url, static_cap)
        pages_src = []
        for u in targets[:static_cap]:
            r = _get(session, u)
            if r is not None and r.status_code == 200 and "html" in (r.headers.get("Content-Type") or "text/html"):
                pages_src.append((r.url, r.text))
        parsed = urlparse(start_url)
        tools = probe_tools(session, "%s://%s" % (parsed.scheme, parsed.netloc))
    use_render = render == "on" or (render == "auto" and playwright_available() and html is None)
    method = "static tier on %d pages" % len(pages_src)
    if use_render:
        method += "; rendered tier (Playwright Chromium, CDP Accessibility.getFullAXTree) on up to %d key pages" % render_cap
    else:
        method += "; rendered tier not run (%s)" % ("Playwright not installed" if not playwright_available() else "disabled")
    results = []
    rendered_done = 0
    seen_templates = {}
    for url, page_html in pages_src:
        st = inspect_static(page_html, url)
        rd = None
        if use_render and rendered_done < render_cap and seen_templates.get(st["template"], 0) < 3:
            try:
                rd = inspect_rendered(url)
                rendered_done += 1
                seen_templates[st["template"]] = seen_templates.get(st["template"], 0) + 1
            except Exception as e:  # never estimate: record and continue static
                rd = None
                st["render_error"] = str(e)[:200]
        results.append(checklist_page(st, rd, tools))
    cnv = sorted(set(x for r in results for x in r["could_not_verify"]))
    failing = {}
    for r in results:
        for cid, c in r["checks"].items():
            if c["verdict"] == "FAIL":
                failing[cid] = failing.get(cid, 0) + 1
    return {
        "site": {
            "start_url": start_url, "scope": scope, "fetched_at": fetched_at, "pages_audited": len(results),
            "checks_passed": sum(r["passed"] for r in results), "checks_failed": sum(r["failed"] for r in results),
            "checks_applicable": sum(r["applicable"] for r in results),
            "failing_checks_by_pages": dict(sorted(failing.items(), key=lambda kv: -kv[1])),
            "method_note": method + ". Static checks are labelled approximations where the accessibility tree was not captured. This is an agent-readiness checklist, not WCAG conformance. Heading hierarchy, SSR, robots and JSON-LD are cited from their owning skills.",
            "could_not_verify": cnv,
            "tools": tools,
            "checks": CHECK_LABELS,
        },
        "pages": results,
    }


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

def format_md(result):
    site = result["site"]
    lines = ["# AI agent readiness checklist (accessibility tree)", "", "Start URL: %s" % site["start_url"],
             "Scope: %s, pages audited: %d, fetched %s" % (site["scope"], site["pages_audited"], site["fetched_at"]), ""]
    lines.append("Checks passed: %d of %d applicable across all pages (no score, no weights)" % (site["checks_passed"], site["checks_applicable"]))
    lines.append("")
    lines.append("| URL | Template | Passed | Failed | Unnamed controls | Unlabeled fields |")
    lines.append("|---|---|---|---|---|---|")
    for p in result["pages"]:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (p["url"], p["template"], p["passed"], p["failed"], p["unnamed"], p["unlabeled"]))
    lines.append("")
    lines.append("## Checks (first page)")
    if result["pages"]:
        for cid, c in result["pages"][0]["checks"].items():
            lines.append("- [%s] %s %s: %s" % (c["verdict"], cid, c["label"], c["note"]))
    lines.append("")
    lines.append("## Defects")
    for p in result["pages"]:
        for d in p["defects"][:10]:
            lines.append("- %s %s: %s. Fix: %s" % (urlparse(p["url"]).path or "/", d["check"], d["selector"], d["fix"]))
    lines.append("")
    tools = {k: v for k, v in (site.get("tools") or {}).items() if v != "not declared"}
    lines.append("## Agent tool surface (informational)")
    lines.append("- " + (", ".join("%s=%s" % kv for kv in tools.items()) if tools else "nothing declared"))
    lines.append("")
    if site["could_not_verify"]:
        lines.append("## Could not verify")
        for x in site["could_not_verify"]:
            lines.append("- " + x)
        lines.append("")
    lines.append("Method: " + site["method_note"])
    return "\n".join(lines) + "\n"


def self_test():
    html = """<html><body><header><nav><a href="/">Home</a><a href="/book"><img src="i.png" alt="Book now"></a></nav></header>
    <main><h1>Clinic</h1><p>text</p><p>more</p>
    <div class="checkout-btn" onclick="go()"><i class="fa"></i><span>Pay now</span></div>
    <button type="submit" id="btn-checkout" aria-label="Pay for the items in the cart"><i aria-hidden="true"></i></button>
    <a href="/x"><svg></svg></a>
    <form><input type="text" placeholder="Phone"><label for="em">Email</label><input type="email" id="em" name="email" autocomplete="email"><input type="text" name="fullname" id="fn"><label for="fn">Name</label><button>Send</button></form>
    <div role="status" aria-live="polite"></div>
    <div class="modal-popup">x</div>
    <div role="buton">bad</div><span aria-describedby="nope">y</span>
    </main><footer><p>c</p></footer></body></html>"""
    st = inspect_static(html, "https://example.com/")
    assert st["landmarks"]["main"] == 1 and st["landmarks"]["navigation"] == 1, st["landmarks"]
    assert len(st["clickable_generics"]) == 1, st["clickable_generics"]
    assert st["fields_total"] == 3 and len(st["fields_placeholder_only"]) == 1, (st["fields_total"], st["fields_placeholder_only"])
    assert len(st["aria_violations"]) == 2, st["aria_violations"]
    page = checklist_page(st, None, {"/.well-known/ucp": "not declared"})
    assert len(page["checks"]) == 14, len(page["checks"])
    for c in page["checks"].values():
        assert c["verdict"] in ("PASS", "FAIL", "N/A", "COULD NOT VERIFY", "INFO"), c
        assert "points" not in c and "earned" not in c
    assert page["checks"]["CTL-01"]["verdict"] == "FAIL" and page["checks"]["CTL-02"]["verdict"] == "FAIL"
    assert page["checks"]["STR-01"]["verdict"] == "PASS" and page["checks"]["ACC-01"]["verdict"] == "COULD NOT VERIFY"
    assert page["checks"]["ACC-02"]["verdict"] == "INFO"
    assert "score" not in page and "gate" not in page
    rd = {"status": 200, "dom_elements": 300, "ax_interactive": 5, "ax_unnamed_interactive": 1, "ax_unnamed_roles": ["button"],
          "clickable_generics_rendered": [], "closed_shadow_hosts": [], "dialogs_rendered": [], "bot_wall": False}
    page2 = checklist_page(st, rd, {"/.well-known/ucp": "declared", "/.well-known/ai-plugin.json": "obsolete"})
    assert page2["checks"]["ACC-01"]["verdict"] == "PASS" and page2["checks"]["CTL-03"]["verdict"] == "FAIL"
    assert "obsolete=/.well-known/ai-plugin.json" in page2["checks"]["ACC-02"]["note"]
    md = format_md({"site": {"start_url": "https://example.com/", "scope": "homepage_only", "fetched_at": "t", "pages_audited": 1,
                             "checks_passed": page["passed"], "checks_failed": page["failed"], "checks_applicable": page["applicable"],
                             "method_note": "t", "could_not_verify": page["could_not_verify"], "tools": {}}, "pages": [page]})
    assert "Checks passed" in md and "site score" not in md.lower() and "/100" not in md
    print("SELF-TEST PASS: %d checks, %d passed, %d failed, %d defects" % (len(page["checks"]), page["passed"], page["failed"], len(page["defects"])))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI agent readiness checklist: semantic HTML and accessibility tree (lite).")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--urls", help="file with one URL per line (overrides discovery)")
    ap.add_argument("--scope", default="representative_templates", choices=sorted(SCOPE_CAPS))
    ap.add_argument("--render", default="auto", choices=["auto", "on", "off"])
    ap.add_argument("--html", help="local HTML file (static tier only)")
    ap.add_argument("--output", default="json", choices=["json", "md"])
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.self_test:
        return self_test()
    if args.html:
        result = audit(start_url=args.url, html=open(args.html, encoding="utf-8", errors="replace").read(), scope="homepage_only", render="off")
    else:
        if not args.url:
            ap.error("url or --html is required")
        urls = [l.strip() for l in open(args.urls, encoding="utf-8") if l.strip()] if args.urls else None
        result = audit(start_url=args.url, urls=urls, scope=args.scope, render=args.render)
    text = json.dumps(result, ensure_ascii=False, indent=2) if args.output == "json" else format_md(result)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        sys.stderr.write("wrote %s\n" % args.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
