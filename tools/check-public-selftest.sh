#!/usr/bin/env bash
# check-public-selftest.sh — prove the gate can still block.
#
# A gate that has only ever printed "clean" is indistinguishable from a gate
# that cannot print anything else. This plants a file containing a real
# deny-listed term, asserts check-public.sh blocks, removes it, and asserts
# the gate passes again.
#
# It plants the canary in TWO places, and inbox/ is the important one: the
# gate excluded that directory from every scan until 2026-09-20, and reported
# clean over eight messages full of other branches' names for as long as they
# sat there. A self-test that only plants at the repository root would have
# passed throughout. See docs/lessons.md.
#
# The term is read from the deny-list at run time and never printed, never
# written anywhere but the canary file, and the canary file is removed on
# every exit path.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2

GATE="tools/check-public.sh"
DENY="${KONTOR_DENY:-$HOME/.config/kontor/deny.txt}"
[ -r "$DENY" ] || { echo "deny-list not readable: $DENY" >&2; exit 2; }

term=$(grep -vE '^[[:space:]]*(#|$)' "$DENY" | head -1)
[ -n "$term" ] || { echo "deny-list is empty — nothing to plant" >&2; exit 2; }

canaries=("./.kontor-canary.md" "./inbox/.kontor-canary.txt")
cleanup() { rm -f "${canaries[@]}"; }
trap cleanup EXIT INT TERM

fail=0
note() { printf '  %-46s %s\n' "$1" "$2"; }

# 0. the gate must be clean before we start, or nothing below means anything.
if ! bash "$GATE" >/dev/null 2>&1; then
  echo "SELFTEST INCONCLUSIVE: the gate already blocks before any canary is planted." >&2
  echo "Fix the real finding first, then run this again." >&2
  exit 2
fi
note "gate clean before planting" "ok"

for c in "${canaries[@]}"; do
  cleanup
  mkdir -p "$(dirname "$c")"
  printf 'canary — this file must make the gate block.\n%s\n' "$term" > "$c"
  if bash "$GATE" >/dev/null 2>&1; then
    note "planted in ${c#./} — gate should BLOCK" "FAIL (it passed)"
    fail=1
  else
    note "planted in ${c#./} — gate blocks" "ok"
  fi
done

cleanup
if bash "$GATE" >/dev/null 2>&1; then
  note "canaries removed — gate clean again" "ok"
else
  note "canaries removed — gate should be clean" "FAIL (still blocking)"
  fail=1
fi

echo
if [ "$fail" = 0 ]; then
  echo "Self-test passed: the gate blocks what it claims to catch, in the repository root AND in inbox/."
else
  echo "Self-test FAILED — the gate cannot be trusted until this is understood." >&2
fi
exit "$fail"
