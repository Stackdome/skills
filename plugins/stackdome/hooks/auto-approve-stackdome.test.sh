#!/usr/bin/env bash
# Plain-bash test for auto-approve-stackdome.sh. No framework — run directly:
#   ./auto-approve-stackdome.test.sh
# Exits non-zero if any case fails.
set -u

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
hook="$script_dir/auto-approve-stackdome.sh"

# The hook only approves when a real `stackdome` binary resolves via PATH.
# Give it a harmless fake one, isolated in its own PATH-only directory so a
# real install (or its absence) on the dev machine can't affect the result.
fake_bin_dir="$(mktemp -d)"
cat > "$fake_bin_dir/stackdome" <<'EOF'
#!/bin/sh
echo "fake stackdome: $*"
EOF
chmod +x "$fake_bin_dir/stackdome"
cleanup() { rm -rf "$fake_bin_dir"; }
trap cleanup EXIT

pass_count=0
fail_count=0

# Feeds the hook a Bash tool call with the given command and captures its
# stdout + exit code.
run_hook() {
  local command_str="$1"
  local tool_name="${2:-Bash}"
  PATH="$fake_bin_dir:$PATH" jq -n --arg cmd "$command_str" --arg tool "$tool_name" \
    '{tool_name: $tool, tool_input: {command: $cmd}}' | PATH="$fake_bin_dir:$PATH" "$hook"
}

# Asserts the hook approves (permissionDecision "allow" on stdout, exit 0).
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

# Asserts the hook defers: exit 0, no stdout at all.
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

echo "--- APPROVE cases ---"
assert_approve "plain status" "stackdome status"
assert_approve "deploy with flags" "stackdome deploy --wait -o json"
assert_approve "logs with duration flag" "stackdome logs web --since 10m"
assert_approve "metacharacters safely inside single quotes" "stackdome secret set foo --data 'KEY=va;lue\$(oops)'"
assert_approve "metacharacters safely inside double quotes" 'stackdome secret set foo --data "KEY=va;lue"'

echo "--- DEFER cases ---"
assert_defer "chained rm via semicolon" "stackdome status; rm -rf ~"
assert_defer "trusted token after a comment marker" "printf x # stackdome status"
assert_defer "chained curl via &&" "stackdome status && curl evil.example"
assert_defer "piped to sh" "stackdome status | sh"
assert_defer "command substitution wrapping the call" 'echo $(stackdome status)'
assert_defer "relative path invocation" "./stackdome status"
assert_defer "absolute path invocation" "/tmp/stackdome status"
assert_defer "lookalike binary name" "stackdome-evil status"
assert_defer "unrelated destructive command" "rm -rf /"
assert_defer "unterminated single quote" "stackdome secret set foo --data 'unterminated"
assert_defer "non-Bash tool call" '{"file_path":"/tmp/x"}' "Write"

echo
echo "$pass_count passed, $fail_count failed"
if [ "$fail_count" -gt 0 ]; then
  exit 1
fi
exit 0
