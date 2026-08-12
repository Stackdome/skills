#!/usr/bin/env python3
"""Validate the published Stackdome skill against its supported contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REQUIRED_REFERENCES = {
    "onboarding.md",
    "stackfiles-and-deploy.md",
    "observe-and-debug.md",
    "resources.md",
    "api-recipes.md",
}

REQUIRED_PHRASES = (
    "/sign-up",
    "/sign-in",
    "/settings/api-tokens",
    "Full access",
    "git remote -v",
    "ttl.sh",
    "explicit confirmation",
    "self-host",
    "stackdome api",
)

FORBIDDEN_PATTERNS = (
    r"stackdome\s+token\s+(?:list|create|delete|scopes)",
    r"stackdome\s+secret\s+(?:list|info|create|set|delete)",
    r"stackdome\s+build\s+(?:list|info|logs)",
    r"stackdome\s+release\s+(?:list|info|events|cancel|rollback)",
    r"stackdome\s+addon\s+postgres",
    r"stackdome\s+volume\s+(?:list|create|delete)",
    r"stackdome\s+stackfile\s+(?:schema|export)",
    r"stackdome\s+config\s+(?:view|set-context|set-stack)",
    r"--email|--password|email and password login",
)

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "plugins/stackdome/skills/use-stackdome/SKILL.md"
MANIFEST_PATHS = (
    ROOT / "plugins/stackdome/.claude-plugin/plugin.json",
    ROOT / "plugins/stackdome/.codex-plugin/plugin.json",
    ROOT / "plugins/stackdome/.cursor-plugin/plugin.json",
    ROOT / "plugins/stackdome/.grok-plugin/plugin.json",
)
REFERENCE_LINK = re.compile(r"\[[^]]+\]\((references/[^)#]+\.md)(?:#[^)]*)?\)")
NUMERIC_CLOUD_QUOTA = re.compile(
    r"\bcloud\b(?=[^\n]{0,120}\b(?:quota|limit|ceiling|maximum|max|capacity)\b)"
    r"(?=[^\n]{0,120}\b\d+(?:\.\d+)?\b)[^\n]*"
    r"|\b\d+(?:\.\d+)?\b(?=[^\n]{0,120}\bcloud\b)"
    r"(?=[^\n]{0,160}\b(?:quota|limit|ceiling|maximum|max|capacity)\b)[^\n]*",
    re.IGNORECASE,
)


def line_for(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def main() -> int:
    errors: list[str] = []
    skill_text = SKILL_PATH.read_text(encoding="utf-8")
    linked_references: set[str] = set()
    combined_text = [skill_text]

    for match in REFERENCE_LINK.finditer(skill_text):
        relative_path = match.group(1)
        reference_path = SKILL_PATH.parent / relative_path
        linked_references.add(Path(relative_path).name)
        if not reference_path.is_file():
            errors.append(f"reference link does not resolve: {relative_path}")
            continue
        combined_text.append(reference_path.read_text(encoding="utf-8"))

    for reference in sorted(REQUIRED_REFERENCES - linked_references):
        errors.append(f"missing required direct reference link: references/{reference}")

    published_text = "\n".join(combined_text)
    for phrase in REQUIRED_PHRASES:
        if phrase not in published_text:
            errors.append(f"missing required phrase: {phrase}")

    for pattern in FORBIDDEN_PATTERNS:
        match = re.search(pattern, published_text, flags=re.IGNORECASE)
        if match:
            errors.append(
                f"forbidden command or login guidance at combined skill line "
                f"{line_for(published_text, match.start())}: {match.group(0)!r}"
            )

    for match in NUMERIC_CLOUD_QUOTA.finditer(published_text):
        errors.append(
            f"numeric Cloud quota or limit claim at combined skill line "
            f"{line_for(published_text, match.start())}: {match.group(0)!r}"
        )

    for manifest_path in MANIFEST_PATHS:
        try:
            version = json.loads(manifest_path.read_text(encoding="utf-8")).get("version")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot read manifest {manifest_path.relative_to(ROOT)}: {exc}")
            continue
        if version != "0.2.0":
            errors.append(
                f"manifest {manifest_path.relative_to(ROOT)} must have version 0.2.0, "
                f"found {version!r}"
            )

    if errors:
        print("Published Stackdome skill contract violations:", file=sys.stderr)
        print(*(f"- {error}" for error in errors), sep="\n", file=sys.stderr)
        return 1

    print("Published Stackdome skill contract is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
