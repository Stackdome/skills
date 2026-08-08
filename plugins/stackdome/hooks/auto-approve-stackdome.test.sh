#!/usr/bin/env bash
# Plain-bash test for auto-approve-stackdome.sh. No framework — run directly:
#   ./auto-approve-stackdome.test.sh
# Exits non-zero if any case fails.
set -u

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
hook="$script_dir/auto-approve-stackdome.sh"

# The hook only approves when a `stackdome` binary resolves via PATH. Give it
# a fake one so a real install, or its absence, can't change the result.
fake_bin_dir="$(mktemp -d)"
cat > "$fake_bin_dir/stackdome" <<'EOF'
#!/bin/sh
echo "fake stackdome: $*"
EOF
chmod +x "$fake_bin_dir/stackdome"
# shellcheck disable=SC2329  # invoked by the trap below, not directly
cleanup() { rm -rf "$fake_bin_dir"; }
trap cleanup EXIT

pass_count=0
fail_count=0

run_hook() {
  local command_str="$1"
  local tool_name="${2:-Bash}"
  PATH="$fake_bin_dir:$PATH" jq -n --arg cmd "$command_str" --arg tool "$tool_name" \
    '{tool_name: $tool, tool_input: {command: $cmd}}' | PATH="$fake_bin_dir:$PATH" "$hook"
}

assert_approve() {
  local desc="$1" command_str="$2"
  local out exit_code
  out="$(run_hook "$command_str")"
  exit_code=$?
  local decision
  decision="$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // empty' 2>/dev/null)"
  if [ "$exit_code" -eq 0 ] && [ "$decision" = "allow" ]; then
    echo "PASS (approve): $desc"
    pass_count=$((pass_count + 1))
  else
    echo "FAIL (approve): $desc -- command=[$command_str] exit=$exit_code output=[$out]"
    fail_count=$((fail_count + 1))
  fi
}

assert_defer() {
  local desc="$1" command_str="$2" tool_name="${3:-Bash}"
  local out exit_code
  out="$(run_hook "$command_str" "$tool_name")"
  exit_code=$?
  if [ "$exit_code" -eq 0 ] && [ -z "$out" ]; then
    echo "PASS (defer): $desc"
    pass_count=$((pass_count + 1))
  else
    echo "FAIL (defer): $desc -- command=[$command_str] exit=$exit_code output=[$out]"
    fail_count=$((fail_count + 1))
  fi
}

# Every stackdome verb approves — the hook gates the shape of the command,
# not the subcommand. Destructive verbs are covered too, deliberately.
echo "--- APPROVE cases ---"
assert_approve "plain status" "stackdome status"
assert_approve "logs with duration flag" "stackdome logs web --since 10m"
assert_approve "metacharacters safely inside single quotes" "stackdome secret set foo --data 'KEY=va;lue\$(oops)'"
assert_approve "metacharacters safely inside double quotes" 'stackdome secret set foo --data "KEY=va;lue"'
assert_approve "release events" "stackdome release events abc123"
assert_approve "addon postgres list" "stackdome addon postgres list"
assert_approve "leading global flag before verb" "stackdome -o json status"
assert_approve "boolean global flag before verb" "stackdome --no-color status"
assert_approve "token scopes" "stackdome token scopes"
assert_approve "bare --help" "stackdome --help"
assert_approve "bare invocation, no subcommand" "stackdome"
assert_approve "destroy" "stackdome destroy -y"
assert_approve "secret delete" "stackdome secret delete prod-db"
assert_approve "deploy" "stackdome deploy --wait -o json"
assert_approve "token create" "stackdome token create ci"
assert_approve "addon postgres credentials" "stackdome addon postgres credentials db main"
assert_approve "stack delete" "stackdome stack delete old"
assert_approve "restart" "stackdome restart web"
assert_approve "open" "stackdome open"
assert_approve "unrecognized verb" "stackdome status-evil"

echo "--- DEFER cases ---"
assert_defer "chained rm via semicolon" "stackdome status; rm -rf ~"
assert_defer "trusted token after a comment marker" "printf x # stackdome status"
assert_defer "chained curl via &&" "stackdome status && curl evil.example"
assert_defer "piped to sh" "stackdome status | sh"
# shellcheck disable=SC2016  # the literal, unexpanded string IS the input under test
assert_defer "command substitution wrapping the call" 'echo $(stackdome status)'
assert_defer "relative path invocation" "./stackdome status"
assert_defer "absolute path invocation" "/tmp/stackdome status"
assert_defer "lookalike binary name" "stackdome-evil status"
assert_defer "unrelated destructive command" "rm -rf /"
assert_defer "unterminated single quote" "stackdome secret set foo --data 'unterminated"
# A parse that disagrees with bash about where a quoted span begins hides the
# top-level `;` behind what it mistakes for data.
assert_defer "escaped double quote" 'stackdome \" ; touch pwned ; echo \"'
assert_defer "escaped single quote" "stackdome \\' ; touch pwned ; echo \\'"
assert_defer "single quote inside double" 'stackdome "a'"'"'b" ; touch pwned'
assert_defer "double quote inside single" "stackdome 'a\"b' ; touch pwned"
# shellcheck disable=SC1003  # the trailing backslash is the literal input under test
assert_defer "trailing lone backslash" 'stackdome \'
# shellcheck disable=SC1003
assert_defer "trailing backslash after a read-only verb" 'stackdome status \'
assert_defer "subshell" '(stackdome status; touch pwned)'
assert_defer "brace group" '{ stackdome status; touch pwned; }'
assert_defer "redirection" "stackdome status > pwned"
assert_defer "newline between commands" "stackdome status
touch pwned"
assert_defer "non-Bash tool call" '{"file_path":"/tmp/x"}' "Write"
# An env-var prefix makes the first word an assignment, not the binary.
assert_defer "env assignment before the binary" "STACKDOME_TOKEN=x stackdome status"

echo
echo "$pass_count passed, $fail_count failed"
if [ "$fail_count" -gt 0 ]; then
  exit 1
fi
exit 0
