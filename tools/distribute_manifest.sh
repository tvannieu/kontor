#!/usr/bin/env bash
# distribute_manifest.sh — copy the canonical manifest to every branch.
#
#   ./distribute_manifest.sh          write the copies
#   ./distribute_manifest.sh --check  report drift only, change nothing (exit 1 on drift)
#
# The branch list is instance data and lives in the config, not here.
# The operator directs the distribution; a session may execute it. This is the
# one sanctioned exception to the boundary rule and it does not generalise:
# it covers generated files with exactly one correct location.
#
# Never edit a distributed copy. They carry a header saying so.
set -euo pipefail

CONF="${KONTOR_CONF:-$HOME/.config/kontor/branches.conf}"
[ -r "$CONF" ] || { echo "no config at $CONF (see tools/kontor.conf.example)" >&2; exit 2; }
. "$CONF"
: "${MANIFEST_SOURCE:?MANIFEST_SOURCE not set in $CONF}"
[ -f "$MANIFEST_SOURCE" ] || { echo "manifest not found: $MANIFEST_SOURCE" >&2; exit 2; }

HEADER_LINES=5
header() {
  printf '<!-- GENERATED FILE — DO NOT EDIT HERE.\n'
  printf '     Canonical source: %s\n' "$MANIFEST_SOURCE"
  printf '     Regenerate with:  tools/distribute_manifest.sh\n'
  printf '     Edits made in this copy are overwritten without warning. -->\n\n'
}

check_only=0; [ "${1:-}" = "--check" ] && check_only=1
drift=0

for branch in "${BRANCHES[@]}"; do
  target="$KONTOR_ROOT/$branch/REPO_MANIFEST.md"
  if [ ! -d "$KONTOR_ROOT/$branch" ]; then
    printf '  %-22s skipped (no such directory)\n' "$branch"; continue
  fi
  if [ -f "$target" ]; then
    if head -1 "$target" | grep -q 'GENERATED FILE'; then
      body=$(tail -n +$((HEADER_LINES + 1)) "$target")
    else
      body=$(cat "$target")
    fi
    if [ "$body" = "$(cat "$MANIFEST_SOURCE")" ]; then
      printf '  %-22s up to date\n' "$branch"; continue
    fi
    drift=1
    [ "$check_only" = 1 ] && { printf '  %-22s DRIFTED\n' "$branch"; continue; }
  else
    drift=1
    [ "$check_only" = 1 ] && { printf '  %-22s MISSING\n' "$branch"; continue; }
  fi
  { header; cat "$MANIFEST_SOURCE"; } > "$target"
  printf '  %-22s written\n' "$branch"
done

if [ "$check_only" = 1 ]; then
  if [ "$drift" = 0 ]; then echo "all copies match the canonical manifest"
  else echo "drift found — run without --check to overwrite" >&2; exit 1; fi
fi
