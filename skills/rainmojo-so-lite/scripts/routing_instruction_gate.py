#!/usr/bin/env python3
"""Install or verify the mandatory workspace routing rule in every public unit (lite).

  python routing_instruction_gate.py            # verify only (exit 1 on failure)
  python routing_instruction_gate.py --apply    # insert or refresh the block, then verify
  python routing_instruction_gate.py --self-test

The lite plugin has two output layouts and the block names both: the audit
layout work/{domain}/ created by new-workspace-lite, and the client workspace
clients/<client>/ with workspace-routing.json created by new-client-lite.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
MARKER = "RAINMOJO_CLIENT_WORKSPACE_ROUTING_V1"
BLOCK = f"""<!-- {MARKER} -->
## Client workspace routing (mandatory for file changes)

Every generated file has exactly one home. Audit, keyword and comparison
outputs live under `work/{{domain}}/` created by `new-workspace-lite`
(`00-baseline/` first run, `01-current/` later runs, `02-fixes/`, `03-content/`,
`04-reports/`, `uploads/` read-only for user files); never invent another
top-level folder there. Content production and WordPress publishing use the
client workspace `clients/<client>/` created by `new-client-lite`: read
`workspace-routing.json` first, resolve every artifact with
`{{PLUGIN_ROOT}}/skills/rainmojo-so-lite/scripts/client_workspace.py route`, use the
most precise registered route, edit root files only when their exact filename is
in `root_policy.allowed_files`, treat `uploads/` as read-only, and when no route
fits use `create-work` then `route-work`; never construct a `work/<name>/...`
path by hand inside a client workspace. Never write generated files to the
plugin tree or the caller's working directory. Append one line to the
workspace's `CHANGELOG.md` or `log.md` after every write. Run
`client_workspace.py validate` before handing a client workspace over. Direct
CMS/API operations retain their own safety and verification gates.

"""

BLOCK_RE = re.compile(
    rf"<!-- {MARKER} -->\r?\n"
    r"## Client workspace routing \(mandatory for file changes\)\r?\n"
    r".*?and verification gates\.\r?\n\r?\n",
    re.DOTALL,
)
FORBIDDEN_ROUTING_TEXT = (
    "Save all generated files to `./clients/{domain}/`:",
    "Save to /tmp/",
    "Check for existing audit reports in current directory",
)


def targets(root: Path | None = None) -> list[Path]:
    root = root or PLUGIN_ROOT
    skill_files = [
        directory / "SKILL.md"
        for directory in sorted((root / "skills").iterdir())
        if directory.is_dir() and (directory / "SKILL.md").is_file()
    ]
    agent_files = sorted((root / "agents").glob("*.md")) if (root / "agents").is_dir() else []
    return skill_files + agent_files


def install_or_refresh(path: Path) -> bool:
    raw = path.read_bytes()
    bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
    payload = raw[len(bom):]
    newline = b"\r\n" if b"\r\n" in payload[:4096] else b"\n"
    block = BLOCK.replace("\n", newline.decode("ascii")).encode("utf-8")
    if MARKER.encode("ascii") in payload:
        decoded = payload.decode("utf-8")
        updated, count = BLOCK_RE.subn(block.decode("utf-8"), decoded)
        if count != 1:
            raise RuntimeError(f"Cannot refresh exactly one routing instruction block: {path}")
        updated_bytes = bom + updated.encode("utf-8")
        if updated_bytes == raw:
            return False
        path.write_bytes(updated_bytes)
        return True
    lines = payload.splitlines(keepends=True)
    delimiters = [index for index, line in enumerate(lines) if line.strip() == b"---"]
    if len(delimiters) < 2 or delimiters[0] != 0:
        raise RuntimeError(f"Missing YAML frontmatter delimiters: {path}")
    insert_at = delimiters[1] + 1
    head = b"".join(lines[:insert_at])
    if not head.endswith((b"\n", b"\r\n")):
        head += newline
    if insert_at < len(lines) and lines[insert_at].strip():
        block = newline + block
    updated = bom + head + block + b"".join(lines[insert_at:])
    path.write_bytes(updated)
    return True


def verify(root: Path | None = None) -> list[str]:
    root = root or PLUGIN_ROOT
    errors: list[str] = []
    normalized_block = BLOCK.replace("\r\n", "\n")
    for path in targets(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8-sig")
        matches = list(BLOCK_RE.finditer(text))
        if len(matches) != 1:
            errors.append(f"{rel}: routing block count={len(matches)}")
        elif matches[0].group(0).replace("\r\n", "\n") != normalized_block:
            errors.append(f"{rel}: routing block is stale")
        for forbidden in FORBIDDEN_ROUTING_TEXT:
            if forbidden in text:
                errors.append(f"{rel}: forbidden broad output directive {forbidden!r}")
    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "skills" / "demo-lite").mkdir(parents=True)
        (root / "agents").mkdir()
        skill = root / "skills" / "demo-lite" / "SKILL.md"
        skill.write_text("---\nname: demo-lite\ndescription: demo\n---\n# Demo\n\nbody\n", encoding="utf-8")
        agent = root / "agents" / "demo-agent-lite.md"
        agent.write_text("---\nname: demo-agent-lite\ndescription: demo\n---\r\n\r\n# Agent\r\n", encoding="utf-8", newline="")
        assert verify(root), "fresh files must fail verification"
        assert install_or_refresh(skill) and install_or_refresh(agent)
        assert not verify(root), verify(root)
        assert not install_or_refresh(skill), "second apply must be a no-op"
        text = skill.read_text(encoding="utf-8")
        assert text.count(MARKER) == 1 and text.index(MARKER) < text.index("# Demo")
        stale = text.replace("Every generated file has exactly one home.", "Old wording.")
        skill.write_text(stale, encoding="utf-8")
        assert any("stale" in e for e in verify(root))
        assert install_or_refresh(skill) and not verify(root)
    print("SELF-TEST PASS: install, refresh, stale detection, CRLF agent")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Insert the rule after YAML frontmatter where it is missing.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    changed: list[Path] = []
    if args.apply:
        changed = [path for path in targets() if install_or_refresh(path)]
    invalid = verify()
    if invalid:
        for error in invalid:
            print("INVALID", error)
        raise SystemExit(1)
    print(f"ROUTING_INSTRUCTION_GATE_OK targets={len(targets())} changed={len(changed)}")


if __name__ == "__main__":
    main()
