"""MCP server that serves the Tier 1 card as an MCP Apps ui:// resource (stdio or streamable HTTP), so the same card renders inline in Claude, ChatGPT, Microsoft 365 Copilot, VS Code, Cursor and Goose; text-only hosts get the Markdown card.

Dependency-free (standard library only). Protocol: MCP JSON-RPC 2.0 with the MCP Apps
extension (SEP-1865, id io.modelcontextprotocol/ui, spec 2026-01-26).

Tools
  present_card       visible to the model. Input: summary (object) or sample (name) or
                     summary_path (stdio only). Returns content = Markdown card (the
                     fallback every text-only host shows) and structuredContent = the
                     summary JSON plus mode/lang/title. No HTML enters the model context.
  render_card_html   visibility ["app"]: called by the widget only, returns the host
                     fragment for a summary. Hidden from the model, so the card costs the
                     model nothing beyond the Markdown and the summary JSON.
  list_samples       visible to the model. Names the bundled sample summaries.

Resource
  ui://rainmojo-so-lite/tier1-card.html  mimeType text/html;profile=mcp-app, prefersBorder false,
                                    no external origins (CSP default). Shell in
                                    templates/widget/tier1-mcp-app.html.

Usage
  python mcp_server.py                       stdio (Claude Desktop config, .mcp.json, Codex .mcp.json)
  python mcp_server.py --http --port 8765    streamable HTTP, POST /mcp, stateless JSON responses.
                                             Put HTTPS and OAuth 2.1 in front of it for ChatGPT.
  python mcp_server.py --self-test           in-process protocol check, exit 0 on PASS
  python mcp_server.py --describe            print the tool and resource catalogue as JSON

Remote mode never reads summary_path (no server file access for remote clients); pass the
summary object or a sample name instead.
"""
import argparse
import io
import json
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WIDGET = os.path.join(ROOT, "templates", "widget")
SAMPLES = os.path.join(WIDGET, "samples")
SHELL = os.path.join(WIDGET, "tier1-mcp-app.html")
sys.path.insert(0, HERE)
import present  # noqa: E402

CARD_URI = "ui://rainmojo-so-lite/tier1-card.html"
MIME = "text/html;profile=mcp-app"
SERVER_NAME = "rainmojo-so-lite"
PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")


def _version():
    for cand in (os.path.join(ROOT, "..", "..", ".claude-plugin", "plugin.json"),):
        try:
            with open(os.path.normpath(cand), "r", encoding="utf-8") as f:
                return json.load(f).get("version", "0")
        except (OSError, ValueError):
            pass
    return "0"


VERSION = _version()
STATE = {"allow_paths": True}


def sample_names():
    return sorted(n[:-5] for n in os.listdir(SAMPLES) if n.endswith(".json"))


def shell_html():
    with io.open(SHELL, "r", encoding="utf-8") as f:
        return f.read().replace("{{VERSION}}", VERSION)


def load_summary(args):
    if isinstance(args.get("summary"), dict):
        return args["summary"]
    if args.get("sample"):
        name = str(args["sample"])
        if name not in sample_names():
            raise ValueError("unknown sample %r; call list_samples" % name)
        return present.load_summary(os.path.join(SAMPLES, name + ".json"))
    if args.get("summary_path"):
        if not STATE["allow_paths"]:
            raise ValueError("summary_path is disabled in remote mode; pass summary or sample")
        path = os.path.abspath(str(args["summary_path"]))
        if not os.path.isfile(path):
            raise ValueError("summary_path not found: %s" % path)
        return present.load_summary(path)
    raise ValueError("pass summary (object), sample (name) or summary_path")


def check(summary):
    problems = present.validate(summary) + present.lint(summary)
    if problems:
        raise ValueError("summary rejected: " + "; ".join(problems[:5]))


SUMMARY_SCHEMA = {"type": "object", "description": "Tier 1 summary.json (contract rainmojo.tier1.summary/1)"}

TOOLS = [
    {
        "name": "present_card",
        "title": "Show the RAINMOJO SO card",
        "description": "Render a RAINMOJO SO Tier 1 summary. Returns the Markdown card as text (shown by every host) and the summary as structuredContent; hosts with MCP Apps support draw the visual card inline from the same data.",
        "inputSchema": {"type": "object", "properties": {
            "summary": SUMMARY_SCHEMA,
            "sample": {"type": "string", "description": "bundled sample name from list_samples"},
            "summary_path": {"type": "string", "description": "local summary.json path (stdio mode only)"},
        }, "additionalProperties": False},
        "outputSchema": {"type": "object", "properties": {
            "mode": {"type": "string"}, "lang": {"type": "string"}, "title": {"type": "string"},
            "summary": SUMMARY_SCHEMA, "tier2_path": {"type": "string"}}, "required": ["mode", "lang", "title", "summary"]},
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
        "_meta": {"ui": {"resourceUri": CARD_URI, "visibility": ["model", "app"]},
                  "openai/outputTemplate": CARD_URI,
                  "openai/toolInvocation/invoking": "Drawing the RAINMOJO SO card",
                  "openai/toolInvocation/invoked": "RAINMOJO SO card ready"},
    },
    {
        "name": "render_card_html",
        "title": "Card HTML for the widget",
        "description": "Widget-only helper: returns the Tier 1 host fragment for a summary. Not for the model.",
        "inputSchema": {"type": "object", "properties": {"summary": SUMMARY_SCHEMA, "sample": {"type": "string"}}, "additionalProperties": False},
        "outputSchema": {"type": "object", "properties": {"card_html": {"type": "string"}}, "required": ["card_html"]},
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
        "_meta": {"ui": {"visibility": ["app"]}},
    },
    {
        "name": "list_samples",
        "title": "List bundled sample cards",
        "description": "Names of the bundled Tier 1 sample summaries (audit, comparison, howto, quick fact, troubleshoot, deployable).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "outputSchema": {"type": "object", "properties": {"samples": {"type": "array", "items": {"type": "string"}}}, "required": ["samples"]},
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
]

RESOURCE_META = {"ui": {"prefersBorder": False, "csp": {"connectDomains": [], "resourceDomains": []}}}
RESOURCES = [{"uri": CARD_URI, "name": "RAINMOJO SO Tier 1 card", "title": "RAINMOJO SO card",
              "description": "MCP Apps shell that draws the Tier 1 card from present_card results.",
              "mimeType": MIME, "_meta": RESOURCE_META}]


def text_result(text, structured, is_error=False):
    return {"content": [{"type": "text", "text": text}], "structuredContent": structured, "isError": is_error}


def call_tool(name, args):
    args = args or {}
    if name == "list_samples":
        names = sample_names()
        return text_result("Samples: " + ", ".join(names), {"samples": names})
    if name == "present_card":
        s = load_summary(args)
        check(s)
        md = present.render_md(s)
        structured = {"mode": s["mode"], "lang": s["meta"].get("lang", "en"), "title": s["headline"]["title"], "summary": s}
        t2 = (s.get("handoff") or {}).get("tier2_path")
        if t2:
            structured["tier2_path"] = t2
        return text_result(md, structured)
    if name == "render_card_html":
        s = load_summary(args)
        check(s)
        return text_result("card html", {"card_html": present.render_host(s)})
    raise KeyError(name)


def rpc_error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def handle(msg):
    """Return a response dict, or None for notifications."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
        return rpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "invalid request")
    method, rid, params = msg["method"], msg.get("id"), msg.get("params") or {}
    is_notification = "id" not in msg
    try:
        if method == "initialize":
            want = str(params.get("protocolVersion", ""))
            result = {"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                      "capabilities": {"tools": {"listChanged": False}, "resources": {"subscribe": False, "listChanged": False},
                                       "extensions": {"io.modelcontextprotocol/ui": {}}},
                      "serverInfo": {"name": SERVER_NAME, "title": "RAINMOJO SO card", "version": VERSION},
                      "instructions": "Call present_card with a Tier 1 summary object (or a sample name) to show the RAINMOJO SO card. The text result is the Markdown card; hosts that support MCP Apps draw the visual card inline."}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            try:
                result = call_tool(params.get("name"), params.get("arguments"))
            except KeyError:
                return rpc_error(rid, -32602, "unknown tool %r" % params.get("name"))
            except ValueError as e:
                result = text_result(str(e), {"error": str(e)}, is_error=True)
        elif method == "resources/list":
            result = {"resources": RESOURCES}
        elif method == "resources/templates/list":
            result = {"resourceTemplates": []}
        elif method == "resources/read":
            if params.get("uri") != CARD_URI:
                return rpc_error(rid, -32002, "resource not found: %s" % params.get("uri"))
            result = {"contents": [{"uri": CARD_URI, "mimeType": MIME, "text": shell_html(), "_meta": RESOURCE_META}]}
        elif method == "prompts/list":
            result = {"prompts": []}
        elif method.startswith("notifications/"):
            return None
        else:
            if is_notification:
                return None
            return rpc_error(rid, -32601, "method not found: %s" % method)
    except Exception as e:  # keep the transport alive
        return rpc_error(rid, -32603, "internal error: %s" % e)
    if is_notification:
        return None
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def handle_payload(payload):
    if isinstance(payload, list):
        out = [r for r in (handle(m) for m in payload) if r is not None]
        return out or None
    return handle(payload)


# ---------------------------------------------------------------------------
# transports
# ---------------------------------------------------------------------------

def serve_stdio():
    stdin = io.open(sys.stdin.fileno(), "rb", buffering=0)
    stdout = io.open(sys.stdout.fileno(), "wb", buffering=0)
    lock = threading.Lock()
    while True:
        line = stdin.readline()
        if not line:
            return 0
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line.decode("utf-8"))
        except ValueError:
            resp = rpc_error(None, -32700, "parse error")
        else:
            resp = handle_payload(payload)
        if resp is not None:
            data = (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")
            with lock:
                stdout.write(data)
                stdout.flush()


def serve_http(host, port, path):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _send(self, status, body=None, ctype="application/json"):
            data = b"" if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept, Authorization, Mcp-Session-Id, MCP-Protocol-Version")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS, DELETE")
            self.end_headers()
            if data:
                self.wfile.write(data)

        def do_OPTIONS(self):
            self._send(204)

        def do_GET(self):
            if self.path.rstrip("/") == path.rstrip("/"):
                self._send(405, {"error": "this server answers POST only (stateless streamable HTTP, JSON responses)"})
            elif self.path == "/healthz":
                self._send(200, {"ok": True, "server": SERVER_NAME, "version": VERSION})
            else:
                self._send(404, {"error": "not found"})

        def do_DELETE(self):
            self._send(204)

        def do_POST(self):
            if self.path.rstrip("/") != path.rstrip("/"):
                return self._send(404, {"error": "not found"})
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            try:
                payload = json.loads(raw.decode("utf-8"))
            except ValueError:
                return self._send(400, rpc_error(None, -32700, "parse error"))
            resp = handle_payload(payload)
            if resp is None:
                return self._send(202)
            self._send(200, resp)

        def log_message(self, fmt, *args):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    srv = ThreadingHTTPServer((host, port), Handler)
    sys.stderr.write("rainmojo-so MCP: http://%s:%d%s (POST), stateless; add HTTPS + OAuth in front for ChatGPT\n" % (host, port, path))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def self_test():
    errs = []

    def rq(rid, method, params=None):
        return handle({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})

    init = rq(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}})
    if init.get("result", {}).get("protocolVersion") != "2025-06-18":
        errs.append("initialize protocol echo")
    if "io.modelcontextprotocol/ui" not in init["result"]["capabilities"].get("extensions", {}):
        errs.append("ui extension capability missing")
    if handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is not None:
        errs.append("notification must not answer")
    tools = rq(2, "tools/list")["result"]["tools"]
    names = [t["name"] for t in tools]
    if names != ["present_card", "render_card_html", "list_samples"]:
        errs.append("tool names %r" % names)
    pc = next(t for t in tools if t["name"] == "present_card")
    if pc["_meta"]["ui"]["resourceUri"] != CARD_URI or pc["_meta"]["openai/outputTemplate"] != CARD_URI:
        errs.append("present_card resourceUri")
    if next(t for t in tools if t["name"] == "render_card_html")["_meta"]["ui"]["visibility"] != ["app"]:
        errs.append("render_card_html must be app-only")
    res = rq(3, "resources/list")["result"]["resources"]
    if len(res) != 1 or res[0]["mimeType"] != MIME or res[0]["_meta"]["ui"]["prefersBorder"] is not False:
        errs.append("resource listing")
    body = rq(4, "resources/read", {"uri": CARD_URI})["result"]["contents"][0]
    if "ui/initialize" not in body["text"] or "ui/notifications/tool-result" not in body["text"] or "{{VERSION}}" in body["text"]:
        errs.append("shell html incomplete")
    if "http://" in body["text"] or "https://" in body["text"]:
        errs.append("shell must not reference external origins")
    ls = rq(5, "tools/call", {"name": "list_samples", "arguments": {}})["result"]
    if "audit-ai-visibility" not in ls["structuredContent"]["samples"]:
        errs.append("samples")
    r = rq(6, "tools/call", {"name": "present_card", "arguments": {"sample": "audit-ai-visibility"}})["result"]
    sc = r["structuredContent"]
    if r.get("isError") or sc["lang"] not in ("th", "en") or sc["mode"] != "audit" or "<" in r["content"][0]["text"][:200]:
        errs.append("present_card result shape")
    if "card_html" in json.dumps(sc):
        errs.append("present_card must not carry HTML (token cost)")
    if "[#" not in r["content"][0]["text"]:
        errs.append("markdown fallback missing ASCII bars")
    h = rq(7, "tools/call", {"name": "render_card_html", "arguments": {"summary": sc["summary"]}})["result"]
    if h.get("isError") or 'class="rm-card' not in h["structuredContent"]["card_html"]:
        errs.append("render_card_html fragment")
    bad = rq(8, "tools/call", {"name": "present_card", "arguments": {"summary": {"schema": "x"}}})["result"]
    if not bad.get("isError"):
        errs.append("invalid summary must be isError")
    STATE["allow_paths"] = False
    rp = rq(9, "tools/call", {"name": "present_card", "arguments": {"summary_path": os.path.join(SAMPLES, "audit-ai-visibility.json")}})["result"]
    STATE["allow_paths"] = True
    if not rp.get("isError") or "remote" not in rp["content"][0]["text"]:
        errs.append("summary_path must be refused in remote mode")
    if "error" not in rq(10, "nope/method"):
        errs.append("unknown method must error")
    if handle_payload([{"jsonrpc": "2.0", "method": "notifications/x"}]) is not None:
        errs.append("batch of notifications must be silent")
    print("SELF-TEST %s" % ("PASS" if not errs else "FAIL: " + "; ".join(errs)))
    return 0 if not errs else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--http", action="store_true", help="serve streamable HTTP instead of stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--path", default="/mcp")
    ap.add_argument("--allow-paths", action="store_true", help="HTTP mode: allow summary_path (local trusted use only)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--describe", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.describe:
        print(json.dumps({"server": SERVER_NAME, "version": VERSION, "tools": TOOLS, "resources": RESOURCES}, ensure_ascii=False, indent=2))
        return 0
    if a.http:
        STATE["allow_paths"] = bool(a.allow_paths)
        return serve_http(a.host, a.port, a.path)
    return serve_stdio()


if __name__ == "__main__":
    sys.exit(main())
