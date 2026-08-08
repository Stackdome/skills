#!/usr/bin/env bash
#
# PreToolUse hook for the Bash tool. Auto-approves ONLY a single, simple
# invocation of the `stackdome` CLI. Everything else is left alone — the
# script exits 0 with no output, which defers to Claude Code's normal
# permission prompt. Silence is the safe default: a missed auto-approval
# costs the user one extra prompt, a wrong auto-approval runs arbitrary code.
#
# What this does NOT do: judge the subcommand. Every `stackdome` verb is
# approved, `destroy` included. The skill grants `Bash(stackdome:*)` in its
# frontmatter, so a verb allow-list here would be overruled by that grant
# anyway — silence from this hook falls through to the normal permission
# flow, and the grant approves what lands there.
#
# What this DOES do: make sure the command really is just the stackdome
# binary and nothing else. `allowed-tools` matches a prefix against the whole
# command string, so both of these satisfy the grant while running something
# else entirely:
#   stackdome status; rm -rf ~
#   printf x # stackdome status
# Rejecting those is this hook's only job.
#
# Contract (Claude Code hooks reference, "PreToolUse"):
#   stdin:  {"tool_name": "Bash", "tool_input": {"command": "..."}, ...}
#   approve: {"hookSpecificOutput": {"hookEventName": "PreToolUse",
#             "permissionDecision": "allow", "permissionDecisionReason": "..."}}
#   defer:  exit 0, no stdout.
set -u

# No JSON parser, no decision. Guessing at the input shape is how a hook
# ends up approving something it never actually validated.
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

input="$(cat)"

# Only the Bash tool carries a shell command to reason about.
tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null)"
if [ "$tool_name" != "Bash" ]; then
  exit 0
fi

# Malformed JSON, or a Bash call with no command string: nothing safe to do.
command_str="$(printf '%s' "$input" | jq -r 'if (.tool_input.command | type) == "string" then .tool_input.command else empty end' 2>/dev/null)"
if [ -z "$command_str" ]; then
  exit 0
fi

# Emits the approval JSON and exits. The only exit path that produces output.
approve() {
  local reason="$1"
  jq -n --arg reason "$reason" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "allow", permissionDecisionReason: $reason}}'
  exit 0
}

# --- Step 1: build the "skeleton" -----------------------------------------
# Strip every single-quoted span, double-quoted span, and backslash-escaped
# character. Metacharacters INSIDE quotes are inert data to the shell (a
# secret value containing ';' is just a string); the same characters at top
# level are control syntax. Only the skeleton needs checking for syntax.
skeleton=""
in_single=0
in_double=0
len=${#command_str}
i=0
bs=$'\\'  # one literal backslash char, via ANSI-C quoting to keep quoting unambiguous
while [ "$i" -lt "$len" ]; do
  c="${command_str:$i:1}"

  if [ "$in_single" -eq 1 ]; then
    # Nothing is special inside single quotes, not even backslash — only
    # the closing quote ends the span.
    [ "$c" = "'" ] && in_single=0
    i=$((i + 1))
    continue
  fi

  if [ "$in_double" -eq 1 ]; then
    if [ "$c" = "$bs" ]; then
      # Backslash escapes the next character even inside double quotes
      # (e.g. \" or \$); consume both without adding them to the skeleton.
      # Nothing after it means the command does not parse — see below.
      [ $((i + 1)) -lt "$len" ] || exit 0
      i=$((i + 2))
      continue
    fi
    [ "$c" = '"' ] && in_double=0
    i=$((i + 1))
    continue
  fi

  # Top level: quotes open a span, backslash escapes exactly one character.
  case "$c" in
    "'")
      in_single=1
      i=$((i + 1))
      continue
      ;;
    '"')
      in_double=1
      i=$((i + 1))
      continue
      ;;
  esac
  if [ "$c" = "$bs" ]; then
    # A trailing backslash escapes nothing: bash reads it as a line
    # continuation and waits for more input, so what we just parsed is not
    # the whole command. Approving it would mean vouching for text we
    # never saw — defer, same as an unterminated quote.
    [ $((i + 1)) -lt "$len" ] || exit 0
    i=$((i + 2))
    continue
  fi

  skeleton="${skeleton}${c}"
  i=$((i + 1))
done

# A quote that never closed means the command can't be reasoned about at
# all — defer rather than guess what the missing half would have done.
if [ "$in_single" -eq 1 ] || [ "$in_double" -eq 1 ]; then
  exit 0
fi

# --- Step 2: reject any control syntax left in the skeleton ----------------
# ; | & < > ( ) { } chain, pipe, background, redirect, or group commands.
# # starts a comment, hiding real content from a naive prefix check.
# ` and $ enable command/parameter substitution — a second command running
# under the cover of the first. A literal newline is a statement separator,
# same as ';'.
if printf '%s' "$skeleton" | grep -qE '[;|&<>#(){}`$]'; then
  exit 0
fi
case "$skeleton" in
  *$'\n'*) exit 0 ;;
esac

# --- Step 3: the command must be a single, bare `stackdome` invocation -----
# Trim leading whitespace, then take everything up to the next whitespace
# (or end of string) as the first word.
trimmed="${command_str#"${command_str%%[![:space:]]*}"}"
first_word="${trimmed%%[[:space:]]*}"

# Must be exactly "stackdome" — not "stackdome-evil" (substring match),
# not "./stackdome" or "/tmp/stackdome" (a path can point anywhere, and a
# relative path depends on an attacker-influenced cwd).
if [ "$first_word" != "stackdome" ]; then
  exit 0
fi

# Resolve the binary via PATH and require it to actually exist, so a name
# that isn't really an installed executable never gets approved.
if ! command -v stackdome >/dev/null 2>&1; then
  exit 0
fi

approve "Single stackdome CLI invocation."
