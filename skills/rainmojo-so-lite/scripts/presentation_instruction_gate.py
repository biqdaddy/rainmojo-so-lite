#!/usr/bin/env python3
"""Install or verify the Two-Tier presentation rule in every public unit (lite), and
enforce the no-emoji policy on public instruction files and widget assets.

  python presentation_instruction_gate.py           # verify only (exit 1 on failure)
  python presentation_instruction_gate.py --apply   # insert or refresh the block, then verify
  python presentation_instruction_gate.py --self-test

The block is inserted directly after the client-workspace routing block
(RAINMOJO_CLIENT_WORKSPACE_ROUTING_V1) so every public SKILL.md and agent file
carries both mandatory layers in a fixed order. Pure ASCII by design.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
CUSTOM_ROOT = PLUGIN_ROOT / "skills" / "rainmojo-so-lite"
MODES_PATH = CUSTOM_ROOT / "reference" / "frameworks" / "presentation-modes.json"
ROUTING_MARKER = "RAINMOJO_CLIENT_WORKSPACE_ROUTING_V1"
MARKER = "RAINMOJO_PRESENTATION_LAYER_V1"
BLOCK = f"""<!-- {MARKER} -->
## Presentation (Two-Tier, 7 modes)

Answer in the response mode that matches the request
(`{{PLUGIN_ROOT}}/skills/rainmojo-so-lite/_base/presentation-scaffold.md`): quick fact,
how-to, comparison, troubleshoot, audit, deployable, always closing with next
steps. A run that writes a deliverable ends with a Tier 1 card built from
`summary.json` (`templates/widget/summary.schema.json`) and rendered with
`{{PLUGIN_ROOT}}/skills/rainmojo-so-lite/scripts/present.py --target auto`, then hands
off to the Tier 2 file, which stays complete and unchanged. Lite cards carry
counts of checks passed, never a weighted score. Every card value is copied
from the deliverable; unmeasured values show as could not verify. No emoji on
any surface; the glyph allowlist applies to chat and Markdown only.

"""

BLOCK_RE = re.compile(
    rf"<!-- {MARKER} -->\r?\n"
    r"## Presentation \(Two-Tier, 7 modes\)\r?\n"
    r".*?applies to chat and Markdown only\.\r?\n\r?\n",
    re.DOTALL,
)
ROUTING_END_RE = re.compile(
    rf"<!-- {ROUTING_MARKER} -->\r?\n.*?and verification gates\.\r?\n\r?\n",
    re.DOTALL,
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


def widget_assets() -> list[Path]:
    out = []
    for pattern in ("templates/widget/**/*", "_base/presentation-scaffold.md",
                    "reference/frameworks/presentation-modes.json", "scripts/present.py",
                    "scripts/present_html.py", "scripts/build_summary.py"):
        for p in CUSTOM_ROOT.glob(pattern):
            if p.is_file():
                out.append(p)
    return sorted(set(out))


def glyph_policy() -> tuple[set[str], list[tuple[int, int]]]:
    policy = json.loads(MODES_PATH.read_text(encoding="utf-8"))["glyph_policy"]
    allow = set(policy["chat_and_markdown_allowlist"])
    ranges = [(int(lo, 16), int(hi, 16)) for lo, hi in policy["forbidden_ranges"]]
    return allow, ranges


def pictographs(text: str, allow: set[str], ranges: list[tuple[int, int]]) -> list[str]:
    found: list[str] = []
    for ch in text:
        if ch in allow:
            continue
        cp = ord(ch)
        for lo, hi in ranges:
            if lo <= cp <= hi:
                found.append("U+%04X" % cp)
                break
    return sorted(set(found))


def install_or_refresh(path: Path) -> bool:
    raw = path.read_bytes()
    bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
    payload = raw[len(bom):]
    newline = b"\r\n" if b"\r\n" in payload[:4096] else b"\n"
    block = BLOCK.replace("\n", newline.decode("ascii")).encode("utf-8")
    decoded = payload.decode("utf-8")
    if MARKER in decoded:
        updated, count = BLOCK_RE.subn(block.decode("utf-8"), decoded)
        if count != 1:
            raise RuntimeError(f"Cannot refresh exactly one presentation block: {path}")
        updated_bytes = bom + updated.encode("utf-8")
        if updated_bytes == raw:
            return False
        path.write_bytes(updated_bytes)
        return True
    m = ROUTING_END_RE.search(decoded)
    if m:
        insert_at = m.end()
        updated = decoded[:insert_at] + block.decode("utf-8") + decoded[insert_at:]
    else:
        lines = payload.splitlines(keepends=True)
        delimiters = [i for i, line in enumerate(lines) if line.strip() == b"---"]
        if len(delimiters) < 2 or delimiters[0] != 0:
            raise RuntimeError(f"Missing YAML frontmatter delimiters: {path}")
        at = delimiters[1] + 1
        head = b"".join(lines[:at])
        if not head.endswith((b"\n", b"\r\n")):
            head += newline
        extra = newline if at < len(lines) and lines[at].strip() else b""
        updated = (head + extra + block + b"".join(lines[at:])).decode("utf-8")
    path.write_bytes(bom + updated.encode("utf-8"))
    return True


def verify(root: Path | None = None, check_assets: bool = True) -> list[str]:
    root = root or PLUGIN_ROOT
    errors: list[str] = []
    normalized_block = BLOCK.replace("\r\n", "\n")
    allow, ranges = glyph_policy()
    for path in targets(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8-sig")
        matches = list(BLOCK_RE.finditer(text))
        if len(matches) != 1:
            errors.append(f"{rel}: presentation block count={len(matches)}")
        elif matches[0].group(0).replace("\r\n", "\n") != normalized_block:
            errors.append(f"{rel}: presentation block is stale")
        routing = list(ROUTING_END_RE.finditer(text))
        if routing and matches and matches[0].start() < routing[0].end():
            errors.append(f"{rel}: presentation block must follow the routing block")
        bad = pictographs(text, allow, ranges)
        if bad:
            errors.append(f"{rel}: emoji or pictograph in public instruction file: {' '.join(bad)}")
    if check_assets:
        for path in widget_assets():
            rel = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8-sig")
            bad = pictographs(text, allow, ranges)
            if bad:
                errors.append(f"{rel}: emoji or pictograph in widget asset: {' '.join(bad)}")
            if path.suffix == ".py" and any(ord(c) > 127 for c in text):
                errors.append(f"{rel}: generator must be pure ASCII")
    return errors


def self_test() -> int:
    import routing_instruction_gate as routing
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "skills" / "demo-lite").mkdir(parents=True)
        (root / "agents").mkdir()
        skill = root / "skills" / "demo-lite" / "SKILL.md"
        skill.write_text("---\nname: demo-lite\ndescription: demo\n---\n# Demo\n\nbody\n", encoding="utf-8")
        routing.install_or_refresh(skill)
        assert verify(root, check_assets=False), "fresh file must fail verification"
        assert install_or_refresh(skill)
        assert not verify(root, check_assets=False), verify(root, check_assets=False)
        text = skill.read_text(encoding="utf-8")
        assert text.index(ROUTING_MARKER) < text.index(MARKER) < text.index("# Demo")
        assert not install_or_refresh(skill), "second apply must be a no-op"
        skill.write_text(text + "\nrocket " + chr(0x1F680) + "\n", encoding="utf-8")
        assert any("emoji" in e for e in verify(root, check_assets=False))
    allow, ranges = glyph_policy()
    assert pictographs("ok " + chr(0x2705), allow, ranges) == ["U+2705"]
    assert pictographs("bar [####----] " + chr(0x2713), allow, ranges) == []
    print("SELF-TEST PASS: order after routing block, refresh no-op, emoji detection")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Insert or refresh the block where needed.")
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
    print(f"PRESENTATION_INSTRUCTION_GATE_OK targets={len(targets())} changed={len(changed)}")


if __name__ == "__main__":
    main()
