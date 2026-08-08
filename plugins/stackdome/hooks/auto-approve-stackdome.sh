#!/usr/bin/env bash
#
# PreToolUse hook for the Bash tool. Approves a command that is one plain
# invocation of the `stackdome` binary. Gates the shape of the command, not
# the subcommand — every verb approves, `destroy` included.
#
# These satisfy a `Bash(stackdome:*)` prefix match while running something
# else, and are what this hook exists to reject:
#   stackdome status; rm -rf ~
#   printf x # stackdome status
#
# Contract (Claude Code hooks reference, "PreToolUse"):
#   stdin:  {"tool_name": "Bash", "tool_input": {"command": "..."}, ...}
#   approve: {"hookSpecificOutput": {"hookEventName": "PreToolUse",
#             "permissionDecision": "allow", "permissionDecisionReason": "..."}}
#   defer:  exit 0, no stdout.
set -u

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

input="$(cat)"

tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null)"
if [ "$tool_name" != "Bash" ]; then
  exit 0
fi

command_str="$(printf '%s' "$input" | jq -r 'if (.tool_input.command | type) == "string" then .tool_input.command else empty end' 2>/dev/null)"
if [ -z "$command_str" ]; then
  exit 0
fi

approve() {
  local reason="$1"
  jq -n --arg reason "$reason" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "allow", permissionDecisionReason: $reason}}'
  exit 0
}

# --- Step 1: build the "skeleton" -----------------------------------------
# Drop every quoted span and escaped character. Metacharacters inside quotes
# are inert data to the shell; only what survives is control syntax.
skeleton=""
in_single=0
in_double=0
len=${#command_str}
i=0
bs=$'\\'  # one literal backslash char, via ANSI-C quoting to keep quoting unambiguous
while [ "$i" -lt "$len" ]; do
  c="${command_str:$i:1}"

  if [ "$in_single" -eq 1 ]; then
    # Not even backslash is special inside single quotes.
    [ "$c" = "'" ] && in_single=0
    i=$((i + 1))
    continue
  fi

  if [ "$in_double" -eq 1 ]; then
    if [ "$c" = "$bs" ]; then
      # Backslash still escapes inside double quotes (\" or \$).
      [ $((i + 1)) -lt "$len" ] || exit 0
      i=$((i + 2))
      continue
    fi
    [ "$c" = '"' ] && in_double=0
    i=$((i + 1))
    continue
  fi

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
    # A trailing backslash is a line continuation: more command is coming
    # that we never saw. Defer, same as an unterminated quote.
    [ $((i + 1)) -lt "$len" ] || exit 0
    i=$((i + 2))
    continue
  fi

  skeleton="${skeleton}${c}"
  i=$((i + 1))
done

if [ "$in_single" -eq 1 ] || [ "$in_double" -eq 1 ]; then
  exit 0
fi

# --- Step 2: reject any control syntax left in the skeleton ----------------
#   ; | & < > ( ) { }  chain, pipe, background, redirect, group
#   #                  comment, hides the rest of the line
#   ` $                substitution, a second command under cover of the first
#   newline            statement separator, same as ';'
if printf '%s' "$skeleton" | grep -qE '[;|&<>#(){}`$]'; then
  exit 0
fi
case "$skeleton" in
  *$'\n'*) exit 0 ;;
esac

# --- Step 3: the first word must be the `stackdome` binary itself ----------
trimmed="${command_str#"${command_str%%[![:space:]]*}"}"
first_word="${trimmed%%[[:space:]]*}"

# Exactly "stackdome" — not "stackdome-evil", and not "./stackdome" or
# "/tmp/stackdome", which can point at any file.
if [ "$first_word" != "stackdome" ]; then
  exit 0
fi

if ! command -v stackdome >/dev/null 2>&1; then
  exit 0
fi

approve "Single stackdome CLI invocation."
