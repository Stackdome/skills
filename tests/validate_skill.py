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
RESOURCE_NOUN = r"(?:stacks?|apps?|resources?|replicas?|volumes?|postgres|builds?|"
RESOURCE_NOUN += r"registr(?:y|ies)|leases?|cpu|memory|storage|disk|ram|cores?|[gmt]b)"
RESOURCE_MODIFIER = r"[a-z][a-z0-9-]*"
RESOURCE_VALUE = rf"\d+(?:\.\d+)?(?:\s+(?:{RESOURCE_MODIFIER}\s+){{0,3}}|\s*){RESOURCE_NOUN}\b"
CLOUD_QUOTA_ASSERTION = re.compile(
    rf"\b(?:supports?|allows?|permits?)\s+only\s+{RESOURCE_VALUE}"
    rf"|\b(?:is\s+)?(?:limited|capped)\s+to\s+{RESOURCE_VALUE}"
    rf"|\b(?:has\s+(?:a\s+)?(?:max(?:imum)?|limit|quota|cap)\s+(?:of\s+)?|"
    rf"(?:max(?:imum)?|limit|quota|cap)\s+(?:is|of)\s+){RESOURCE_VALUE}"
    rf"|\b(?:at\s+most|no\s+more\s+than|up\s+to)\s+{RESOURCE_VALUE}"
    rf"|\b(?:requires?|allows?|permits?)\s+exactly\s+{RESOURCE_VALUE}",
    re.IGNORECASE,
)
PASSWORD_TERM = r"\bpasswords?\b"
PASSWORD_ACTION = re.compile(
    r"\b(?:ask(?:s|ed|ing)?|accept(?:s|ed|ing)?|paste(?:s|d|ing)?|store(?:s|d|ing)?|"
    r"use(?:s|d|ing)?|typ(?:e|es|ed|ing)|enter(?:s|ed|ing)?|provid(?:e|es|ed|ing)|"
    r"suppl(?:y|ies|ied|ying)|handle(?:s|d|ing)?|solicit(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
NEGATION = re.compile(
    r"\b(?:never|do\s+not|don't|must\s+not|should\s+not|cannot|can't|without)\b",
    re.IGNORECASE,
)
SCOPE_BOUNDARY = re.compile(
    r"(?:;|—|--|\b(?:but|however|except|yet|although|though|nevertheless|nonetheless)\b)",
    re.IGNORECASE,
)
NEGATIVE_COORDINATION = re.compile(r"\b(?:or|nor)\b", re.IGNORECASE)
PASSWORD_PRONOUN = re.compile(r"\b(?:it|them|their)\b", re.IGNORECASE)


def line_for(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def global_policy_errors(text: str) -> list[str]:
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
            r"\b(?:exact\s+)?docker\s+push\b[^\n]{0,200}\bttl\.sh\b"
            r"(?=[^\n]{0,200}\b(?:warn|warning)\b)"
            r"(?=[^\n]{0,200}\bexplicit\s+confirmation\b)"
            r"(?=[^\n]{0,200}\b(?:privacy|security|public|expos(?:e|es|ure))\b)[^\n]*",
        ),
        (
            "missing CLI-first, documented stackdome api-second policy",
            r"\b(?:use|prefer)\b[^\n]{0,80}\b(?:documented\s+)?cli\b[^\n]{0,80}\bfirst\b"
            r"[^\n]{0,180}\bstackdome\s+api\b[^\n]{0,120}\b(?:only|when)\b"
            r"[^\n]{0,120}\b(?:documented|without[^\n]{0,40}\bcli\b)\b",
        ),
    )
    errors = [
        message
        for message, pattern in requirements
        if not re.search(pattern, text, re.IGNORECASE)
    ]
    if re.search(r"\bgit\s+push\b[^\n]{0,200}\bttl\.sh\b", text, re.IGNORECASE):
        errors.append("Git push cannot publish an OCI image to ttl.sh; require docker push")
    return errors


def cloud_quota_errors(text: str) -> list[str]:
    errors: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if re.search(r"\bcloud\b", line, re.IGNORECASE) and CLOUD_QUOTA_ASSERTION.search(line):
            errors.append(f"numeric Cloud quota or resource claim at combined skill line {number}: {line!r}")
    return errors


def password_guidance_errors(text: str) -> list[str]:
    errors: list[str] = []
    for number, sentence in enumerate(re.split(r"(?<=[.!?])\s+", text), start=1):
        password_matches = list(re.finditer(PASSWORD_TERM, sentence, re.IGNORECASE))
        if not password_matches:
            continue

        actions = list(PASSWORD_ACTION.finditer(sentence))
        first_password = password_matches[0]
        actions_before_password = [
            action
            for action in actions
            if action.start() < first_password.start()
            and first_password.start() - action.end() <= 100
        ]
        pre_password_negative_scope = False
        previous_action_end = 0
        for action in actions_before_password:
            action_object = sentence[action.end() : first_password.end()]
            if re.search(r"\bnot\s+(?:a\s+)?passwords?\b", action_object, re.IGNORECASE):
                continue
            prefix = sentence[: action.start()]
            boundaries = list(SCOPE_BOUNDARY.finditer(prefix))
            scope_prefix = prefix[boundaries[-1].end() :] if boundaries else prefix
            fresh_negation = bool(NEGATION.search(scope_prefix))
            continued_prohibition = (
                pre_password_negative_scope
                and not SCOPE_BOUNDARY.search(sentence[previous_action_end : action.start()])
            )
            if not fresh_negation and not continued_prohibition:
                errors.append(
                    f"positive password-handling guidance in sentence {number}: {sentence!r}"
                )
                break
            pre_password_negative_scope = fresh_negation or continued_prohibition
            previous_action_end = action.end()
        else:
            initial_prohibition = pre_password_negative_scope

            negative_scope_active = initial_prohibition
            previous_handling_end = first_password.end()
            for action in actions:
                if action.start() < first_password.start():
                    continue

                preceding_password = next(
                    (
                        password
                        for password in reversed(password_matches)
                        if password.end() <= action.start()
                    ),
                    None,
                )
                if preceding_password is None:
                    continue
                following_password = next(
                    (
                        password
                        for password in password_matches
                        if 0 <= password.start() - action.end() <= 100
                    ),
                    None,
                )
                action_tail = sentence[action.end() : action.end() + 100]
                intervening = sentence[preceding_password.end() : action.start()]
                passive_reference = bool(
                    re.fullmatch(
                        r"\s*(?:(?:must|should|can|cannot|can't|may|is|are|be|never|not)\s+)*",
                        intervening,
                        re.IGNORECASE,
                    )
                )
                if (
                    following_password is None
                    and not PASSWORD_PRONOUN.search(action_tail)
                    and not passive_reference
                ):
                    continue

                coordination = sentence[previous_handling_end : action.start()]
                boundaries = list(SCOPE_BOUNDARY.finditer(intervening))
                scope_intervening = (
                    intervening[boundaries[-1].end() :] if boundaries else intervening
                )
                fresh_negation = bool(NEGATION.search(scope_intervening))
                negative_coordination = (
                    negative_scope_active
                    and bool(NEGATIVE_COORDINATION.search(coordination))
                    and not SCOPE_BOUNDARY.search(coordination)
                )
                if not fresh_negation and not negative_coordination:
                    errors.append(
                        f"positive password-handling guidance in sentence {number}: {sentence!r}"
                    )
                    break
                negative_scope_active = fresh_negation or negative_coordination
                previous_handling_end = action.end()
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

    errors.extend(global_policy_errors(skill_text))
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
