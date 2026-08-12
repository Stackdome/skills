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
CLOUD_QUOTA_NOUN = re.compile(
    r"\b(?:stacks?|apps?|resources?|replicas?|volumes?|postgres|builds?|"
    r"registr(?:y|ies)|leases?|cpu|memory|storage|disk|ram|cores?|[gmt]b)\b",
    re.IGNORECASE,
)
NUMERIC_VALUE = re.compile(r"\b\d+(?:\.\d+)?\b")
POSITIVE_PASSWORD_GUIDANCE = re.compile(
    r"\b(?:ask(?:ing)?\s+(?:the\s+)?user\s+(?:for|to\s+(?:paste|provide|enter))|"
    r"accept(?:ing)?|paste|store|use)\b[^.\n]{0,100}\b(?:the\s+)?"
    r"(?:user(?:['’]s)?\s+|their\s+)?password\b",
    re.IGNORECASE,
)
PASSWORD_PROHIBITION = re.compile(
    r"\b(?:never|do\s+not|don't|must\s+not)\b[^.\n]{0,100}"
    r"\b(?:ask|accept|paste|store|use)\b[^.\n]{0,100}\bpassword\b",
    re.IGNORECASE,
)


def line_for(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def semantic_contract_errors(text: str) -> list[str]:
    requirements = (
        (
            "missing policy that Cloud custom-domain registration is disabled or self-hosted only",
            r"\b(?:stackdome\s+)?cloud\b[^\n]{0,180}\bcustom[- ]domains?\b[^\n]{0,160}"
            r"\b(?:disabled|unavailable|not supported|self[- ]hosted(?:\s+only)?)\b",
        ),
        (
            "missing policy that Cloud limits do not apply to self-hosted instances",
            r"\bcloud\b[^\n]{0,100}\b(?:limits?|quotas?)\b[^\n]{0,100}"
            r"\b(?:do\s+not|don't|never|not)\s+apply\b[^\n]{0,100}\bself[- ]host(?:ed)?\b",
        ),
        (
            "missing ttl.sh warning and explicit confirmation for the exact push",
            r"\b(?:exact\s+)?git\s+push\b[^\n]{0,200}\bttl\.sh\b(?=[^\n]{0,200}"
            r"\b(?:warn|warning)\b)(?=[^\n]{0,200}\bexplicit\s+confirmation\b)[^\n]*",
        ),
        (
            "missing CLI-first, documented stackdome api-second policy",
            r"\b(?:use|prefer)\b[^\n]{0,80}\b(?:documented\s+)?cli\b[^\n]{0,80}\bfirst\b"
            r"[^\n]{0,180}\bstackdome\s+api\b[^\n]{0,120}\b(?:only|when)\b"
            r"[^\n]{0,120}\b(?:documented|without[^\n]{0,40}\bcli\b)\b",
        ),
    )
    return [message for message, pattern in requirements if not re.search(pattern, text, re.IGNORECASE)]


def cloud_quota_errors(text: str) -> list[str]:
    errors: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if (
            re.search(r"\bcloud\b", line, re.IGNORECASE)
            and NUMERIC_VALUE.search(line)
            and CLOUD_QUOTA_NOUN.search(line)
        ):
            errors.append(f"numeric Cloud quota or resource claim at combined skill line {number}: {line!r}")
    return errors


def password_guidance_errors(text: str) -> list[str]:
    errors: list[str] = []
    for number, sentence in enumerate(re.split(r"(?<=[.!?])\s+", text), start=1):
        if POSITIVE_PASSWORD_GUIDANCE.search(sentence) and not PASSWORD_PROHIBITION.search(sentence):
            errors.append(f"positive password-handling guidance in sentence {number}: {sentence!r}")
    return errors


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

    errors.extend(semantic_contract_errors(published_text))
    errors.extend(cloud_quota_errors(published_text))
    errors.extend(password_guidance_errors(published_text))

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
