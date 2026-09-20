#!/usr/bin/env bash
# census.sh — count the system, so the numbers in the README can be re-derived.
#
# Prints repositories, commits and pouch messages with the definition used for
# each. Numbers in documentation should be quoted with the date this produced
# them; a reader who can reproduce your figures stops auditing you.
set -uo pipefail

CONF="${KONTOR_CONF:-$HOME/.config/kontor/branches.conf}"
[ -r "$CONF" ] && . "$CONF" || { echo "no config at $CONF" >&2; exit 2; }

# Three dates, not one. "How long has this been running" has no single
# answer: the repositories, the conventions and the pouch each began on a
# different day, and quoting only the first invites the reader to assume the
# whole arrangement is that old. The README said "four months" for a while,
# which matched none of them.
repos=0; commits=0; first="9999-99-99"; conv="9999-99-99"; pouch1="9999-99-99"
newest="0000-00-00"
for b in "${BRANCHES[@]}"; do
  d="$KONTOR_ROOT/$b"
  [ -d "$d/.git" ] || continue
  repos=$((repos+1))
  n=$(git -C "$d" rev-list --count HEAD 2>/dev/null || echo 0)
  commits=$((commits+n))
  f=$(git -C "$d" log --reverse --format=%ad --date=short 2>/dev/null | head -1)
  [ -n "$f" ] && [[ "$f" < "$first" ]] && first="$f"
  [ -n "$f" ] && [[ "$f" > "$newest" ]] && newest="$f"
  c=$(git -C "$d" log --reverse --format=%ad --date=short --diff-filter=A \
        -- AGENTS.md CLAUDE.md 2>/dev/null | head -1)
  [ -n "$c" ] && [[ "$c" < "$conv" ]] && conv="$c"
  i=$(git -C "$d" log --reverse --format=%ad --date=short --diff-filter=A \
        -- inbox 2>/dev/null | head -1)
  [ -n "$i" ] && [[ "$i" < "$pouch1" ]] && pouch1="$i"
done

# A pouch message is a .md file in a branch's inbox/, excluding the folder's own
# README/INDEX. "delivered" counts those already moved to processed/.
pouch=$(find "$KONTOR_ROOT"/*/inbox -name '*.md' 2>/dev/null \
        | grep -vE '/(README|INDEX)\.md$' | wc -l | tr -d ' ')
done_=$(find "$KONTOR_ROOT"/*/inbox/processed -name '*.md' 2>/dev/null \
        | grep -vE '/(README|INDEX)\.md$' | wc -l | tr -d ' ')

cat <<TXT
Kontor census — $(date +%Y-%m-%d)

  repositories   $repos      branches listed in the instance config that contain a .git
  commits        $commits    sum of \`git rev-list --count HEAD\` across those
  earliest       $first      first commit in any of them
  newest repo    $newest      first commit in the most recently started one
  conventions    $conv      first AGENTS.md or CLAUDE.md in any of them
  pouch since    $pouch1      first inbox/ directory in any of them
  pouch messages $pouch      .md files under any inbox/, excluding README and INDEX
   of which done $done_      already moved to inbox/processed/

Reproduce with: tools/census.sh
TXT
