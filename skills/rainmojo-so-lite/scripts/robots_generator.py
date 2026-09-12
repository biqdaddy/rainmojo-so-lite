#!/usr/bin/env python3
"""
robots.txt Analyzer and Generator, AI-aware version (lite: counts and verdicts, no score).
Analyzes current robots.txt for AI crawler directives and generates
an updated version with proper AI bot support.

Usage:
    python robots_generator.py https://example.com
    python robots_generator.py https://example.com --mode generate --policy friendly
    python robots_generator.py https://example.com --mode diff
    python robots_generator.py --mode generate --policy selective --sitemap https://example.com/sitemap.xml
    python robots_generator.py --self-test
"""

import argparse
import sys
import json
import re
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Install: pip install requests", file=sys.stderr)
    sys.exit(1)


# Known AI crawlers and their purpose: loaded from the shared registry
# (reference/frameworks/ai-platform-registry.json via ai_platforms.py) so this
# script, page_analyzer.py and the aiso-*-lite skills agree.
# The dict shapes below are kept for callers that read AI_CRAWLERS / SEARCH_CRAWLERS.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ai_platforms as _reg

_ROLE_LABEL = {"search_index": "search", "training": "training", "user_fetcher": "user browsing",
               "ads": "ads", "link_preview": "link previews", "agent": "agent"}


def _recommended(c: dict) -> str:
    rec = c.get("default_recommendation", "Site-decides")
    if rec == "Allow":
        return "Allow"
    if rec == "Block":
        return "Block"
    # Site-decides: the audit never penalises either choice; the verdict names the
    # trade-off (training only, no citation benefit) and leaves the decision to the client.
    return "Site decides"


AI_CRAWLERS = {}
SEARCH_CRAWLERS = {}
for _c in _reg.crawlers():
    _entry = {
        "owner": _c["vendor"],
        "purpose": "%s (%s)" % (_c["purpose"], _ROLE_LABEL.get(_c["role"], _c["role"])),
        "recommended": _recommended(_c),
        "role": _c["role"],
        "evidence_tier": _c["evidence_tier"],
        "respects_robots_txt": _c["respects_robots_txt"],
        "platform_ids": _c.get("platform_ids", []),
    }
    if _c["token"] in ("Googlebot", "bingbot"):
        SEARCH_CRAWLERS[_c["token"]] = _entry
    else:
        AI_CRAWLERS[_c["token"]] = _entry


def fetch_robots(url: str) -> dict:
    """Fetch and parse robots.txt from a URL."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = {
        "url": robots_url,
        "exists": False,
        "raw": "",
        "rules": {},
        "sitemaps": [],
        "ai_status": {},
    }

    try:
        resp = requests.get(robots_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; RobotsTxtAnalyzer/1.0)"
        }, timeout=10)

        if resp.status_code == 200:
            result["exists"] = True
            result["raw"] = resp.text
            result["rules"], result["sitemaps"] = parse_robots(resp.text)
            result["declared_preferences"] = parse_declared_preferences(resp.text)
            known = {c["token"].lower() for c in _reg.crawlers()} | {"*", "googlebot", "bingbot", "googlebot-image",
                     "googlebot-news", "googlebot-video", "adsbot-google", "mediapartners-google", "yandex", "yandexbot",
                     "baiduspider", "duckduckbot", "slurp", "facebot", "linkedinbot", "pinterestbot", "twitterbot", "ia_archiver",
                     "ahrefsbot", "semrushbot", "mj12bot", "dotbot", "rogerbot", "screaming frog seo spider", "petalbot"}
            result["unregistered_tokens"] = sorted({v.get("token", k) for k, v in result["rules"].items()
                                                    if k not in known and not k.startswith("*")}, key=str.lower)

            # Check each AI crawler
            for bot_name, bot_info in AI_CRAWLERS.items():
                status = get_bot_status(result["rules"], bot_name)
                result["ai_status"][bot_name] = {
                    "status": status,
                    "owner": bot_info["owner"],
                    "purpose": bot_info["purpose"],
                    "recommended": bot_info["recommended"],
                    "ok": bot_info["recommended"] == "Site decides" or
                          (status in ("ALLOWED", "NOT_SPECIFIED") and bot_info["recommended"] == "Allow") or
                          (status == "BLOCKED" and bot_info["recommended"] == "Block"),
                    "role": bot_info.get("role"),
                    "evidence_tier": bot_info.get("evidence_tier"),
                    "respects_robots_txt": bot_info.get("respects_robots_txt"),
                    "platform_ids": bot_info.get("platform_ids", []),
                }

            # Check search crawlers
            for bot_name, bot_info in SEARCH_CRAWLERS.items():
                status = get_bot_status(result["rules"], bot_name)
                result["ai_status"][bot_name] = {
                    "status": status,
                    "owner": bot_info["owner"],
                    "purpose": bot_info["purpose"],
                    "recommended": "Allow",
                    "ok": status == "ALLOWED",
                }
        else:
            result["exists"] = False

    except requests.RequestException as e:
        result["error"] = str(e)

    return result


def parse_declared_preferences(text: str) -> dict:
    """Machine-readable usage preferences a robots.txt may carry in 2026: Cloudflare
    Content-Signal (search, ai-input, ai-train), IETF AIPREF Content-Usage, and the RSL
    License line. Reported for transparency, never scored: no platform states compliance."""
    prefs = {"content_signal": {}, "content_usage": {}, "rsl_license": ""}
    for line in (text or "").splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower(); value = value.strip()
        if key == "license":
            prefs["rsl_license"] = value
        elif key in ("content-signal", "content-usage"):
            target = prefs["content_signal"] if key == "content-signal" else prefs["content_usage"]
            for part in value.replace(";", ",").split(","):
                if "=" in part:
                    a, b = part.split("=", 1)
                    target[a.strip().lower()] = b.strip().lower()
    prefs["ai_input_declined"] = prefs["content_signal"].get("ai-input") == "no"
    prefs["declared"] = bool(prefs["content_signal"] or prefs["content_usage"] or prefs["rsl_license"])
    return prefs


def parse_robots(text: str) -> tuple:
    """Parse robots.txt into rules dict and sitemaps list.

    RFC 9309 group semantics: consecutive User-agent lines form ONE group and every
    Allow/Disallow that follows applies to each of them; product tokens are matched
    case-insensitively (keys are stored lower-cased, display spelling is kept in
    the value under "token"); a UTF-8 BOM is stripped; inline comments dropped."""
    rules = {}
    sitemaps = []
    current_agents = []
    last_was_agent = False

    for line in (text or "").lstrip("\ufeff").split("\n"):
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            token = value.lower()
            if not last_was_agent:
                current_agents = []
            if token not in current_agents:
                current_agents.append(token)
            if token not in rules:
                rules[token] = {"allow": [], "disallow": [], "token": value}
            last_was_agent = True
            continue
        if key == "allow" and current_agents:
            for agent in current_agents:
                rules[agent]["allow"].append(value)
        elif key == "disallow" and current_agents:
            for agent in current_agents:
                rules[agent]["disallow"].append(value)
        elif key == "sitemap":
            sitemaps.append(value)
        last_was_agent = False

    return rules, sitemaps


# Paths every well-run site keeps crawlers out of; disallowing them never makes access "partial"
HYGIENE_PATH_RE = re.compile(r"^/(?:wp-admin|wp-includes|wp-json|wp-login|xmlrpc|admin|cgi-bin|cart|checkout|my-account|account|login|"
                             r"search|feed|tag|author|private|tmp|temp|test|staging|api|\?|\*\?|page/\*/\?|\*/feed)", re.I)


def _status_from_rules(bot_rules: dict) -> str:
    disallow = [d for d in bot_rules.get("disallow", []) if d]
    allow = [a for a in bot_rules.get("allow", []) if a]
    if "/" in disallow and "/" not in allow:
        return "BLOCKED"
    content_blocks = [d for d in disallow if d != "/" and not HYGIENE_PATH_RE.match(d)]
    if content_blocks:
        return "PARTIAL"
    return "ALLOWED"


def get_bot_status(rules: dict, bot_name: str) -> str:
    """Determine if a bot is allowed, blocked, partially blocked, or not specified.

    Lookup is case-insensitive (RFC 9309); a group that names the bot wins over the
    wildcard group; a bot named nowhere inherits the wildcard group; no wildcard and
    no group means NOT_SPECIFIED (crawling permitted by default)."""
    key = (bot_name or "").lower()
    if key in rules:
        return _status_from_rules(rules[key])
    for agent, agent_rules in rules.items():
        if agent.lower() == key:
            return _status_from_rules(agent_rules)
    if "*" in rules:
        wild = _status_from_rules(rules["*"])
        return wild if wild != "ALLOWED" else "ALLOWED"
    return "NOT_SPECIFIED"


def generate_robots(policy: str, sitemap_url: str = "", domain: str = "") -> str:
    """Generate robots.txt content based on policy (friendly, selective, blocked).

    The per-crawler rules come from the registry's robots_policies so the file always
    names the documented search crawlers (OAI-SearchBot, Claude-SearchBot,
    meta-webindexer, Applebot, ...) and never an invented token."""
    lines = [f"# robots.txt for {domain}" if domain else "# robots.txt",
             f"# Policy: {policy}",
             f"# Generated by RAINMOJO SO (crawler registry v%s)" % _reg.registry()["version"],
             ""]
    policies = _reg.registry()["robots_policies"]
    if policy not in policies:
        raise ValueError("unknown policy: %s" % policy)

    private_paths = ["Disallow: /private/", "Disallow: /admin/"]
    groups = [("search_index", "# Search engines and AI search crawlers (bring citations and traffic)"),
              ("user_fetcher", "# User-initiated AI fetchers (a person asked the assistant to open a page)"),
              ("training", "# AI training crawlers (no citation benefit; block or allow is a policy decision)")]
    by_token = {c["token"]: c for c in _reg.crawlers()}
    rules = policies[policy]["rules"]
    for role, comment in groups:
        block = [r for r in rules if by_token.get(r["token"], {}).get("role") == role]
        if not block:
            continue
        lines.append(comment)
        for r in block:
            lines.append("User-agent: %s" % r["token"])
            lines.append(r["directive"])
            if policy == "selective" and r["directive"].startswith("Allow") and role != "user_fetcher":
                lines.extend(private_paths)
            lines.append("")
    leftovers = [r for r in rules if by_token.get(r["token"], {}).get("role") not in {g[0] for g in groups}]
    if leftovers:
        lines.append("# Other crawlers")
        for r in leftovers:
            lines.extend(["User-agent: %s" % r["token"], r["directive"], ""])

    lines.append("# Default")
    lines.append("User-agent: *")
    lines.append("Allow: /")
    if policy == "selective":
        lines.extend(private_paths + [
            "Disallow: /wp-admin/",
            # Reconcile before deploy: seo-noindex-checklist assigns /cart/ and /checkout/ to
            # meta_robots. A URL blocked here is never crawled, so its meta noindex is never
            # read. Drop these two lines whenever the client's noindex plan covers those URLs.
            "Disallow: /cart/",
            "Disallow: /checkout/",
        ])
    elif policy == "blocked":
        lines.extend(["Disallow: /wp-admin/", "Disallow: /private/"])

    if sitemap_url:
        lines.extend(["", f"Sitemap: {sitemap_url}"])

    return "\n".join(lines) + "\n"


def format_analysis(data: dict) -> str:
    """Format analysis as markdown."""
    lines = [
        f"# robots.txt Analysis",
        f"",
        f"**URL:** {data['url']}",
        f"**Exists:** {'Yes' if data['exists'] else 'No'}",
        f"",
    ]

    if not data["exists"]:
        lines.append("**robots.txt not found**: all bots can access everything by default.")
        lines.append("")
        lines.append("**Recommendation:** Create a robots.txt to control AI crawler access.")
        return "\n".join(lines)

    # AI crawler status table: primary crawlers (tied to one of the ten answer platforms)
    # first, grouped by role; secondary crawlers summarised underneath.
    role_label = {"search_index": "search", "training": "training", "user_fetcher": "user fetch",
                  "ads": "ads", "link_preview": "preview", "agent": "agent"}
    primary = {k: v for k, v in data["ai_status"].items() if v.get("platform_ids")}
    secondary = {k: v for k, v in data["ai_status"].items() if not v.get("platform_ids")}
    lines.extend([
        "## AI Crawler Access (documented platforms)",
        "",
        "| Bot | Owner | Role | Evidence | Status | Recommended | OK? |",
        "|-----|-------|------|:--------:|:------:|:-----------:|:---:|",
    ])
    for bot_name, info in primary.items():
        status_icon = {"ALLOWED": "ALLOWED", "BLOCKED": "BLOCKED", "PARTIAL": "PARTIAL", "NOT_SPECIFIED": "not specified"}.get(info["status"], "?")
        ok_icon = "Yes" if info.get("ok") else "No"
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            bot_name, info["owner"], role_label.get(info.get("role"), info.get("role", "")),
            info.get("evidence_tier", ""), status_icon, info["recommended"], ok_icon))
    lines.append("")
    lines.append("Evidence: official = vendor documents the token; observed = community lists only; "
                 "a platform with no documented crawler (Grok, DeepSeek) cannot be checked here and is reported as could not verify.")
    lines.append("")
    if secondary:
        lines.extend(["## Other AI crawlers", "", "| Bot | Owner | Role | Status | Recommended | OK? |", "|-----|-------|------|:------:|:-----------:|:---:|"])
        for bot_name, info in secondary.items():
            status_icon = {"ALLOWED": "ALLOWED", "BLOCKED": "BLOCKED", "PARTIAL": "PARTIAL", "NOT_SPECIFIED": "not specified"}.get(info["status"], "?")
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                bot_name, info["owner"], role_label.get(info.get("role"), info.get("role", "")), status_icon,
                info["recommended"], "Yes" if info.get("ok") else "No"))
        lines.append("")

    # Count only: visibility crawlers (search index + user fetch) so training choices never move it
    vis = {k: v for k, v in data["ai_status"].items() if v.get("role") in ("search_index", "user_fetcher") and v.get("platform_ids")}
    total = len(vis)
    ok_count = sum(1 for v in vis.values() if v.get("ok"))
    lines.extend([
        "",
        f"**Allowed count:** {ok_count} of {total} documented search and user-fetch crawlers allowed (a count, not a score)",
        "",
    ])

    # Tokens the registry does not know (spec 5D dynamic metric expansion): reported for review
    unknown = data.get("unregistered_tokens") or []
    if unknown:
        lines.extend(["## User-agent tokens not in the registry", "",
                      "This robots.txt names crawlers the AI platform registry does not track. Report them as observed tokens and add them to "
                      "reference/frameworks/ai-platform-registry.json after checking the vendor documentation; never guess a role.", ""])
        for tok in unknown[:40]:
            lines.append("- " + tok)
        lines.append("")

    # Declared usage preferences (2026 standards): reported, never scored
    prefs = data.get("declared_preferences") or {}
    if prefs.get("declared"):
        lines.extend(["## Declared usage preferences (reported, not scored)", ""])
        if prefs.get("content_signal"):
            lines.append("- Content-Signal: " + ", ".join("%s=%s" % kv for kv in prefs["content_signal"].items()))
        if prefs.get("content_usage"):
            lines.append("- Content-Usage: " + ", ".join("%s=%s" % kv for kv in prefs["content_usage"].items()))
        if prefs.get("rsl_license"):
            lines.append("- RSL License: " + prefs["rsl_license"])
        if prefs.get("ai_input_declined"):
            lines.append("- ai-input=no is declared: the site has opted out of AI answers by policy")
        lines.append("")

    # Sitemaps
    if data["sitemaps"]:
        lines.extend(["## Sitemaps", ""])
        for s in data["sitemaps"]:
            lines.append(f"- {s}")
        lines.append("")

    # Recommendations
    issues = [name for name, info in data["ai_status"].items() if not info.get("ok")]
    if issues:
        lines.extend(["## Recommendations", ""])
        for bot in issues:
            info = data["ai_status"][bot]
            if info["recommended"] == "Allow" and info["status"] in ("BLOCKED", "NOT_SPECIFIED"):
                lines.append(f"- **{bot}** ({info['owner']}): Currently {info['status'].lower()}, recommend **allowing** for AI search visibility")
            elif info["recommended"] == "Block" and info["status"] == "ALLOWED":
                lines.append(f"- **{bot}** ({info['owner']}): Currently allowed, recommend **blocking** (undocumented or ignores robots.txt, no citation benefit)")
        lines.append("")

    return "\n".join(lines)


def format_diff(current: str, new: str) -> str:
    """Show diff between current and new robots.txt."""
    current_lines = current.strip().split("\n")
    new_lines = new.strip().split("\n")

    lines = ["# robots.txt Diff", "", "```diff"]

    current_set = set(l.strip() for l in current_lines if l.strip() and not l.strip().startswith("#"))
    new_set = set(l.strip() for l in new_lines if l.strip() and not l.strip().startswith("#"))

    removed = current_set - new_set
    added = new_set - current_set

    for line in sorted(removed):
        lines.append(f"- {line}")
    for line in sorted(added):
        lines.append(f"+ {line}")

    if not removed and not added:
        lines.append("  (no changes needed)")

    lines.extend(["```", ""])
    return "\n".join(lines)


def self_test():
    sample = ("\ufeff# demo\nUser-agent: GPTBot\nUser-agent: ClaudeBot\nDisallow: /\n\n"
              "user-agent: oai-searchbot\nAllow: /\nDisallow: /wp-admin/\n\n"
              "User-agent: PerplexityBot\nDisallow: /blog/\n\n"
              "User-agent: *\nDisallow: /search\n\n"
              "Sitemap: https://example.com/sitemap.xml\nContent-Signal: search=yes, ai-train=no\n")
    rules, sitemaps = parse_robots(sample)
    assert "gptbot" in rules and "claudebot" in rules, rules.keys()
    assert rules["claudebot"]["disallow"] == ["/"], "shared multi User-agent group must apply to every token (RFC 9309)"
    assert get_bot_status(rules, "GPTBot") == "BLOCKED" and get_bot_status(rules, "ClaudeBot") == "BLOCKED"
    assert get_bot_status(rules, "OAI-SearchBot") == "ALLOWED", "case-insensitive token plus hygiene path"
    assert get_bot_status(rules, "PerplexityBot") == "PARTIAL"
    assert get_bot_status(rules, "Claude-SearchBot") == "ALLOWED", "wildcard group with hygiene path only"
    assert get_bot_status({}, "Applebot") == "NOT_SPECIFIED"
    assert sitemaps == ["https://example.com/sitemap.xml"]
    prefs = parse_declared_preferences(sample)
    assert prefs["declared"] and prefs["content_signal"]["ai-train"] == "no" and not prefs["ai_input_declined"]
    for policy in ("friendly", "selective", "blocked"):
        text = generate_robots(policy, "https://example.com/sitemap.xml", "example.com")
        assert "User-agent: OAI-SearchBot" in text and "Sitemap:" in text, policy
    md = format_analysis({"url": "https://example.com/robots.txt", "exists": True, "raw": sample, "rules": rules, "sitemaps": sitemaps,
                          "ai_status": {"OAI-SearchBot": {"status": "ALLOWED", "owner": "OpenAI", "purpose": "search", "recommended": "Allow", "ok": True, "role": "search_index", "evidence_tier": "official", "platform_ids": ["chatgpt"]}},
                          "declared_preferences": prefs, "unregistered_tokens": []})
    assert "Allowed count" in md and "visibility score" not in md.lower()
    print("SELF-TEST PASS: RFC 9309 groups, case-insensitive tokens, BOM, hygiene paths, 3 policies")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Analyze robots.txt for AI crawler access and generate AI-friendly versions (lite)."
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("url", nargs="?", help="Website URL to analyze")
    parser.add_argument("--mode", choices=["analyze", "generate", "diff"], default="analyze",
                       help="analyze: check current robots.txt | generate: create new | diff: show changes")
    parser.add_argument("--policy", choices=["friendly", "selective", "blocked"], default="selective",
                       help="AI policy for generation (default: selective)")
    parser.add_argument("--sitemap", help="Sitemap URL to include")
    parser.add_argument("--output", choices=["markdown", "json", "txt"], default="markdown")
    args = parser.parse_args()
    if args.self_test:
        sys.exit(self_test())

    if args.mode == "generate" and not args.url:
        # Generate without analyzing
        domain = ""
        if args.sitemap:
            parsed = urlparse(args.sitemap)
            domain = parsed.netloc
        content = generate_robots(args.policy, args.sitemap or "", domain)
        if args.output == "txt":
            print(content)
        else:
            print(f"# Generated robots.txt (policy: {args.policy})\n")
            print(f"```\n{content}```")
        return

    if not args.url:
        parser.print_help()
        sys.exit(1)

    data = fetch_robots(args.url)
    parsed = urlparse(args.url)
    domain = parsed.netloc

    if args.mode == "analyze":
        if args.output == "json":
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(format_analysis(data))

    elif args.mode == "generate":
        sitemap = args.sitemap or (data["sitemaps"][0] if data.get("sitemaps") else "")
        content = generate_robots(args.policy, sitemap, domain)
        if args.output == "txt":
            print(content)
        else:
            print(f"# Generated robots.txt (policy: {args.policy})\n")
            print(f"```\n{content}```")

    elif args.mode == "diff":
        if not data["exists"]:
            print("No current robots.txt found, generating a new one.")
            content = generate_robots(args.policy, args.sitemap or "", domain)
            print(f"\n```\n{content}```")
        else:
            sitemap = args.sitemap or (data["sitemaps"][0] if data["sitemaps"] else "")
            new_content = generate_robots(args.policy, sitemap, domain)
            print(format_diff(data["raw"], new_content))
            print("\n## New robots.txt\n")
            print(f"```\n{new_content}```")


if __name__ == "__main__":
    main()
