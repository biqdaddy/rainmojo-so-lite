#!/usr/bin/env python3
"""
ai_platforms.py - single loader for the AI platform and crawler registry.

The registry (reference/frameworks/ai-platform-registry.json) is the one place
that knows which crawler tokens exist, who owns them, what role they play
(search index, training, user fetcher), whether the vendor documents them, and
which checklist items each of the ten answer platforms carries. Lite edition:
the registry holds no weights or scores. robots_generator.py, page_analyzer.py
and the aiso-*-lite skills read from here so the plugin never carries three
disagreeing bot lists.

Usage as a module:
    from ai_platforms import registry, crawlers, platform, visibility_tokens
Usage as a CLI:
    python ai_platforms.py --list-crawlers [--role search_index]
    python ai_platforms.py --platforms
    python ai_platforms.py --robots-policy friendly
    python ai_platforms.py --self-test
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.normpath(os.path.join(HERE, "..", "reference", "frameworks", "ai-platform-registry.json"))

_CACHE = None


def registry(path=None):
    """Load and cache the registry."""
    global _CACHE
    if _CACHE is None or path:
        with open(path or REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if path:
            return data
        _CACHE = data
    return _CACHE


def platforms():
    return registry()["platforms"]


def platform(platform_id):
    for p in platforms():
        if p["id"] == platform_id:
            return p
    raise KeyError("unknown platform id: %s" % platform_id)


def platform_ids():
    return [p["id"] for p in platforms()]


def crawlers(role=None, platform_id=None, evidence_tier=None, primary_only=False):
    """Return crawler records, optionally filtered."""
    out = []
    for c in registry()["crawlers"]:
        if role and c["role"] != role:
            continue
        if platform_id and platform_id not in c.get("platform_ids", []):
            continue
        if evidence_tier and c["evidence_tier"] != evidence_tier:
            continue
        if primary_only and not c.get("platform_ids"):
            continue
        out.append(c)
    return out


def crawler(token):
    for c in registry()["crawlers"]:
        if c["token"].lower() == token.lower():
            return c
    return None


def tokens(**filters):
    return [c["token"] for c in crawlers(**filters)]


def visibility_tokens(platform_id=None):
    """Tokens whose robots.txt status changes whether a site can be cited on a platform."""
    out = []
    for c in crawlers(platform_id=platform_id):
        if c.get("affects_visibility"):
            out.append(c["token"])
    return out


def training_tokens():
    return [c["token"] for c in crawlers(role="training")]


def robots_policy(name):
    """Return the ordered (token, directive) list for a named policy: friendly, selective, blocked."""
    pol = registry()["robots_policies"][name]
    return [(item["token"], item["directive"]) for item in pol["rules"]]



def checklist(platform_id):
    """Checklist items (id, label, inspection, rationale) for one platform; no points."""
    return platform(platform_id).get("checklist", [])


def self_test():
    reg = registry()
    assert "scoring" not in reg and "\"weight\":" not in json.dumps(reg), "lite registry must carry no scoring"
    assert len(platforms()) == 11, len(platforms())
    assert len(crawlers()) >= 60
    assert "OAI-SearchBot" in visibility_tokens("chatgpt") and "GPTBot" not in visibility_tokens("chatgpt")
    assert crawler("gptbot")["role"] == "training"
    assert platform("grok")["crawler_evidence"] != "official"
    assert checklist("chatgpt") and all("weight" not in item for item in checklist("chatgpt"))
    assert robots_policy("friendly") and robots_policy("selective") and robots_policy("blocked")
    print("SELF-TEST PASS: %d platforms, %d crawlers, no scoring keys" % (len(platforms()), len(crawlers())))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Query the AI platform and crawler registry (lite).")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list-crawlers", action="store_true")
    ap.add_argument("--role", default=None)
    ap.add_argument("--platform", default=None)
    ap.add_argument("--platforms", action="store_true")
    ap.add_argument("--robots-policy", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.self_test:
        return self_test()
    if args.list_crawlers:
        rows = crawlers(role=args.role, platform_id=args.platform)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for c in rows:
                print("%-22s %-12s %-13s robots=%-11s evidence=%-8s %s" % (
                    c["token"], c["vendor"], c["role"], c["respects_robots_txt"], c["evidence_tier"],
                    c.get("default_recommendation", "")))
        return 0
    if args.platforms:
        for p in platforms():
            print("%-20s %-16s crawler_evidence=%-8s visibility=%s" % (
                p["id"], p["vendor"], p["crawler_evidence"], ",".join(p.get("visibility_crawlers", [])) or "-"))
        return 0
    if args.robots_policy:
        for token, directive in robots_policy(args.robots_policy):
            print("User-agent: %s\n%s\n" % (token, directive))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
