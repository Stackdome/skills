#!/usr/bin/env bash
#
# PreToolUse hook for the Bash tool. Auto-approves ONLY a single, simple,
# READ-ONLY invocation of the `stackdome` CLI. Everything else is left
# alone — the script exits 0 with no output, which defers to Claude Code's
# normal permission prompt. Silence is the safe default: a missed
# auto-approval costs the user one extra prompt, a wrong auto-approval runs
# arbitrary code (or destroys something irreversible).
#
# Why this exists: the skill grants `allowed-tools: Bash(stackdome:*)`, but
# that's prefix/substring matching against the WHOLE command string. Both of
# these start with (or contain) the trusted token yet run something else:
#   stackdome status; rm -rf ~
#   printf x # stackdome status
# so prefix matching alone cannot be trusted to gate approval.
#
# An approval here covers the WHOLE command, and there's no walking it back
# once Claude Code has run it — so beyond just being a well-formed single
# `stackdome` call, the command must also be read-only. `stackdome status`
# and `stackdome destroy -y` are both "a single simple stackdome call"; only
# one of them can be undone if the agent was wrong to run it. Everything
# that mutates or destroys state stays behind the normal prompt.
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

# Resolve the binary via PATH and require it to actually exist. This is a
# sanity check, not the security boundary above — it just avoids approving
# a call to a name that isn't really an installed executable.
if ! command -v stackdome >/dev/null 2>&1; then
  exit 0
fi

# --- Step 4: tokenize into words (quotes/escapes resolved) -----------------
# The skeleton above is deliberately lossy (it drops quoted and escaped
# characters outright) — good enough to spot stray metacharacters, but not
# a trustworthy word list: it can merge or mangle tokens. Re-walk the same
# command_str, this time keeping every literal character, so a quoted value
# like --data '... --help ...' stays inside ONE token instead of leaking a
# standalone --help word that could spoof the check below.
words=()
tok=""
have_tok=0
in_single=0
in_double=0
i=0
while [ "$i" -lt "$len" ]; do
  c="${command_str:$i:1}"

  if [ "$in_single" -eq 1 ]; then
    if [ "$c" = "'" ]; then
      in_single=0
    else
      tok="${tok}${c}"
    fi
    i=$((i + 1))
    continue
  fi

  if [ "$in_double" -eq 1 ]; then
    if [ "$c" = "$bs" ]; then
      tok="${tok}${command_str:$((i + 1)):1}"
      i=$((i + 2))
      continue
    fi
    if [ "$c" = '"' ]; then
      in_double=0
    else
      tok="${tok}${c}"
    fi
    i=$((i + 1))
    continue
  fi

  case "$c" in
    "'")
      in_single=1
      have_tok=1
      i=$((i + 1))
      continue
      ;;
    '"')
      in_double=1
      have_tok=1
      i=$((i + 1))
      continue
      ;;
    [[:space:]])
      if [ "$have_tok" -eq 1 ] || [ -n "$tok" ]; then
        words+=("$tok")
      fi
      tok=""
      have_tok=0
      i=$((i + 1))
      continue
      ;;
  esac
  if [ "$c" = "$bs" ]; then
    tok="${tok}${command_str:$((i + 1)):1}"
    i=$((i + 2))
    continue
  fi

  tok="${tok}${c}"
  have_tok=1
  i=$((i + 1))
done
if [ "$have_tok" -eq 1 ] || [ -n "$tok" ]; then
  words+=("$tok")
fi

# A bare `stackdome` with nothing after it does nothing.
n=${#words[@]}
if [ "$n" -le 1 ]; then
  approve "Bare stackdome invocation with no subcommand."
fi

# --- Step 5: resolve the verb, skipping recognized global flags ------------
# Global flags can appear before the subcommand (stackdome -o json status).
# -o takes a value, --no-color doesn't. Any other leading flag means we
# can't confidently say where the verb starts — defer rather than guess.
#
# --help/-h is tracked here rather than decided here: whether it's harmless
# depends on the verb it's attached to (below), not on its own presence. The
# CLI itself short-circuits on --help before running a subcommand, but this
# hook's approval can't lean on that — a future subcommand that parses
# --help differently would turn a "harmless" case into a live bypass.
verb=""
subverb=""
saw_help=0
idx=1
while [ "$idx" -lt "$n" ]; do
  word="${words[$idx]}"
  case "$word" in
    -h | --help)
      saw_help=1
      idx=$((idx + 1))
      continue
      ;;
    -o)
      idx=$((idx + 2))
      continue
      ;;
    --no-color)
      idx=$((idx + 1))
      continue
      ;;
    -*)
      exit 0
      ;;
    *)
      verb="$word"
      subverb="${words[$((idx + 1))]:-}"
      break
      ;;
  esac
done

# No verb at all (every token was a recognized flag): approve only if that
# was a help request, e.g. `stackdome --help`. Otherwise there's nothing to
# approve — defer.
if [ -z "$verb" ]; then
  if [ "$saw_help" -eq 1 ]; then
    approve "Help flag — prints usage, does not execute a subcommand."
  fi
  exit 0
fi

# --- Step 6: allow-list of read-only operations -----------------------------
# Only operations that cannot change or destroy state are auto-approved.
# Keep this list narrow and explicit rather than trying to enumerate every
# destructive verb — anything not named here defers by default.
case "$verb" in
  version | whoami | validate | status | logs)
    approve "Read-only stackdome command ($verb)."
    ;;
  config)
    case "$subverb" in
      view) approve "Read-only stackdome command (config view)." ;;
    esac
    ;;
  stack)
    case "$subverb" in
      list | info) approve "Read-only stackdome command (stack $subverb)." ;;
    esac
    ;;
  release)
    case "$subverb" in
      list | info | events) approve "Read-only stackdome command (release $subverb)." ;;
    esac
    ;;
  build)
    case "$subverb" in
      list | info | logs) approve "Read-only stackdome command (build $subverb)." ;;
    esac
    ;;
  secret)
    # secret create/set/delete mutate a secret's value — never here.
    case "$subverb" in
      list | info) approve "Read-only stackdome command (secret $subverb)." ;;
    esac
    ;;
  volume)
    case "$subverb" in
      list) approve "Read-only stackdome command (volume list)." ;;
    esac
    ;;
  addon)
    # Only "addon postgres <op>" is defined today.
    if [ "$subverb" = "postgres" ]; then
      op="${words[$((idx + 2))]:-}"
      case "$op" in
        # "credentials" reads as a verb but hands back live DB credentials —
        # treat it the same as a mutation and keep it behind the prompt.
        list | info | backups) approve "Read-only stackdome command (addon postgres $op)." ;;
      esac
    fi
    ;;
  token)
    # "token create" mints a live credential — never here.
    case "$subverb" in
      list | scopes) approve "Read-only stackdome command (token $subverb)." ;;
    esac
    ;;
esac

# Every other verb (deploy, destroy, init, restart, open, login, logout,
# signup, or an unrecognized/misspelled one) falls through to here and
# defers to the normal permission prompt.
exit 0
