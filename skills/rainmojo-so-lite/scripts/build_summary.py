#!/usr/bin/env python3
"""
build_summary.py - assemble a Tier 1 summary.json (mode audit) from the JSON the
lite measurement scripts already wrote, so the card never carries a number the
deliverables do not.

Lite edition: there is no site score and no weighting. Every dimension is a
count of checks passed out of checks applicable, copied from the inputs.

Inputs (any subset; absent inputs simply leave their blocks out):
  --agent      agent_readiness_lite.py --output json
  --page       page_analyzer.py --output json
  --robots     robots_generator.py --mode analyze --output json
  --checklist  a JSON the aiso-platform-lite skill writes by hand:
               {"platforms": [{"id", "label", "status", "crawler_access", "note"}],
                "dimensions": [{"key", "label", "passed", "total"}]}
  --sampling   JSON written by aiso-brand-mentions-lite ai_answer_sampling:
               {"query_matrix": [...], "dimensions": [...], "competitors": [...]}

Usage:
  python build_summary.py --agent a.json --page p.json --robots r.json \
      --client "Demo Clinic" --domain demo.example --lang th --skill so-audit-lite \
      --tier2 "work/demo-example/04-reports/demo-example_so-audit_2026-09-12.html" \
      --out work/demo-example/04-reports/demo-example_so-audit_2026-09-12_summary.json
  python build_summary.py --self-test
Pure ASCII; labels come from templates/widget/labels.json.
"""

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.normpath(os.path.join(HERE, ".."))


def _load(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def status_for_count(passed, total):
    """Status from a pass count: all passed = ok, none passed = critical, otherwise warning."""
    if not total:
        return "info"
    if passed == total:
        return "ok"
    if passed == 0:
        return "critical"
    return "warning"


def dim(key, label, passed, total, tooltip=None):
    d = {"key": key, "label": label, "value": passed, "max": total, "status": status_for_count(passed, total)}
    if tooltip:
        d["tooltip"] = tooltip
    return d


def build(agent=None, page=None, robots=None, checklist=None, sampling=None, client="", domain="", lang="en",
          skill="so-audit-lite", tier2="", tier2_label=None, summary_text="", run_id=None):
    sampling = sampling or {}
    checklist = checklist or {}
    L = _load(os.path.join(ROOT, "templates", "widget", "labels.json"))[lang]
    now = dt.datetime.now().astimezone().isoformat(timespec="minutes")
    cnv = []
    dims = []
    platforms_block = []
    actions = []
    key_risk = None

    if robots and robots.get("exists"):
        vis = {k: v for k, v in robots.get("ai_status", {}).items() if v.get("platform_ids") and v.get("role") in ("search_index", "user_fetcher")}
        allowed = sum(1 for v in vis.values() if v.get("ok"))
        dims.append(dim("crawler_access", L["dims"]["crawler_access"], allowed, len(vis), L["dim_tooltip_crawler"] % (allowed, len(vis))))
        blocked = [k for k, v in vis.items() if v.get("status") == "BLOCKED"]
        if blocked:
            key_risk = {"severity": "critical", "title": "AI search crawlers are blocked", "body": "Blocked in robots.txt: %s. A blocked search crawler cannot cite the site at all." % ", ".join(blocked[:6])}
            actions.append({"title": "Allow blocked AI search crawlers", "body": "Blocked in robots.txt: %s" % ", ".join(blocked[:6]), "impact": "high", "effort": "low", "owner": "Dev"})
        for tok in (robots.get("unregistered_tokens") or [])[:5]:
            cnv.append("robots.txt names a crawler token the registry does not track: %s" % tok)

    if page:
        checks = [page.get("ssr"), page.get("crawler_access"), page.get("content_blocks"), page.get("llms_txt")]
        checks = [c for c in checks if c]
        passed = sum(1 for c in checks if c.get("verdict") == "PASS")
        applicable = sum(1 for c in checks if c.get("verdict") in ("PASS", "FAIL"))
        dims.append(dim("page_readiness", L["dims"].get("passage_citability", "Page readiness"), passed, applicable))
        for c in checks:
            if c.get("verdict") == "COULD NOT VERIFY":
                cnv.append(c.get("check", "page check"))
        ssr = page.get("ssr") or {}
        if ssr.get("verdict") == "FAIL":
            actions.append({"title": "Serve the main text in the raw HTML", "body": "Rendering is %s: AI search crawlers do not run JavaScript, so text that appears only after scripts run is invisible to them." % ssr.get("rendering"), "impact": "high", "effort": "high", "owner": "Dev"})
        cb = page.get("content_blocks") or {}
        if cb.get("verdict") == "FAIL":
            actions.append({"title": "Rewrite blocks so each one stands alone", "body": "%d of %d blocks are self-contained and %d carry a definition; rewrite the rest so a block still makes sense when quoted on its own." % (cb.get("blocks_self_contained", 0), cb.get("total_blocks", 0), cb.get("blocks_with_definition", 0)), "impact": "high", "effort": "medium", "owner": "Content"})

    if agent:
        site = agent["site"]
        dims.append(dim("agent_readiness", L["dims"]["agent_readiness"], site.get("checks_passed", 0), site.get("checks_applicable", 0),
                        L["dim_tooltip_agent"] % (site.get("pages_audited", 0), "n/a")))
        for c in site.get("could_not_verify", []):
            if c not in cnv:
                cnv.append(c)
        labels = site.get("checks") or {}
        for check, n in list((site.get("failing_checks_by_pages") or {}).items())[:2]:
            fix = next((d["fix"] for p in agent["pages"] for d in p.get("defects", []) if d["check"] == check), "")
            actions.append({"title": "%s (%d %s)" % (labels.get(check, check), n, L["findings"]), "body": fix.split(";")[0][:180], "impact": "high" if n >= 3 else "medium", "effort": "medium", "owner": "Dev"})
        if key_risk is None and site.get("failing_checks_by_pages"):
            check, n = next(iter(site["failing_checks_by_pages"].items()))
            key_risk = {"severity": "warning", "title": labels.get(check, check), "body": "Failed on %d of %d audited pages. An AI agent that cannot name or find a control cannot operate the site." % (n, site.get("pages_audited", 0))}

    for p in checklist.get("platforms", []):
        platforms_block.append({"id": p["id"], "label": p["label"], "score": None, "status": p.get("status", "info"),
                                "crawler_access": p.get("crawler_access", "not_checked"), "note": (p.get("note") or "")[:110]})
        if p.get("crawler_access") == "unverifiable":
            cnv.append("%s: crawler access could not be verified (no documented crawler)" % p["label"])
    for d in checklist.get("dimensions", []):
        dims.append(dim(d["key"], d["label"], d["passed"], d["total"]))

    summary = {
        "schema": "rainmojo.tier1.summary/1",
        "mode": "audit",
        "meta": {"skill": skill, "client": client, "domain": domain, "generated_at": now, "lang": lang, "run_id": run_id or dt.datetime.now().strftime("%Y%m%d-%H%M")},
        "headline": {"kicker": L["card_kicker"], "title": L["card_title"] % client, "subtitle": domain},
        "summary": summary_text or "",
        "dimensions": dims[:8],
        "platforms": platforms_block,
        "actions": actions[:4],
        "transparency": {"crawled_at": (agent or {}).get("site", {}).get("fetched_at") or now,
                         "user_agents": ["RainmojoBot/1.0 (static)", "Chromium headless (rendered tier)"] if agent else ["RainmojoBot/1.0"],
                         "guidelines": ["ai-platform-registry.json v%s" % _load(os.path.join(ROOT, "reference", "frameworks", "ai-platform-registry.json"))["version"], "WAI-ARIA 1.2, WCAG 2.2", "Lite: counts of checks passed, no score"],
                         "could_not_verify": cnv[:8]},
        "handoff": {"tier2_path": tier2, "tier2_label": tier2_label or L["tier2_default"], "formats": ["HTML", "Markdown"]},
        "next_steps": [{"label": "Platform detail", "prompt": "/rainmojo-so-lite:aiso-platform-lite %s" % domain},
                       {"label": "Agent readiness fixes", "prompt": "/rainmojo-so-lite:aiso-agent-readiness-lite %s" % domain},
                       {"label": "Compare next round", "prompt": "/rainmojo-so-lite:compare-lite %s" % domain}],
    }
    for k in ("query_matrix", "competitors"):
        if sampling.get(k):
            summary[k] = sampling[k]
    if sampling.get("dimensions"):
        summary["dimensions"] = (sampling["dimensions"] + summary["dimensions"])[:8]
    if key_risk:
        summary["key_risk"] = key_risk
    for k in ("dimensions", "platforms", "actions"):
        if not summary[k]:
            del summary[k]
    return summary


def self_test():
    agent = {"site": {"fetched_at": "2026-09-12T00:00:00+00:00", "pages_audited": 2, "checks_passed": 9, "checks_applicable": 14,
                      "failing_checks_by_pages": {"CTL-03": 2, "FRM-01": 1}, "could_not_verify": ["ACC-01 headless render integrity (Playwright not run)"],
                      "checks": {"CTL-03": "Interactive controls carry an accessible name", "FRM-01": "Form fields have a programmatic label"}},
             "pages": [{"defects": [{"check": "CTL-03", "fix": "Give the control a name; decorative icons get aria-hidden"}]}]}
    robots = {"exists": True, "ai_status": {"OAI-SearchBot": {"platform_ids": ["chatgpt"], "role": "search_index", "status": "BLOCKED", "ok": False},
                                              "PerplexityBot": {"platform_ids": ["perplexity"], "role": "search_index", "status": "ALLOWED", "ok": True},
                                              "GPTBot": {"platform_ids": ["chatgpt"], "role": "training", "status": "BLOCKED", "ok": True}},
              "unregistered_tokens": ["FooBot"]}
    page = {"ssr": {"check": "SSR-01", "verdict": "FAIL", "rendering": "CSR"}, "crawler_access": {"check": "BOT-01", "verdict": "FAIL"},
            "content_blocks": {"check": "CNT-01", "verdict": "PASS", "total_blocks": 4, "blocks_self_contained": 3, "blocks_with_definition": 1},
            "llms_txt": {"check": "LLM-01", "verdict": "COULD NOT VERIFY"}}
    checklist = {"platforms": [{"id": "chatgpt", "label": "ChatGPT", "status": "critical", "crawler_access": "blocked", "note": "OAI-SearchBot blocked"},
                               {"id": "grok", "label": "Grok", "status": "info", "crawler_access": "unverifiable", "note": "no documented crawler"}],
                 "dimensions": [{"key": "platform_checklist", "label": "Platform checklist", "passed": 12, "total": 30}]}
    s = build(agent=agent, page=page, robots=robots, checklist=checklist, client="Demo", domain="demo.example", lang="en", tier2="x.html", summary_text="ok")
    assert "score" not in s, "lite summary must not carry a site score"
    assert all(d["value"] <= d["max"] for d in s["dimensions"]) and len(s["dimensions"]) == 4
    assert s["dimensions"][0]["key"] == "crawler_access" and s["dimensions"][0]["value"] == 1 and s["dimensions"][0]["max"] == 2
    assert s["key_risk"]["severity"] == "critical" and s["platforms"][1]["score"] is None
    assert any("FooBot" in c for c in s["transparency"]["could_not_verify"])
    assert len(s["actions"]) == 4
    text = json.dumps(s)
    assert "/100" not in text and chr(0x2014) not in text
    try:
        import present
        problems = present.validate(s) + present.lint(s)
        assert not problems, problems
    except ImportError:
        pass
    print("SELF-TEST PASS: %d dimensions as counts, %d platforms, no score" % (len(s["dimensions"]), len(s["platforms"])))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build a Tier 1 summary.json from lite measurement JSON (counts, no score).")
    ap.add_argument("--agent"); ap.add_argument("--page"); ap.add_argument("--robots"); ap.add_argument("--checklist"); ap.add_argument("--sampling")
    ap.add_argument("--client"); ap.add_argument("--domain")
    ap.add_argument("--lang", default="en", choices=["en", "th"]); ap.add_argument("--skill", default="so-audit-lite")
    ap.add_argument("--tier2", default=""); ap.add_argument("--tier2-label", dest="tier2_label")
    ap.add_argument("--summary", default=""); ap.add_argument("--run-id", dest="run_id")
    ap.add_argument("--out"); ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.self_test:
        return self_test()
    if not args.client or not args.domain:
        ap.error("--client and --domain are required")
    s = build(agent=_load(args.agent), page=_load(args.page), robots=_load(args.robots), checklist=_load(args.checklist),
              sampling=_load(args.sampling), client=args.client, domain=args.domain, lang=args.lang, skill=args.skill,
              tier2=args.tier2, tier2_label=args.tier2_label, summary_text=args.summary, run_id=args.run_id)
    text = json.dumps(s, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        sys.stderr.write("wrote %s\n" % args.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
