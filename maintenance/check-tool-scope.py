#!/usr/bin/env python3
"""Check each skill's `permissions` list against what its bundled scripts do.

ClawHub scans skills with SkillSpector, whose least-privilege rules compare a
skill's declared tool scope with capabilities found in its code. A script with
no declaration is a Medium finding (LP3), a capability missing from the
declaration a High (LP1), and a declared capability with no code behind it a
Low (LP4). This check fails on all three, so the list has to match exactly.

The patterns are a copy of SkillSpector's capability patterns. The publisher
runs the scanner itself before a release; this is the fast check that runs on
every push.
"""

import re
import sys
from pathlib import Path

CAPABILITY_PATTERNS = {
    "shell": [r"subprocess", r"Popen", r"os\.system", r"os\.popen", r"os\.exec",
              r"\bcurl\b", r"\bwget\b", r"\bchmod\b"],
    "network": [r"\bhttpx\b", r"\brequests\b", r"\burllib\b", r"\baiohttp\b",
                r"socket\.connect", r"fetch\(", r"XMLHttpRequest"],
    "file_read": [r"open\s*\([^)]{0,200}['\"][^'\"]{0,8}r['\"]", r"\.read_text\(",
                  r"\.read_bytes\(", r"os\.listdir", r"os\.walk", r"glob\.glob"],
    "file_write": [r"open\s*\([^)]{0,200}['\"][^'\"]{0,8}[wa]['\"]", r"\.write_text\(",
                   r"\.write_bytes\(", r"shutil\.copy", r"os\.rename", r"os\.mkdir"],
    "env": [r"os\.environ", r"os\.getenv", r"process\.env", r"\bdotenv\b"],
    "mcp": [r"create_session", r"MCPClient", r"mcp\.client"],
}
COMPILED = {name: [re.compile(p, re.IGNORECASE) for p in patterns]
            for name, patterns in CAPABILITY_PATTERNS.items()}
SCRIPT_SUFFIXES = {".py", ".sh", ".js", ".mjs", ".cjs", ".ts"}


def detected_capabilities(skill_dir):
    found = set()
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.suffix not in SCRIPT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, patterns in COMPILED.items():
            if any(p.search(text) for p in patterns):
                found.add(name)
    return found


def declared_permissions(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError(f"{skill_md}: no frontmatter")
    line = re.search(r"^permissions:\s*\[(.*)\]\s*$", match.group(1), re.MULTILINE)
    if not line:
        return set()
    return {item.strip() for item in line.group(1).split(",") if item.strip()}


def main(root):
    failed = False
    for skill_dir in sorted(Path(root).iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        detected = detected_capabilities(skill_dir)
        declared = declared_permissions(skill_md)
        if detected == declared:
            continue
        failed = True
        print(f"ERROR: {skill_dir.name}: permissions {sorted(declared)} do not match "
              f"what its scripts do {sorted(detected)}", file=sys.stderr)
        if detected - declared:
            print(f"  undeclared (a High finding): {sorted(detected - declared)}",
                  file=sys.stderr)
        if declared - detected:
            print(f"  declared but unused (a Low finding): {sorted(declared - detected)}",
                  file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "skills"))
