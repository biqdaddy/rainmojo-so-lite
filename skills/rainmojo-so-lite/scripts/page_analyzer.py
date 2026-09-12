#!/usr/bin/env python3
"""
page_analyzer.py - Analyze a web page for AI search readiness (lite: checks, no score).

Checks SSR detection, AI crawler access directives (RFC 9309 robots.txt parsing),
content block extractability signals, and llms.txt presence. Every check is
reported as PASS, FAIL, INFO or COULD NOT VERIFY. There is no weighting, no
grade and no overall number: the learner reads the list and fixes what failed.

Usage:
    python page_analyzer.py https://example.com
    python page_analyzer.py https://example.com --output json
    python page_analyzer.py --self-test
"""

import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup, Comment
except ImportError:
    sys.exit("Missing dependency: pip install beautifulsoup4 lxml")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Visibility crawlers of the documented answer platforms, from the shared registry
# (reference/frameworks/ai-platform-registry.json). Training-only tokens are not
# listed here: blocking GPTBot or ClaudeBot does not remove a site from ChatGPT or
# Claude search, so they never change the crawler-access verdict.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import ai_platforms as _reg
    AI_BOTS = sorted(set(_reg.visibility_tokens()) | {"Googlebot"})
except Exception:  # registry missing: fall back to the documented search crawlers
    AI_BOTS = ["OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "Googlebot", "bingbot",
               "meta-webindexer", "Applebot"]

FRAMEWORK_SIGNATURES = {
    "react": [r'id=["\']root["\']', r'id=["\']__next["\']', r"data-reactroot", r"__NEXT_DATA__"],
    "vue": [r'id=["\']app["\']', r"__VUE__", r"__NUXT__", r"data-v-"],
    "angular": [r"ng-version", r"_nghost", r"_ngcontent"],
    "nextjs": [r"__NEXT_DATA__", r"_next/static"],
    "nuxt": [r"__NUXT__", r"_nuxt/"],
    "svelte": [r"__svelte", r"svelte-"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RainmojoBot/1.0; +https://rainmojo.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
}

REQUEST_TIMEOUT = 15


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _session():
    if requests is None:
        sys.exit("Missing dependency: pip install requests")
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _safe_get(session, url, **kwargs):
    try:
        return session.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.RequestException:
        return None


def _text_ratio(html):
    """Return ratio of visible text length to total HTML length."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "path"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    text = soup.get_text(separator=" ", strip=True)
    if not html:
        return 0.0
    return len(text) / len(html)


# ---------------------------------------------------------------------------
# 1. SSR detection
# ---------------------------------------------------------------------------

def detect_ssr(html):
    """Verdict on whether the main text is present in the raw HTML.

    Googlebot renders JavaScript, but most AI search and user-fetch crawlers
    (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot) do not, so
    text that only appears after JavaScript runs is invisible to them."""
    detected = []
    for framework, patterns in FRAMEWORK_SIGNATURES.items():
        for pat in patterns:
            if re.search(pat, html):
                detected.append(framework)
                break
    ratio = _text_ratio(html)
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body")
    body_text = body.get_text(separator=" ", strip=True) if body else ""
    word_count = len(body_text.split())
    if word_count >= 80 and ratio > 0.03:
        verdict = "SSR"
    elif word_count < 20:
        verdict = "CSR"
    else:
        verdict = "Hybrid"
    return {
        "check": "SSR-01 main text present in raw HTML",
        "verdict": {"SSR": "PASS", "Hybrid": "FAIL", "CSR": "FAIL"}[verdict],
        "rendering": verdict,
        "text_ratio": round(ratio, 4),
        "body_word_count": word_count,
        "frameworks_detected": detected,
        "note": "AI search crawlers read the raw HTML; Googlebot renders JavaScript but most AI crawlers do not",
    }


# ---------------------------------------------------------------------------
# 2. AI crawler access (RFC 9309 robots.txt)
# ---------------------------------------------------------------------------

def _parse_robots_txt(robots_text):
    """Return mapping of lower-cased user-agent token -> list of disallow paths.

    RFC 9309: consecutive User-agent lines share one group; tokens match case-
    insensitively; a UTF-8 BOM on the first line is ignored; comments dropped."""
    blocks = {}
    current_agents = []
    last_was_agent = False
    for line in (robots_text or "").lstrip("\ufeff").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip().lower()
            if not last_was_agent:
                current_agents = []
            if agent not in current_agents:
                current_agents.append(agent)
            blocks.setdefault(agent, [])
            last_was_agent = True
            continue
        if low.startswith("disallow:") and current_agents:
            path = line.split(":", 1)[1].strip()
            if path:
                for ag in current_agents:
                    blocks.setdefault(ag, []).append(path)
        last_was_agent = False
    return blocks


def bot_statuses(robots_text):
    blocks = _parse_robots_txt(robots_text)
    wildcard_blocks = blocks.get("*", [])
    out = {}
    for bot in AI_BOTS:
        key = bot.lower()
        if key in blocks:
            out[bot] = "BLOCKED" if "/" in blocks[key] else "ALLOWED"
        elif "/" in wildcard_blocks:
            out[bot] = "BLOCKED"
        else:
            out[bot] = "NOT_SPECIFIED"
    return out


def check_crawler_access(session, url, html, resp_headers):
    parsed = urlparse(url)
    base = "%s://%s" % (parsed.scheme, parsed.netloc)
    x_robots = resp_headers.get("X-Robots-Tag", "")
    soup = BeautifulSoup(html, "lxml")
    meta_robots_tags = soup.find_all("meta", attrs={"name": re.compile(r"robots", re.I)})
    meta_content = " ".join(t.get("content", "") for t in meta_robots_tags).lower()
    ai_directives = [d for d in ("noai", "noimageai") if d in meta_content or d in x_robots.lower()]
    robots_resp = _safe_get(session, base + "/robots.txt")
    if robots_resp is None:
        return {"check": "BOT-01 documented AI search crawlers allowed", "verdict": "COULD NOT VERIFY",
                "x_robots_tag": x_robots or None, "meta_robots": meta_content or None, "ai_directives": ai_directives,
                "bot_access": {}, "robots_txt_found": None, "note": "robots.txt could not be fetched"}
    robots_text = robots_resp.text if robots_resp.status_code == 200 else ""
    status = bot_statuses(robots_text)
    blocked = [b for b, s in status.items() if s == "BLOCKED"]
    verdict = "FAIL" if blocked or ai_directives else "PASS"
    return {
        "check": "BOT-01 documented AI search crawlers allowed",
        "verdict": verdict,
        "x_robots_tag": x_robots or None,
        "meta_robots": meta_content or None,
        "ai_directives": ai_directives,
        "bot_access": status,
        "robots_txt_found": bool(robots_text),
        "note": ("blocked: " + ", ".join(blocked)) if blocked else "no documented search or user-fetch crawler is blocked",
    }


# ---------------------------------------------------------------------------
# 3. Content block extractability signals
# ---------------------------------------------------------------------------

_STAT_PATTERN = re.compile(r"\d+[\d,]*\.?\d*\s*%|(?:\u0e3f|\$|EUR|USD|THB)\s*\d|^\d{4}$", re.M)
_DEFINITION_PATTERN = re.compile(
    r"(?:is defined as|refers to|means that|\u0e04\u0e37\u0e2d|\u0e2b\u0e21\u0e32\u0e22\u0e16\u0e36\u0e07|\bis\b .{5,60}(?:that|which|where))",
    re.I,
)


def _block_signals(text):
    """Three observable signals per block; no length band and no composite number."""
    words = text.split()
    has_stats = bool(_STAT_PATTERN.search(text))
    has_definition = bool(_DEFINITION_PATTERN.search(text))
    starts_with_subject = bool(re.match(r"^[A-Z\u0E00-\u0E7F]", text.strip()))
    no_dangling_ref = not re.match(r"^(It |This |That |These |Those |They |He |She )", text.strip())
    self_contained = starts_with_subject and no_dangling_ref
    return {
        "word_count": len(words),
        "has_statistics": has_stats,
        "has_definition_pattern": has_definition,
        "is_self_contained": self_contained,
        "signals_present": int(has_stats) + int(has_definition) + int(self_contained),
        "preview": text[:120].replace("\n", " ") + ("..." if len(text) > 120 else ""),
    }


def extract_content_blocks(html):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    blocks = []
    seen = set()
    for el in soup.find_all(["p", "li", "blockquote", "td", "dd"]):
        text = el.get_text(separator=" ", strip=True)
        if len(text) < 40:
            continue
        fp = text[:80]
        if fp in seen:
            continue
        seen.add(fp)
        blocks.append(_block_signals(text))
    for heading in soup.find_all(["h2", "h3", "h4"]):
        parts = []
        for sib in heading.find_next_siblings():
            if sib.name and sib.name in ["h1", "h2", "h3", "h4"]:
                break
            t = sib.get_text(separator=" ", strip=True)
            if t:
                parts.append(t)
        combined = " ".join(parts)
        if len(combined) > 80:
            fp = combined[:80]
            if fp not in seen:
                seen.add(fp)
                blocks.append(_block_signals(combined))
    blocks.sort(key=lambda b: b["signals_present"], reverse=True)
    self_contained = sum(1 for b in blocks if b["is_self_contained"])
    with_definition = sum(1 for b in blocks if b["has_definition_pattern"])
    verdict = "PASS" if blocks and self_contained and with_definition else ("FAIL" if blocks else "COULD NOT VERIFY")
    return {
        "check": "CNT-01 self-contained blocks with a definition or a fact",
        "verdict": verdict,
        "total_blocks": len(blocks),
        "blocks_self_contained": self_contained,
        "blocks_with_definition": with_definition,
        "blocks_with_statistics": sum(1 for b in blocks if b["has_statistics"]),
        "top_blocks": blocks[:15],
        "note": "each block is listed with its three signals; rewrite the ones that carry none",
    }


# ---------------------------------------------------------------------------
# 4. llms.txt presence (hygiene item)
# ---------------------------------------------------------------------------

def check_llms_txt(session, url):
    parsed = urlparse(url)
    llms_url = "%s://%s/llms.txt" % (parsed.scheme, parsed.netloc)
    resp = _safe_get(session, llms_url)
    base = {"check": "LLM-01 llms.txt present and well formed (hygiene item, adoption evidence low)", "url": llms_url,
            "note": "2026 measurements found no major platform reading llms.txt; keep it as hygiene, never as the reason a site is or is not cited"}
    if resp is None:
        return dict(base, verdict="COULD NOT VERIFY", exists=None)
    if resp.status_code != 200:
        return dict(base, verdict="INFO", exists=False, details="not found")
    content = resp.text.strip()
    has_title = content.startswith("#")
    has_sections = bool(re.search(r"^## ", content, re.M))
    has_links = bool(re.search(r"\[.+?\]\(https?://", content))
    return dict(base, verdict="PASS" if (has_title and has_sections and has_links) else "FAIL", exists=True,
                line_count=len(content.splitlines()), has_title=has_title, has_sections=has_sections, has_links=has_links)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _md_bot_table(bot_access):
    lines = ["| Bot | Status |", "|-----|--------|"]
    for bot, status in bot_access.items():
        lines.append("| %s | %s |" % (bot, status))
    return "\n".join(lines)


def format_markdown(url, ssr, crawler, content, llms):
    checks = [ssr, crawler, content, llms]
    passed = sum(1 for c in checks if c["verdict"] == "PASS")
    applicable = sum(1 for c in checks if c["verdict"] in ("PASS", "FAIL"))
    parts = ["# AI readiness checklist: %s" % url, "",
             "Checks passed: %d of %d applicable (no score, no weights)" % (passed, applicable), ""]
    for c in checks:
        parts.append("- [%s] %s" % (c["verdict"], c["check"]))
    parts += ["", "## 1. Server-side rendering",
              "- Rendering: **%s**" % ssr["rendering"],
              "- Text-to-HTML ratio: %s" % ssr["text_ratio"],
              "- Body word count: %s" % ssr["body_word_count"],
              "- Frameworks detected: %s" % (", ".join(ssr["frameworks_detected"]) or "none"),
              "- Note: %s" % ssr["note"], "",
              "## 2. AI crawler access", _md_bot_table(crawler["bot_access"])]
    if crawler["ai_directives"]:
        parts.append("\nAI directives found: " + ", ".join(crawler["ai_directives"]))
    parts += ["- Note: %s" % crawler["note"], "", "## 3. Content blocks",
              "- Total blocks found: %d" % content["total_blocks"],
              "- Self-contained: %d, with definition: %d, with statistics: %d" % (content["blocks_self_contained"], content["blocks_with_definition"], content["blocks_with_statistics"])]
    for i, block in enumerate(content["top_blocks"][:5], 1):
        parts.append("\n**Block %d** (%d words; statistics=%s, definition=%s, self-contained=%s)" % (
            i, block["word_count"], block["has_statistics"], block["has_definition_pattern"], block["is_self_contained"]))
        parts.append("> " + block["preview"])
    parts += ["", "## 4. llms.txt"]
    if llms.get("exists"):
        parts.append("- Found at: %s (title=%s, sections=%s, links=%s)" % (llms["url"], llms["has_title"], llms["has_sections"], llms["has_links"]))
    elif llms.get("exists") is False:
        parts.append("- Not found")
    else:
        parts.append("- Could not verify")
    parts.append("- Note: %s" % llms["note"])
    return "\n".join(parts)


def format_json(url, ssr, crawler, content, llms):
    return json.dumps({"url": url, "ssr": ssr, "crawler_access": crawler, "content_blocks": content, "llms_txt": llms},
                      ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def analyze(url):
    session = _session()
    resp = _safe_get(session, url)
    if resp is None or resp.status_code >= 400:
        sys.exit("Failed to fetch %s" % url)
    html = resp.text
    ssr = detect_ssr(html)
    time.sleep(0.3)
    crawler = check_crawler_access(session, url, html, dict(resp.headers))
    time.sleep(0.3)
    content = extract_content_blocks(html)
    time.sleep(0.3)
    llms = check_llms_txt(session, url)
    return ssr, crawler, content, llms


def self_test():
    html = ("<html><body><main><h1>Dental implants</h1>"
            "<p>A dental implant is defined as a titanium post placed in the jaw. " + "Text " * 90 + "</p>"
            "<p>Prices start at 45,000 THB and 92% of patients report no pain.</p>"
            "<h2>How long does it take</h2><p>The treatment refers to three visits over four months, which most clinics follow.</p>"
            "</main></body></html>")
    ssr = detect_ssr(html)
    assert ssr["verdict"] == "PASS" and ssr["rendering"] == "SSR", ssr
    assert "score" not in ssr and "grade" not in ssr
    robots = "\ufeffUser-agent: OAI-SearchBot\nUser-agent: PerplexityBot\nDisallow: /\n\nuser-agent: *\nDisallow: /wp-admin/\n"
    status = bot_statuses(robots)
    assert status["OAI-SearchBot"] == "BLOCKED" and status["PerplexityBot"] == "BLOCKED", status
    assert status["Googlebot"] == "NOT_SPECIFIED", status
    content = extract_content_blocks(html)
    assert content["verdict"] == "PASS" and content["blocks_with_statistics"] >= 1, content
    for b in content["top_blocks"]:
        assert "extractability_score" not in b and "score" not in b
    md = format_markdown("https://example.com/", ssr, {"check": "BOT-01 documented AI search crawlers allowed", "verdict": "FAIL", "bot_access": status, "ai_directives": [], "note": "blocked: OAI-SearchBot"},
                         content, {"check": "LLM-01 llms.txt present", "verdict": "INFO", "exists": False, "url": "x", "note": "hygiene"})
    assert "Checks passed" in md and "/100" not in md and "Grade" not in md
    print("SELF-TEST PASS: 4 checks, RFC 9309 shared group, no score keys")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Analyze a web page for AI search readiness (lite checklist).")
    parser.add_argument("url", nargs="?", help="URL of the page to analyze")
    parser.add_argument("--output", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.self_test:
        sys.exit(self_test())
    if not args.url:
        parser.error("url is required")
    url = args.url if args.url.startswith("http") else "https://" + args.url
    ssr, crawler, content, llms = analyze(url)
    print(format_json(url, ssr, crawler, content, llms) if args.output == "json" else format_markdown(url, ssr, crawler, content, llms))


if __name__ == "__main__":
    main()
